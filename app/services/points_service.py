from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from app.models.points_earned import PointsEarned
from app.models.user import User
from app.models.lesson import Lesson
from app.core.exceptions import ResourceNotFoundException, InvalidDataException


class PointsService:
    """Service for managing points earning and tracking"""

    @staticmethod
    def award_lesson_points(db: Session, user_id: int, lesson_id: int,
                            points: int, lesson_title: str = None) -> Dict[str, Any]:
        """Award points for lesson completion"""

        # Verify user and lesson exist
        user = db.query(User).filter(User.id == user_id).first()
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

        if not user:
            raise ResourceNotFoundException("User", "User not found")
        if not lesson:
            raise ResourceNotFoundException("Lesson", "Lesson not found")

        # Create points record
        points_record = PointsEarned.create_lesson_points(
            user_id=user_id,
            lesson_id=lesson_id,
            points=points,
            lesson_title=lesson_title or lesson.title
        )

        try:
            db.add(points_record)
            db.commit()
            db.refresh(points_record)

            return {
                "success": True,
                "message": f"Awarded {points} points for lesson completion",
                "points_record": points_record,
                "user_total_points": user.total_points + points_record.effective_points
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Failed to award lesson points: {str(e)}")

    @staticmethod
    def award_weaklist_points(db: Session, user_id: int, words_practiced: int,
                              accuracy: float = None) -> Dict[str, Any]:
        """Award points for weaklist practice"""

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundException("User", "User not found")

        # Create points record
        points_record = PointsEarned.create_weaklist_points(
            user_id=user_id,
            words_practiced=words_practiced,
            accuracy=accuracy
        )

        try:
            db.add(points_record)
            db.commit()
            db.refresh(points_record)

            # Calculate bonus message
            bonus_msg = ""
            if points_record.bonus_multiplier > 1:
                bonus_msg = f" (x{points_record.bonus_multiplier} accuracy bonus!)"

            return {
                "success": True,
                "message": f"Awarded {points_record.effective_points} points for weaklist practice{bonus_msg}",
                "points_record": points_record,
                "base_points": points_record.points_amount,
                "bonus_multiplier": points_record.bonus_multiplier,
                "effective_points": points_record.effective_points,
                "user_total_points": user.total_points + points_record.effective_points
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Failed to award weaklist points: {str(e)}")

    @staticmethod
    def award_bonus_points(db: Session, user_id: int, points: int,
                           reason: str) -> Dict[str, Any]:
        """Award bonus points for achievements, events, etc."""

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundException("User", "User not found")

        # Create points record
        points_record = PointsEarned.create_bonus_points(
            user_id=user_id,
            points=points,
            reason=reason
        )

        try:
            db.add(points_record)
            db.commit()
            db.refresh(points_record)

            return {
                "success": True,
                "message": f"Awarded {points} bonus points: {reason}",
                "points_record": points_record,
                "user_total_points": user.total_points + points
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Failed to award bonus points: {str(e)}")

    @staticmethod
    def get_user_points_summary(db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive points summary for user"""

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundException("User", "User not found")

        # Get date ranges
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Calculate points by period
        all_points = user.points_earned
        points_today = sum(pe.effective_points for pe in all_points if pe.date_earned == today)
        points_week = sum(pe.effective_points for pe in all_points if pe.date_earned >= week_start)
        points_month = sum(pe.effective_points for pe in all_points if pe.date_earned >= month_start)

        # Calculate points by source
        lesson_points = sum(pe.effective_points for pe in all_points if pe.source_type == "lesson")
        weaklist_points = sum(pe.effective_points for pe in all_points if pe.source_type == "weaklist")
        bonus_points = sum(pe.effective_points for pe in all_points if pe.source_type == "bonus")

        # Calculate streaks and averages
        active_days = len(set(pe.date_earned for pe in all_points))
        avg_daily = round(user.total_points / active_days, 1) if active_days > 0 else 0

        # Find best day
        daily_totals = {}
        for pe in all_points:
            daily_totals[pe.date_earned] = daily_totals.get(pe.date_earned, 0) + pe.effective_points

        best_day_points = max(daily_totals.values()) if daily_totals else 0

        # Calculate current streak
        current_streak = PointsService._calculate_current_streak(all_points)

        return {
            "user_id": user_id,
            "user_name": user.full_name,
            "total_points": user.total_points,
            "points_today": points_today,
            "points_this_week": points_week,
            "points_this_month": points_month,
            "points_breakdown": {
                "lesson_points": lesson_points,
                "weaklist_points": weaklist_points,
                "bonus_points": bonus_points
            },
            "statistics": {
                "active_days": active_days,
                "average_daily_points": avg_daily,
                "best_day_points": best_day_points,
                "current_streak_days": current_streak
            }
        }

    @staticmethod
    def get_daily_points_leaderboard(db: Session, learning_center_id: int,
                                     target_date: date = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get daily points leaderboard for a learning center"""

        if not target_date:
            target_date = date.today()

        # Get all users in learning center with points today
        daily_points = db.query(
            User.id,
            User.full_name,
            db.func.coalesce(db.func.sum(PointsEarned.points_amount * PointsEarned.bonus_multiplier), 0).label(
                'points_today')
        ).outerjoin(PointsEarned,
                    db.and_(
                        User.id == PointsEarned.user_id,
                        PointsEarned.date_earned == target_date
                    )
                    ).filter(
            User.learning_center_id == learning_center_id,
            User.is_active == True
        ).group_by(User.id, User.full_name).order_by(
            db.desc('points_today')
        ).limit(limit).all()

        # Add ranks
        leaderboard = []
        for rank, (user_id, full_name, points_today) in enumerate(daily_points, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "full_name": full_name,
                "points_today": int(points_today or 0),
                "is_top_3": rank <= 3,
                "is_first_place": rank == 1
            })

        return leaderboard

    @staticmethod
    def get_all_time_points_leaderboard(db: Session, learning_center_id: int,
                                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get all-time points leaderboard for a learning center"""

        # Get all users with their total points
        all_time_points = db.query(
            User.id,
            User.full_name,
            db.func.coalesce(db.func.sum(PointsEarned.points_amount * PointsEarned.bonus_multiplier), 0).label(
                'total_points'),
            db.func.max(PointsEarned.date_earned).label('last_activity')
        ).outerjoin(PointsEarned).filter(
            User.learning_center_id == learning_center_id,
            User.is_active == True
        ).group_by(User.id, User.full_name).order_by(
            db.desc('total_points')
        ).limit(limit).all()

        # Add ranks
        leaderboard = []
        for rank, (user_id, full_name, total_points, last_activity) in enumerate(all_time_points, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "full_name": full_name,
                "total_points": int(total_points or 0),
                "last_activity_date": last_activity
            })

        return leaderboard

    @staticmethod
    def get_user_points_history(db: Session, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user's points history over time"""

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundException("User", "User not found")

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get points records in date range
        points_records = db.query(PointsEarned).filter(
            PointsEarned.user_id == user_id,
            PointsEarned.date_earned >= start_date,
            PointsEarned.date_earned <= end_date
        ).order_by(PointsEarned.date_earned).all()

        # Group by date
        daily_breakdown = {}
        for record in points_records:
            date_key = record.date_earned
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = {
                    "date": date_key,
                    "total_points": 0,
                    "lesson_points": 0,
                    "weaklist_points": 0,
                    "bonus_points": 0,
                    "records": []
                }

            daily_breakdown[date_key]["total_points"] += record.effective_points
            daily_breakdown[date_key][f"{record.source_type}_points"] += record.effective_points
            daily_breakdown[date_key]["records"].append(record)

        return {
            "user_id": user_id,
            "period": {"start_date": start_date, "end_date": end_date, "days": days},
            "total_points_period": sum(r.effective_points for r in points_records),
            "daily_breakdown": list(daily_breakdown.values()),
            "trend": PointsService._calculate_trend(list(daily_breakdown.values()))
        }

    @staticmethod
    def _calculate_current_streak(points_records: List[PointsEarned]) -> int:
        """Calculate current consecutive days streak"""
        if not points_records:
            return 0

        # Get unique dates and sort
        dates = sorted(set(pe.date_earned for pe in points_records), reverse=True)

        today = date.today()
        streak = 0

        for i, check_date in enumerate(dates):
            expected_date = today - timedelta(days=i)
            if check_date == expected_date:
                streak += 1
            else:
                break

        return streak

    @staticmethod
    def _calculate_trend(daily_data: List[Dict]) -> str:
        """Calculate trend direction from daily data"""
        if len(daily_data) < 7:
            return "stable"

        # Compare first half vs second half
        mid_point = len(daily_data) // 2
        first_half_avg = sum(d["total_points"] for d in daily_data[:mid_point]) / mid_point
        second_half_avg = sum(d["total_points"] for d in daily_data[mid_point:]) / (len(daily_data) - mid_point)

        if second_half_avg > first_half_avg * 1.1:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            return "decreasing"
        else:
            return "stable"