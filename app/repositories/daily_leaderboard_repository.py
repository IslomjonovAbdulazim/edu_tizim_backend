from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, date, timedelta
from app.models.daily_leaderboard import DailyLeaderboard
from app.models.user import User
from app.models.learning_center import LearningCenter
from app.repositories.base_repository import BaseRepository


class DailyLeaderboardRepository(BaseRepository[DailyLeaderboard]):
    def __init__(self):
        super().__init__(DailyLeaderboard)

    def get_daily_leaderboard(
            self,
            db: Session,
            learning_center_id: int,
            target_date: date,
            limit: int = 100
    ) -> List[DailyLeaderboard]:
        """Get daily leaderboard for a specific date and learning center"""
        return db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date == target_date
            )
        ).options(
            joinedload(DailyLeaderboard.user)
        ).order_by(DailyLeaderboard.rank).limit(limit).all()

    def get_user_daily_entry(
            self,
            db: Session,
            user_id: int,
            target_date: date
    ) -> Optional[DailyLeaderboard]:
        """Get specific user's entry for a date"""
        return db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.user_id == user_id,
                DailyLeaderboard.leaderboard_date == target_date
            )
        ).first()

    def get_user_history(
            self,
            db: Session,
            user_id: int,
            days: int = 30,
            learning_center_id: Optional[int] = None
    ) -> List[DailyLeaderboard]:
        """Get user's leaderboard history for specified days"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        query = db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.user_id == user_id,
                DailyLeaderboard.leaderboard_date >= start_date,
                DailyLeaderboard.leaderboard_date <= end_date
            )
        )

        if learning_center_id:
            query = query.filter(DailyLeaderboard.learning_center_id == learning_center_id)

        return query.order_by(desc(DailyLeaderboard.leaderboard_date)).all()

    def create_daily_snapshot(
            self,
            db: Session,
            learning_center_id: int,
            target_date: date,
            leaderboard_data: List[Dict[str, Any]]
    ) -> List[DailyLeaderboard]:
        """Create daily leaderboard snapshot from current data"""

        # Get previous day's data for position change calculation
        previous_date = target_date - timedelta(days=1)
        previous_entries = {
            entry.user_id: entry.rank
            for entry in self.get_daily_leaderboard(db, learning_center_id, previous_date)
        }

        # Delete existing entries for this date (if any)
        db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date == target_date
            )
        ).delete()

        # Create new entries
        new_entries = []
        for entry_data in leaderboard_data:
            user_id = entry_data["user_id"]
            current_rank = entry_data["rank"]
            previous_rank = previous_entries.get(user_id)

            # Calculate position change
            if previous_rank is None:
                position_change = 0  # New to leaderboard
            else:
                position_change = previous_rank - current_rank  # Positive = moved up

            daily_entry = DailyLeaderboard(
                learning_center_id=learning_center_id,
                leaderboard_date=target_date,
                user_id=user_id,
                rank=current_rank,
                points=entry_data["points"],
                previous_rank=previous_rank,
                position_change=position_change,
                user_full_name=entry_data["full_name"],
                user_avatar_url=entry_data.get("avatar_url")
            )

            db.add(daily_entry)
            new_entries.append(daily_entry)

        db.commit()

        # Refresh all entries
        for entry in new_entries:
            db.refresh(entry)

        return new_entries

    def get_top_performers(
            self,
            db: Session,
            learning_center_id: int,
            days: int = 7,
            top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """Get users who frequently appear in top N positions"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Count how many times each user was in top N
        top_appearances = db.query(
            DailyLeaderboard.user_id,
            DailyLeaderboard.user_full_name,
            func.count(DailyLeaderboard.id).label('top_appearances'),
            func.avg(DailyLeaderboard.rank).label('avg_rank'),
            func.min(DailyLeaderboard.rank).label('best_rank'),
            func.sum(DailyLeaderboard.points).label('total_points')
        ).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date >= start_date,
                DailyLeaderboard.leaderboard_date <= end_date,
                DailyLeaderboard.rank <= top_n
            )
        ).group_by(
            DailyLeaderboard.user_id,
            DailyLeaderboard.user_full_name
        ).order_by(
            desc('top_appearances'),
            desc('total_points')
        ).all()

        return [
            {
                "user_id": user_id,
                "user_full_name": user_full_name,
                "top_appearances": top_appearances,
                "avg_rank": float(avg_rank),
                "best_rank": best_rank,
                "total_points": total_points,
                "consistency_score": (top_appearances / days * 100) if days > 0 else 0
            }
            for user_id, user_full_name, top_appearances, avg_rank, best_rank, total_points in top_appearances
        ]

    def get_biggest_climbers(
            self,
            db: Session,
            learning_center_id: int,
            target_date: date,
            limit: int = 10
    ) -> List[DailyLeaderboard]:
        """Get users with biggest positive position changes on a specific date"""
        return db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date == target_date,
                DailyLeaderboard.position_change > 0
            )
        ).order_by(desc(DailyLeaderboard.position_change)).limit(limit).all()

    def get_participation_stats(
            self,
            db: Session,
            learning_center_id: int,
            days: int = 30
    ) -> Dict[str, Any]:
        """Get participation statistics for the learning center"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Daily participation counts
        daily_participation = db.query(
            DailyLeaderboard.leaderboard_date,
            func.count(DailyLeaderboard.id).label('participants')
        ).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date >= start_date,
                DailyLeaderboard.leaderboard_date <= end_date
            )
        ).group_by(DailyLeaderboard.leaderboard_date).order_by(DailyLeaderboard.leaderboard_date).all()

        total_unique_participants = db.query(DailyLeaderboard.user_id).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date >= start_date,
                DailyLeaderboard.leaderboard_date <= end_date
            )
        ).distinct().count()

        # Average participation per day
        avg_daily_participation = db.query(
            func.avg(func.count(DailyLeaderboard.id))
        ).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date >= start_date,
                DailyLeaderboard.leaderboard_date <= end_date
            )
        ).group_by(DailyLeaderboard.leaderboard_date).scalar() or 0

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "total_unique_participants": total_unique_participants,
            "average_daily_participants": float(avg_daily_participation),
            "daily_breakdown": [
                {
                    "date": str(leaderboard_date),
                    "participants": participants
                }
                for leaderboard_date, participants in daily_participation
            ]
        }

    def get_streak_leaders(
            self,
            db: Session,
            learning_center_id: int,
            streak_type: str = "top_3",  # "top_3", "top_10", "participation"
            min_streak: int = 3
    ) -> List[Dict[str, Any]]:
        """Get users with longest streaks in specified category"""

        # This is a complex query that would need to be optimized based on specific database
        # For now, implementing a basic version

        if streak_type == "top_3":
            rank_filter = DailyLeaderboard.rank <= 3
        elif streak_type == "top_10":
            rank_filter = DailyLeaderboard.rank <= 10
        else:  # participation
            rank_filter = DailyLeaderboard.rank > 0  # Any participation

        # Get recent entries for analysis
        recent_entries = db.query(DailyLeaderboard).filter(
            and_(
                DailyLeaderboard.learning_center_id == learning_center_id,
                DailyLeaderboard.leaderboard_date >= date.today() - timedelta(days=30),
                rank_filter
            )
        ).order_by(DailyLeaderboard.user_id, DailyLeaderboard.leaderboard_date).all()

        # Group by user and calculate streaks (simplified algorithm)
        user_streaks = {}
        for entry in recent_entries:
            user_id = entry.user_id
            if user_id not in user_streaks:
                user_streaks[user_id] = {
                    "user_full_name": entry.user_full_name,
                    "current_streak": 0,
                    "max_streak": 0,
                    "last_date": None
                }

            # Simple streak calculation (would need more sophisticated logic for production)
            if user_streaks[user_id]["last_date"] is None:
                user_streaks[user_id]["current_streak"] = 1
            else:
                expected_date = user_streaks[user_id]["last_date"] + timedelta(days=1)
                if entry.leaderboard_date == expected_date:
                    user_streaks[user_id]["current_streak"] += 1
                else:
                    user_streaks[user_id]["current_streak"] = 1

            user_streaks[user_id]["max_streak"] = max(
                user_streaks[user_id]["max_streak"],
                user_streaks[user_id]["current_streak"]
            )
            user_streaks[user_id]["last_date"] = entry.leaderboard_date

        # Filter and sort by streak length
        streak_leaders = [
            {
                "user_id": user_id,
                "user_full_name": data["user_full_name"],
                "current_streak": data["current_streak"],
                "max_streak": data["max_streak"]
            }
            for user_id, data in user_streaks.items()
            if data["max_streak"] >= min_streak
        ]

        return sorted(streak_leaders, key=lambda x: x["max_streak"], reverse=True)

    def cleanup_old_leaderboards(self, db: Session, days_to_keep: int = 90) -> int:
        """Delete old leaderboard entries"""
        cutoff_date = date.today() - timedelta(days=days_to_keep)

        deleted_count = db.query(DailyLeaderboard).filter(
            DailyLeaderboard.leaderboard_date < cutoff_date
        ).delete()

        db.commit()
        return deleted_count

    def get_learning_center_comparison(
            self,
            db: Session,
            date_from: date,
            date_to: date,
            limit_per_center: int = 10
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get top performers across all learning centers for comparison"""

        top_performers = db.query(
            DailyLeaderboard.learning_center_id,
            DailyLeaderboard.user_id,
            DailyLeaderboard.user_full_name,
            func.avg(DailyLeaderboard.rank).label('avg_rank'),
            func.sum(DailyLeaderboard.points).label('total_points'),
            func.count(DailyLeaderboard.id).label('appearances')
        ).filter(
            and_(
                DailyLeaderboard.leaderboard_date >= date_from,
                DailyLeaderboard.leaderboard_date <= date_to,
                DailyLeaderboard.rank <= 10  # Only top 10 daily performers
            )
        ).group_by(
            DailyLeaderboard.learning_center_id,
            DailyLeaderboard.user_id,
            DailyLeaderboard.user_full_name
        ).order_by(
            DailyLeaderboard.learning_center_id,
            desc('total_points')
        ).all()

        # Group by learning center
        result = {}
        for entry in top_performers:
            center_id = entry.learning_center_id
            if center_id not in result:
                result[center_id] = []

            if len(result[center_id]) < limit_per_center:
                result[center_id].append({
                    "user_id": entry.user_id,
                    "user_full_name": entry.user_full_name,
                    "avg_rank": float(entry.avg_rank),
                    "total_points": entry.total_points,
                    "appearances": entry.appearances
                })

        return result