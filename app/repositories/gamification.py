from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from datetime import date, timedelta
from app.models import LeaderboardEntry, UserBadge, LeaderboardType, BadgeCategory
from app.repositories.base import BaseRepository


class LeaderboardRepository(BaseRepository[LeaderboardEntry]):
    def __init__(self, db: Session):
        super().__init__(LeaderboardEntry, db)

    def get_leaderboard(
            self,
            leaderboard_type: LeaderboardType,
            group_id: Optional[int] = None,
            leaderboard_date: Optional[date] = None,
            limit: int = 50
    ) -> List[LeaderboardEntry]:
        """Get leaderboard entries"""
        query = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.leaderboard_type == leaderboard_type
        )

        if group_id:
            query = query.filter(LeaderboardEntry.group_id == group_id)

        if leaderboard_date:
            query = query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)
        elif leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]:
            # For 3-daily leaderboards, use today's date if not specified
            query = query.filter(LeaderboardEntry.leaderboard_date == date.today())

        return query.order_by(LeaderboardEntry.rank).limit(limit).all()

    def get_user_rank(
            self,
            user_id: int,
            leaderboard_type: LeaderboardType,
            group_id: Optional[int] = None,
            leaderboard_date: Optional[date] = None
    ) -> Optional[LeaderboardEntry]:
        """Get user's rank in specific leaderboard"""
        query = self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_type == leaderboard_type
            )
        )

        if group_id:
            query = query.filter(LeaderboardEntry.group_id == group_id)

        if leaderboard_date:
            query = query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)
        elif leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]:
            query = query.filter(LeaderboardEntry.leaderboard_date == date.today())

        return query.first()

    def update_leaderboard(
            self,
            leaderboard_type: LeaderboardType,
            user_rankings: List[Dict],  # [{user_id, points, user_full_name}, ...]
            group_id: Optional[int] = None,
            leaderboard_date: Optional[date] = None
    ) -> List[LeaderboardEntry]:
        """Update entire leaderboard with new rankings"""
        if leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]:
            if not leaderboard_date:
                leaderboard_date = date.today()
        else:
            leaderboard_date = None  # All-time leaderboards don't have dates

        # Delete existing entries for this leaderboard
        delete_query = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.leaderboard_type == leaderboard_type
        )

        if group_id:
            delete_query = delete_query.filter(LeaderboardEntry.group_id == group_id)
        if leaderboard_date:
            delete_query = delete_query.filter(LeaderboardEntry.leaderboard_date == leaderboard_date)

        delete_query.delete()

        # Create new entries
        entries = []
        for i, user_data in enumerate(user_rankings, 1):
            entry = LeaderboardEntry(
                user_id=user_data['user_id'],
                leaderboard_type=leaderboard_type,
                group_id=group_id,
                leaderboard_date=leaderboard_date,
                rank=i,
                points=user_data['points'],
                user_full_name=user_data['user_full_name'],
                position_change=user_data.get('position_change', 0),
                previous_rank=user_data.get('previous_rank')
            )
            entries.append(entry)

        self.db.add_all(entries)
        self.db.commit()

        for entry in entries:
            self.db.refresh(entry)

        return entries

    def get_user_position_changes(self, user_id: int, days: int = 7) -> List[LeaderboardEntry]:
        """Get user's position changes over time"""
        cutoff_date = date.today() - timedelta(days=days)
        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.leaderboard_type.in_([
                    LeaderboardType.GLOBAL_3_DAILY,
                    LeaderboardType.GROUP_3_DAILY
                ]),
                LeaderboardEntry.leaderboard_date >= cutoff_date
            )
        ).order_by(LeaderboardEntry.leaderboard_date.desc()).all()

    def get_daily_first_finishes_count(self, user_id: int) -> int:
        """Get count of times user finished first in daily leaderboards"""
        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.rank == 1,
                LeaderboardEntry.leaderboard_type.in_([
                    LeaderboardType.GLOBAL_3_DAILY,
                    LeaderboardType.GROUP_3_DAILY
                ])
            )
        ).count()

    def get_position_improvements_count(self, user_id: int) -> int:
        """Get count of times user improved position"""
        return self.db.query(LeaderboardEntry).filter(
            and_(
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.position_change > 0
            )
        ).count()


class BadgeRepository(BaseRepository[UserBadge]):
    def __init__(self, db: Session):
        super().__init__(UserBadge, db)

    def get_user_badges(self, user_id: int) -> List[UserBadge]:
        """Get all badges for user"""
        return self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.is_active == True
            )
        ).order_by(UserBadge.earned_at.desc()).all()

    def get_user_badge(self, user_id: int, category: BadgeCategory) -> Optional[UserBadge]:
        """Get specific badge for user"""
        return self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.category == category
            )
        ).first()

    def create_or_update_badge(
            self,
            user_id: int,
            category: BadgeCategory,
            level: int,
            title: str,
            description: str,
            image_url: str
    ) -> UserBadge:
        """Create new badge or update existing badge level"""
        existing_badge = self.get_user_badge(user_id, category)

        if existing_badge:
            # Update existing badge level
            existing_badge.level = level
            existing_badge.title = title
            existing_badge.description = description
            existing_badge.image_url = image_url
            existing_badge.earned_at = date.today()
            self.db.commit()
            self.db.refresh(existing_badge)
            return existing_badge
        else:
            # Create new badge
            badge = UserBadge(
                user_id=user_id,
                category=category,
                level=level,
                title=title,
                description=description,
                image_url=image_url,
                earned_at=date.today()
            )
            self.db.add(badge)
            self.db.commit()
            self.db.refresh(badge)
            return badge

    def check_and_award_badges(self, user_id: int, stats: Dict[str, int]) -> List[UserBadge]:
        """Check user stats and award appropriate badges"""
        from app.models.badge_types import (
            get_level_for_count, get_badge_info, LEVEL_THRESHOLDS
        )

        awarded_badges = []

        # Check each badge category
        badge_checks = {
            BadgeCategory.DAILY_FIRST: stats.get('daily_first_finishes', 0),
            BadgeCategory.PERFECT_LESSON: stats.get('perfect_lessons', 0),
            BadgeCategory.WEAKLIST_SOLVER: stats.get('weaklist_solved', 0),
            BadgeCategory.POSITION_CLIMBER: stats.get('position_improvements', 0)
        }

        for category, count in badge_checks.items():
            if count > 0:  # Only check if user has any count for this category
                required_level = get_level_for_count(category.value, count)

                if required_level > 0:
                    current_badge = self.get_user_badge(user_id, category)
                    current_level = current_badge.level if current_badge else 0

                    if required_level > current_level:
                        # Award or upgrade badge
                        badge_info = get_badge_info(category.value, required_level)
                        badge = self.create_or_update_badge(
                            user_id=user_id,
                            category=category,
                            level=required_level,
                            title=badge_info['title'],
                            description=badge_info['description'],
                            image_url=badge_info['image_url']
                        )
                        awarded_badges.append(badge)

        return awarded_badges

    def get_badge_progress(self, user_id: int) -> List[Dict]:
        """Get badge progress for user"""
        from app.models.badge_types import (
            get_level_for_count, get_next_level_threshold, LEVEL_THRESHOLDS
        )

        # Get current stats (this would typically come from other services)
        # For now, we'll return a basic structure
        progress = []

        for category in BadgeCategory:
            current_badge = self.get_user_badge(user_id, category)
            current_level = current_badge.level if current_badge else 0

            # You'll need to implement a way to get current count for each category
            current_count = 0  # Placeholder - implement based on your needs

            next_threshold = get_next_level_threshold(category.value, current_count)
            progress_percentage = (current_count / next_threshold * 100) if next_threshold > 0 else 100

            progress.append({
                'category': category,
                'current_level': current_level,
                'current_count': current_count,
                'next_threshold': next_threshold,
                'progress_percentage': min(100, progress_percentage),
                'can_level_up': current_count >= next_threshold if next_threshold > 0 else False
            })

        return progress

    def get_total_badges_count(self, user_id: int) -> int:
        """Get total number of badges for user"""
        return self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.is_active == True
            )
        ).count()