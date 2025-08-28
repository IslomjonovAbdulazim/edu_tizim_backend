from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, extract
from datetime import datetime, date, timedelta
from app.models.progress import Progress
from app.models.user import User
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class ProgressRepository(BaseRepository[Progress]):
    def __init__(self):
        super().__init__(Progress)

    def get_user_progress(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Progress]:
        """Get all progress records for a user"""
        return db.query(Progress).filter(Progress.user_id == user_id).options(
            joinedload(Progress.lesson).joinedload(Lesson.module).joinedload(Module.course),
            joinedload(Progress.user)
        ).order_by(desc(Progress.last_attempt_at)).offset(skip).limit(limit).all()

    def get_lesson_progress(self, db: Session, lesson_id: int, skip: int = 0, limit: int = 100) -> List[Progress]:
        """Get all progress records for a lesson"""
        return db.query(Progress).filter(Progress.lesson_id == lesson_id).options(
            joinedload(Progress.user),
            joinedload(Progress.lesson)
        ).order_by(desc(Progress.completion_percentage)).offset(skip).limit(limit).all()

    def get_user_lesson_progress(self, db: Session, user_id: int, lesson_id: int) -> Optional[Progress]:
        """Get specific progress record for a user and lesson"""
        return db.query(Progress).filter(
            and_(Progress.user_id == user_id, Progress.lesson_id == lesson_id)
        ).first()

    def create_or_update_progress(
            self,
            db: Session,
            user_id: int,
            lesson_id: int,
            completion_percentage: float,
            time_spent_seconds: int = 0
    ) -> Progress:
        """Create new progress record or update existing one"""
        progress = self.get_user_lesson_progress(db, user_id, lesson_id)

        if progress:
            # Update existing progress
            progress.update_progress(completion_percentage, time_spent_seconds)
            db.commit()
            db.refresh(progress)
        else:
            # Create new progress record
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                raise ValueError("Lesson not found")

            points = int((completion_percentage / 100.0) * lesson.completion_points)
            is_completed = completion_percentage >= 100.0

            progress_data = {
                "user_id": user_id,
                "lesson_id": lesson_id,
                "completion_percentage": completion_percentage,
                "points": points,
                "is_completed": is_completed,
                "total_attempts": 1,
                "best_score": completion_percentage,
                "time_spent_seconds": time_spent_seconds,
                "first_attempt_at": datetime.utcnow(),
                "last_attempt_at": datetime.utcnow()
            }

            if is_completed:
                progress_data["completed_at"] = datetime.utcnow()

            progress = self.create(db, progress_data)

        return progress

    def get_user_total_points(self, db: Session, user_id: int) -> int:
        """Get total points for a user"""
        result = db.query(func.sum(Progress.points)).filter(Progress.user_id == user_id).scalar()
        return result or 0

    def get_course_progress(self, db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
        """Get user's progress for a specific course"""
        query = db.query(Progress).join(Lesson).join(Module).filter(
            and_(Progress.user_id == user_id, Module.course_id == course_id)
        )

        total_lessons = db.query(Lesson).join(Module).filter(Module.course_id == course_id).count()
        completed_lessons = query.filter(Progress.is_completed == True).count()
        total_points = query.with_entities(func.sum(Progress.points)).scalar() or 0
        avg_completion = query.with_entities(func.avg(Progress.completion_percentage)).scalar() or 0.0

        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_points": total_points,
            "average_completion": float(avg_completion),
            "completion_rate": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        }

    def get_module_progress(self, db: Session, user_id: int, module_id: int) -> Dict[str, Any]:
        """Get user's progress for a specific module"""
        query = db.query(Progress).join(Lesson).filter(
            and_(Progress.user_id == user_id, Lesson.module_id == module_id)
        )

        total_lessons = db.query(Lesson).filter(Lesson.module_id == module_id).count()
        completed_lessons = query.filter(Progress.is_completed == True).count()
        total_points = query.with_entities(func.sum(Progress.points)).scalar() or 0
        avg_completion = query.with_entities(func.avg(Progress.completion_percentage)).scalar() or 0.0

        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_points": total_points,
            "average_completion": float(avg_completion),
            "completion_rate": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        }

    def get_daily_progress(self, db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
        """Get user's progress for a specific day"""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        query = db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.last_attempt_at >= start_datetime,
                Progress.last_attempt_at <= end_datetime
            )
        )

        lessons_attempted = query.count()
        lessons_completed = query.filter(Progress.is_completed == True).count()
        points_earned = query.with_entities(func.sum(Progress.points)).scalar() or 0
        time_spent = query.with_entities(func.sum(Progress.time_spent_seconds)).scalar() or 0

        return {
            "date": target_date,
            "lessons_attempted": lessons_attempted,
            "lessons_completed": lessons_completed,
            "points_earned": points_earned,
            "time_spent_seconds": time_spent,
            "time_spent_hours": round(time_spent / 3600.0, 2)
        }

    def get_weekly_progress(self, db: Session, user_id: int, week_start: date) -> Dict[str, Any]:
        """Get user's progress for a specific week"""
        week_end = week_start + timedelta(days=6)
        start_datetime = datetime.combine(week_start, datetime.min.time())
        end_datetime = datetime.combine(week_end, datetime.max.time())

        query = db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.last_attempt_at >= start_datetime,
                Progress.last_attempt_at <= end_datetime
            )
        )

        lessons_attempted = query.count()
        lessons_completed = query.filter(Progress.is_completed == True).count()
        points_earned = query.with_entities(func.sum(Progress.points)).scalar() or 0
        time_spent = query.with_entities(func.sum(Progress.time_spent_seconds)).scalar() or 0
        avg_score = query.with_entities(func.avg(Progress.completion_percentage)).scalar() or 0.0

        return {
            "week_start": week_start,
            "week_end": week_end,
            "lessons_attempted": lessons_attempted,
            "lessons_completed": lessons_completed,
            "points_earned": points_earned,
            "time_spent_seconds": time_spent,
            "time_spent_hours": round(time_spent / 3600.0, 2),
            "average_score": float(avg_score)
        }

    def get_leaderboard_data(
            self,
            db: Session,
            learning_center_id: int,
            target_date: Optional[date] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get leaderboard data for a specific date or overall"""
        if target_date:
            # Daily leaderboard - points earned on specific date
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            query = db.query(
                Progress.user_id,
                User.full_name,
                func.sum(Progress.points).label('points')
            ).join(User).filter(
                and_(
                    User.learning_center_id == learning_center_id,
                    Progress.last_attempt_at >= start_datetime,
                    Progress.last_attempt_at <= end_datetime
                )
            ).group_by(Progress.user_id, User.full_name).order_by(desc('points'))
        else:
            # Overall leaderboard - total points
            query = db.query(
                Progress.user_id,
                User.full_name,
                func.sum(Progress.points).label('points')
            ).join(User).filter(
                User.learning_center_id == learning_center_id
            ).group_by(Progress.user_id, User.full_name).order_by(desc('points'))

        results = query.limit(limit).all()

        leaderboard = []
        for rank, (user_id, full_name, points) in enumerate(results, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "full_name": full_name,
                "points": int(points or 0)
            })

        return leaderboard

    def get_user_streak(self, db: Session, user_id: int) -> int:
        """Calculate user's current streak (consecutive days with completed lessons)"""
        # Get all dates when user completed lessons, ordered by date desc
        completed_dates = db.query(
            func.date(Progress.completed_at)
        ).filter(
            and_(Progress.user_id == user_id, Progress.is_completed == True)
        ).distinct().order_by(desc(func.date(Progress.completed_at))).all()

        if not completed_dates:
            return 0

        completed_dates = [d[0] for d in completed_dates]
        today = date.today()

        # Check if user completed lessons today or yesterday (to allow for timezone differences)
        if completed_dates[0] not in [today, today - timedelta(days=1)]:
            return 0

        # Count consecutive days
        streak = 0
        expected_date = completed_dates[0]

        for completion_date in completed_dates:
            if completion_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break

        return streak

    def get_progress_analytics(
            self,
            db: Session,
            user_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            days: int = 30
    ) -> Dict[str, Any]:
        """Get progress analytics for a user or learning center"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        query = db.query(Progress).filter(
            Progress.last_attempt_at >= start_datetime,
            Progress.last_attempt_at <= end_datetime
        )

        if user_id:
            query = query.filter(Progress.user_id == user_id)
        elif learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        total_attempts = query.count()
        completed_lessons = query.filter(Progress.is_completed == True).count()
        total_points = query.with_entities(func.sum(Progress.points)).scalar() or 0
        total_time = query.with_entities(func.sum(Progress.time_spent_seconds)).scalar() or 0
        avg_score = query.with_entities(func.avg(Progress.completion_percentage)).scalar() or 0.0

        # Daily breakdown
        daily_stats = db.query(
            func.date(Progress.last_attempt_at).label('date'),
            func.count(Progress.id).label('attempts'),
            func.sum(func.case([(Progress.is_completed == True, 1)], else_=0)).label('completed'),
            func.sum(Progress.points).label('points')
        ).filter(
            Progress.last_attempt_at >= start_datetime,
            Progress.last_attempt_at <= end_datetime
        )

        if user_id:
            daily_stats = daily_stats.filter(Progress.user_id == user_id)
        elif learning_center_id:
            daily_stats = daily_stats.join(User).filter(User.learning_center_id == learning_center_id)

        daily_data = daily_stats.group_by(func.date(Progress.last_attempt_at)).all()

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "totals": {
                "attempts": total_attempts,
                "completed": completed_lessons,
                "points": total_points,
                "time_hours": round(total_time / 3600.0, 2),
                "average_score": float(avg_score),
                "completion_rate": (completed_lessons / total_attempts * 100) if total_attempts > 0 else 0.0
            },
            "daily_breakdown": [
                {
                    "date": str(row.date),
                    "attempts": row.attempts,
                    "completed": row.completed,
                    "points": row.points or 0
                }
                for row in daily_data
            ]
        }