from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, date, timedelta
from app.models.badge import UserBadge
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.constants.badge_types import BadgeType, BadgeCategory, get_level_for_count, get_next_level_threshold, \
    is_level_badge


class BadgeRepository(BaseRepository[UserBadge]):
    def __init__(self):
        super().__init__(UserBadge)

    def get_user_badges(self, db: Session, user_id: int, active_only: bool = True) -> List[UserBadge]:
        """Get all badges for a user"""
        query = db.query(UserBadge).filter(UserBadge.user_id == user_id).options(
            joinedload(UserBadge.user)
        )

        if active_only:
            query = query.filter(UserBadge.is_active == True)

        return query.order_by(desc(UserBadge.earned_at)).all()

    def get_user_badge_by_type(self, db: Session, user_id: int, badge_type: BadgeType) -> Optional[UserBadge]:
        """Get a specific badge type for a user (for level badges)"""
        return db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.badge_type == badge_type,
                UserBadge.is_active == True
            )
        ).first()

    def get_badges_by_type(self, db: Session, badge_type: BadgeType, skip: int = 0, limit: int = 100) -> List[
        UserBadge]:
        """Get all badges of a specific type"""
        return db.query(UserBadge).filter(
            and_(UserBadge.badge_type == badge_type, UserBadge.is_active == True)
        ).options(joinedload(UserBadge.user)).order_by(desc(UserBadge.level), desc(UserBadge.count)).offset(skip).limit(
            limit).all()

    def get_recent_badges(self, db: Session, learning_center_id: int, days: int = 7, limit: int = 50) -> List[
        UserBadge]:
        """Get recently earned badges in a learning center"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return db.query(UserBadge).join(User).filter(
            and_(
                User.learning_center_id == learning_center_id,
                UserBadge.earned_at >= cutoff_date,
                UserBadge.is_active == True
            )
        ).options(joinedload(UserBadge.user)).order_by(desc(UserBadge.earned_at)).limit(limit).all()

    def award_achievement_badge(
            self,
            db: Session,
            user_id: int,
            badge_type: BadgeType,
            context: Optional[str] = None
    ) -> UserBadge:
        """Award an achievement badge (can have multiple instances)"""
        badge_data = {
            "user_id": user_id,
            "badge_type": badge_type,
            "level": 1,
            "count": 1,
            "context_data": context,
            "earned_at": datetime.utcnow()
        }

        return self.create(db, badge_data)

    def update_level_badge(
            self,
            db: Session,
            user_id: int,
            badge_type: BadgeType,
            new_count: int,
            context: Optional[str] = None
    ) -> UserBadge:
        """Update or create a level badge based on new count"""
        existing_badge = self.get_user_badge_by_type(db, user_id, badge_type)
        new_level = get_level_for_count(badge_type, new_count)

        if existing_badge:
            # Update existing badge
            old_level = existing_badge.level
            existing_badge.count = new_count
            existing_badge.level = new_level
            existing_badge.context_data = context

            # If level increased, update earned_at
            if new_level > old_level:
                existing_badge.earned_at = datetime.utcnow()

            db.commit()
            db.refresh(existing_badge)
            return existing_badge
        else:
            # Create new badge
            if new_level > 0:  # Only create if threshold is met
                badge_data = {
                    "user_id": user_id,
                    "badge_type": badge_type,
                    "level": new_level,
                    "count": new_count,
                    "context_data": context,
                    "earned_at": datetime.utcnow()
                }
                return self.create(db, badge_data)

        return None

    def increment_badge_progress(
            self,
            db: Session,
            user_id: int,
            badge_type: BadgeType,
            increment: int = 1,
            context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Increment progress for a badge type and return progress info"""
        if is_level_badge(badge_type):
            existing_badge = self.get_user_badge_by_type(db, user_id, badge_type)
            current_count = existing_badge.count if existing_badge else 0
            new_count = current_count + increment

            old_level = existing_badge.level if existing_badge else 0
            new_level = get_level_for_count(badge_type, new_count)
            next_threshold = get_next_level_threshold(badge_type, new_count)

            # Update badge
            badge = self.update_level_badge(db, user_id, badge_type, new_count, context)

            return {
                "badge_type": badge_type,
                "old_count": current_count,
                "new_count": new_count,
                "old_level": old_level,
                "new_level": new_level,
                "level_up": new_level > old_level,
                "next_threshold": next_threshold,
                "progress_to_next": (
                            (new_count - (next_threshold - increment)) / increment * 100) if next_threshold else 100,
                "badge_earned": badge is not None
            }
        else:
            # Achievement badge - just award it
            badge = self.award_achievement_badge(db, user_id, badge_type, context)
            return {
                "badge_type": badge_type,
                "badge_earned": True,
                "level_up": False,
                "achievement": True
            }

    def get_badge_leaderboard(
            self,
            db: Session,
            badge_type: Optional[BadgeType] = None,
            learning_center_id: Optional[int] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get badge leaderboard (users with most badges or highest levels)"""
        if badge_type:
            # Specific badge type leaderboard
            query = db.query(
                UserBadge.user_id,
                User.full_name,
                UserBadge.level,
                UserBadge.count,
                UserBadge.earned_at
            ).join(User).filter(
                and_(UserBadge.badge_type == badge_type, UserBadge.is_active == True)
            )

            if learning_center_id:
                query = query.filter(User.learning_center_id == learning_center_id)

            if is_level_badge(badge_type):
                query = query.order_by(desc(UserBadge.level), desc(UserBadge.count))
            else:
                query = query.order_by(desc(UserBadge.count), desc(UserBadge.earned_at))

            results = query.limit(limit).all()

            return [
                {
                    "rank": idx + 1,
                    "user_id": user_id,
                    "full_name": full_name,
                    "level": level,
                    "count": count,
                    "earned_at": earned_at
                }
                for idx, (user_id, full_name, level, count, earned_at) in enumerate(results)
            ]
        else:
            # Overall badge leaderboard (total badges)
            query = db.query(
                UserBadge.user_id,
                User.full_name,
                func.count(UserBadge.id).label('total_badges'),
                func.max(UserBadge.earned_at).label('latest_badge')
            ).join(User).filter(UserBadge.is_active == True)

            if learning_center_id:
                query = query.filter(User.learning_center_id == learning_center_id)

            results = query.group_by(UserBadge.user_id, User.full_name).order_by(
                desc('total_badges'), desc('latest_badge')
            ).limit(limit).all()

            return [
                {
                    "rank": idx + 1,
                    "user_id": user_id,
                    "full_name": full_name,
                    "total_badges": total_badges,
                    "latest_badge": latest_badge
                }
                for idx, (user_id, full_name, total_badges, latest_badge) in enumerate(results)
            ]

    def get_badge_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive badge statistics"""
        base_query = db.query(UserBadge).join(User).filter(UserBadge.is_active == True)

        if learning_center_id:
            base_query = base_query.filter(User.learning_center_id == learning_center_id)

        total_badges = base_query.count()
        unique_earners = base_query.with_entities(UserBadge.user_id).distinct().count()

        # Badge type distribution
        type_distribution = base_query.with_entities(
            UserBadge.badge_type,
            func.count(UserBadge.id).label('count')
        ).group_by(UserBadge.badge_type).all()

        # Level badge statistics
        level_badges = base_query.filter(
            UserBadge.badge_type.in_([
                BadgeType.LESSON_MASTER,
                BadgeType.WEEKLIST_SOLVER,
                BadgeType.TOP_PERFORMER,
                BadgeType.POSITION_CLIMBER
            ])
        )

        level_stats = level_badges.with_entities(
            UserBadge.badge_type,
            func.max(UserBadge.level).label('highest_level'),
            func.avg(UserBadge.level).label('avg_level'),
            func.count(UserBadge.id).label('count')
        ).group_by(UserBadge.badge_type).all()

        # Recent activity (last 30 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        recent_badges = base_query.filter(UserBadge.earned_at >= recent_cutoff).count()

        return {
            "total_badges_awarded": total_badges,
            "unique_badge_holders": unique_earners,
            "recent_badges_30_days": recent_badges,
            "average_badges_per_user": round(total_badges / unique_earners, 2) if unique_earners > 0 else 0,
            "type_distribution": {badge_type: count for badge_type, count in type_distribution},
            "level_badge_stats": {
                badge_type: {
                    "highest_level": highest_level,
                    "average_level": float(avg_level),
                    "total_holders": count
                }
                for badge_type, highest_level, avg_level, count in level_stats
            }
        }

    def get_user_badge_progress(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive badge progress for a user"""
        user_badges = self.get_user_badges(db, user_id)

        # Organize badges by category
        achievement_badges = [b for b in user_badges if not is_level_badge(b.badge_type)]
        level_badges = [b for b in user_badges if is_level_badge(b.badge_type)]

        # Get progress to next level for each level badge type
        level_progress = {}
        for badge_type in [BadgeType.LESSON_MASTER, BadgeType.WEEKLIST_SOLVER, BadgeType.TOP_PERFORMER,
                           BadgeType.POSITION_CLIMBER]:
            existing_badge = self.get_user_badge_by_type(db, user_id, badge_type)
            current_count = existing_badge.count if existing_badge else 0
            current_level = existing_badge.level if existing_badge else 0
            next_threshold = get_next_level_threshold(badge_type, current_count)

            level_progress[badge_type] = {
                "current_count": current_count,
                "current_level": current_level,
                "next_threshold": next_threshold,
                "progress_percentage": (current_count / next_threshold * 100) if next_threshold else 100
            }

        return {
            "total_badges": len(user_badges),
            "achievement_badges": len(achievement_badges),
            "level_badges": len(level_badges),
            "badges": [
                {
                    "badge_type": badge.badge_type,
                    "level": badge.level,
                    "count": badge.count,
                    "earned_at": badge.earned_at,
                    "is_level_badge": is_level_badge(badge.badge_type)
                }
                for badge in user_badges
            ],
            "level_progress": level_progress
        }

    def cleanup_inactive_badges(self, db: Session, days: int = 365) -> int:
        """Mark old badges as inactive (soft delete)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        updated_count = db.query(UserBadge).filter(
            and_(
                UserBadge.earned_at < cutoff_date,
                UserBadge.is_active == True
            )
        ).update({"is_active": False})

        db.commit()
        return updated_count