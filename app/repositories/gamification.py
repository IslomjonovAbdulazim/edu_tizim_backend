from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, asc
from datetime import date, datetime, timedelta
from app.models.gamification import LeaderboardEntry, LeaderboardType
from app.repositories.base import BaseRepository


class LeaderboardRepository(BaseRepository):
    """Leaderboard repository for gamification features"""

    def __init__(self, db: Session):
        super().__init__(db, LeaderboardEntry)

    def get_leaderboard(
            self,
            leaderboard_type: LeaderboardType,
            group_id: int = None,
            leaderboard_date: date = None,
            limit: int = 50
    ) -> List[LeaderboardEntry]:
        """Get leaderboard entries"""
        query = self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.leaderboard_type == leaderboard_type,
                LeaderboardEntry.is_active == True
            )
        )

        # Add group filter for group leaderboards
        if group_id:
            query = query.filter(LeaderboardEntry.group_id == group_id)

        # Add date filter for daily leaderboards
        if leaderboard_date:
            query = query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)
        elif leaderboard_type == LeaderboardType.DAILY:
            # Default to today for daily leaderboards
            query = query.filter(LeaderboardEntry.leaderboard_date == date.today())

        return query.order_by(asc(LeaderboardEntry.rank)).limit(limit).all()

    def get_user_rank(
            self,
            user_id: int,
            leaderboard_type: LeaderboardType,
            group_id: int = None,
            leaderboard_date: date = None
    ) -> Optional[LeaderboardEntry]:
        """Get user's rank in specific leaderboard"""
        query = self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_type == leaderboard_type,
                LeaderboardEntry.is_active == True
            )
        )

        if group_id:
            query = query.filter(LeaderboardEntry.group_id == group_id)

        if leaderboard_date:
            query = query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)
        elif leaderboard_type == LeaderboardType.DAILY:
            query = query.filter(LeaderboardEntry.leaderboard_date == date.today())

        return query.first()

    def update_leaderboard(
            self,
            leaderboard_type: LeaderboardType,
            user_rankings: List[Dict[str, Any]],
            group_id: int = None,
            leaderboard_date: date = None
    ) -> bool:
        """Update entire leaderboard with new rankings"""
        try:
            # Clear existing entries for this leaderboard
            query = self.db.query(LeaderboardEntry).filter(
                and_(
                    LeaderboardEntry.leaderboard_type == leaderboard_type,
                    LeaderboardEntry.is_active == True
                )
            )

            if group_id:
                query = query.filter(LeaderboardEntry.group_id == group_id)

            if leaderboard_date:
                query = query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)
            elif leaderboard_type == LeaderboardType.DAILY:
                query = query.filter(LeaderboardEntry.leaderboard_date == date.today())

            # Soft delete existing entries
            existing_entries = query.all()
            for entry in existing_entries:
                entry.is_active = False

            # Create new entries
            new_entries = []
            for rank, user_data in enumerate(user_rankings, 1):
                entry_data = {
                    "user_id": user_data["user_id"],
                    "leaderboard_type": leaderboard_type,
                    "group_id": group_id,
                    "leaderboard_date": leaderboard_date if leaderboard_date else (
                        date.today() if leaderboard_type == LeaderboardType.DAILY else None),
                    "rank": rank,
                    "points": user_data["points"],
                    "user_full_name": user_data["user_full_name"]
                }
                new_entries.append(LeaderboardEntry(**entry_data))

            self.db.add_all(new_entries)
            self._commit()
            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_daily_first_finishes_count(self, user_id: int) -> int:
        """Get count of times user finished #1 in daily leaderboards"""
        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_type == LeaderboardType.DAILY,
                LeaderboardEntry.rank == 1,
                LeaderboardEntry.is_active == True
            )
        ).count()

    def get_position_improvements_count(self, user_id: int) -> int:
        """Get count of position improvements (simplified calculation)"""
        # This would require storing previous ranks and comparing
        # For now, return a simplified count based on rank <= 3 appearances
        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.rank <= 3,
                LeaderboardEntry.is_active == True
            )
        ).count()

    def get_user_best_rank(self, user_id: int, leaderboard_type: LeaderboardType) -> Optional[int]:
        """Get user's best (lowest) rank in leaderboard type"""
        result = self.db.query(func.min(LeaderboardEntry.rank)).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_type == leaderboard_type,
                LeaderboardEntry.is_active == True
            )
        ).scalar()
        return result

    def get_user_leaderboard_history(self, user_id: int, days: int = 30) -> List[LeaderboardEntry]:
        """Get user's leaderboard history for specified days"""
        cutoff_date = date.today() - timedelta(days=days)

        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_date >= cutoff_date,
                LeaderboardEntry.is_active == True
            )
        ).order_by(desc(LeaderboardEntry.leaderboard_date)).all()

    def get_top_performers(self, leaderboard_type: LeaderboardType, limit: int = 10) -> List[LeaderboardEntry]:
        """Get consistent top performers across time periods"""
        if leaderboard_type == LeaderboardType.ALL_TIME:
            return self.get_leaderboard(leaderboard_type, limit=limit)

        # For daily leaderboards, get users who frequently appear in top 3
        top_users = self.db.query(
            LeaderboardEntry.user_id,
            LeaderboardEntry.user_full_name,
            func.count(LeaderboardEntry.id).label('top_appearances'),
            func.avg(LeaderboardEntry.rank).label('avg_rank'),
            func.sum(LeaderboardEntry.points).label('total_points')
        ).filter(
            and_(
                LeaderboardEntry.leaderboard_type == leaderboard_type,
                LeaderboardEntry.rank <= 3,
                LeaderboardEntry.is_active == True
            )
        ).group_by(
            LeaderboardEntry.user_id,
            LeaderboardEntry.user_full_name
        ).order_by(
            desc('top_appearances'),
            asc('avg_rank')
        ).limit(limit).all()

        # Convert to LeaderboardEntry format for consistency
        entries = []
        for rank, user_data in enumerate(top_users, 1):
            entry = LeaderboardEntry(
                user_id=user_data.user_id,
                leaderboard_type=leaderboard_type,
                rank=rank,
                points=int(user_data.total_points),
                user_full_name=user_data.user_full_name
            )
            entries.append(entry)

        return entries

    def get_group_leaderboard_stats(self, group_id: int) -> Dict[str, Any]:
        """Get statistics for group leaderboards"""
        # All-time group leaderboard
        all_time_entries = self.get_leaderboard(LeaderboardType.ALL_TIME, group_id=group_id)

        # Recent daily entries
        recent_date = date.today()
        daily_entries = self.get_leaderboard(LeaderboardType.DAILY, group_id=group_id, leaderboard_date=recent_date)

        return {
            "group_id": group_id,
            "all_time_participants": len(all_time_entries),
            "daily_participants": len(daily_entries),
            "total_points_today": sum(e.points for e in daily_entries),
            "average_points_today": sum(e.points for e in daily_entries) / len(daily_entries) if daily_entries else 0,
            "top_performer_all_time": all_time_entries[0] if all_time_entries else None,
            "top_performer_today": daily_entries[0] if daily_entries else None
        }

    def get_leaderboard_engagement(self, learning_center_id: int, days: int = 30) -> Dict[str, Any]:
        """Get leaderboard engagement statistics for learning center"""
        cutoff_date = date.today() - timedelta(days=days)

        # Get all entries for this learning center (would need to join through user->center)
        # For now, simplified implementation
        from app.models.user import User, UserCenterRole

        recent_entries = self.db.query(LeaderboardEntry).join(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                LeaderboardEntry.leaderboard_date >= cutoff_date,
                LeaderboardEntry.is_active == True,
                User.is_active == True,
                UserCenterRole.is_active == True
            )
        ).all()

        unique_participants = len(set(entry.user_id for entry in recent_entries))
        total_entries = len(recent_entries)

        # Daily engagement
        daily_stats = {}
        for entry in recent_entries:
            if entry.leaderboard_date:
                date_str = entry.leaderboard_date.isoformat()
                if date_str not in daily_stats:
                    daily_stats[date_str] = {"participants": set(), "total_points": 0}
                daily_stats[date_str]["participants"].add(entry.user_id)
                daily_stats[date_str]["total_points"] += entry.points

        # Convert sets to counts
        for date_str in daily_stats:
            daily_stats[date_str]["participants"] = len(daily_stats[date_str]["participants"])

        return {
            "learning_center_id": learning_center_id,
            "period_days": days,
            "unique_participants": unique_participants,
            "total_leaderboard_entries": total_entries,
            "daily_stats": daily_stats,
            "average_daily_participants": sum(day["participants"] for day in daily_stats.values()) / len(
                daily_stats) if daily_stats else 0
        }

    def cleanup_old_daily_leaderboards(self, days_to_keep: int = 90) -> int:
        """Clean up old daily leaderboard entries"""
        cutoff_date = date.today() - timedelta(days=days_to_keep)

        old_entries = self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.leaderboard_type == LeaderboardType.DAILY,
                LeaderboardEntry.leaderboard_date < cutoff_date,
                LeaderboardEntry.is_active == True
            )
        ).all()

        for entry in old_entries:
            entry.is_active = False

        self._commit()
        return len(old_entries)

    def get_rank_distribution(self, leaderboard_type: LeaderboardType, group_id: int = None) -> Dict[str, Any]:
        """Get distribution of ranks (how many users at each rank level)"""
        query = self.db.query(
            func.case([
                (LeaderboardEntry.rank == 1, '1st Place'),
                (LeaderboardEntry.rank <= 3, 'Top 3'),
                (LeaderboardEntry.rank <= 10, 'Top 10'),
                (LeaderboardEntry.rank <= 50, 'Top 50')
            ], else_='Below 50').label('rank_category'),
            func.count(LeaderboardEntry.user_id.distinct()).label('user_count')
        ).filter(
            and_(
                LeaderboardEntry.leaderboard_type == leaderboard_type,
                LeaderboardEntry.is_active == True
            )
        )

        if group_id:
            query = query.filter(LeaderboardEntry.group_id == group_id)

        if leaderboard_type == LeaderboardType.DAILY:
            # Use recent data for daily leaderboards
            recent_date = date.today() - timedelta(days=7)
            query = query.filter(LeaderboardEntry.leaderboard_date >= recent_date)

        results = query.group_by('rank_category').all()

        distribution = {category: count for category, count in results}

        return {
            "leaderboard_type": leaderboard_type.value,
            "group_id": group_id,
            "distribution": distribution,
            "total_participants": sum(distribution.values())
        }

    def get_leaderboard_trends(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user's leaderboard trends over time"""
        cutoff_date = date.today() - timedelta(days=days)

        entries = self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_date >= cutoff_date,
                LeaderboardEntry.is_active == True
            )
        ).order_by(asc(LeaderboardEntry.leaderboard_date)).all()

        if not entries:
            return {
                "user_id": user_id,
                "period_days": days,
                "trend": "no_data",
                "entries": []
            }

        # Calculate trend
        first_rank = entries[0].rank
        last_rank = entries[-1].rank

        trend = "stable"
        if last_rank < first_rank:
            trend = "improving"
        elif last_rank > first_rank:
            trend = "declining"

        # Format data for response
        trend_data = []
        for entry in entries:
            trend_data.append({
                "date": entry.leaderboard_date.isoformat() if entry.leaderboard_date else None,
                "rank": entry.rank,
                "points": entry.points,
                "leaderboard_type": entry.leaderboard_type.value
            })

        return {
            "user_id": user_id,
            "period_days": days,
            "trend": trend,
            "rank_change": last_rank - first_rank,
            "best_rank": min(e.rank for e in entries),
            "worst_rank": max(e.rank for e in entries),
            "average_rank": sum(e.rank for e in entries) / len(entries),
            "total_points": sum(e.points for e in entries),
            "entries": trend_data
        }