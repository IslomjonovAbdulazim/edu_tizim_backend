from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.badge import UserBadge
from app.models.user import User
from app.repositories.badge_repository import BadgeRepository
from app.core.exceptions import ResourceNotFoundException, InvalidDataException


class BadgeService:
    """Service for managing user badges and notifications"""

    def __init__(self):
        self.badge_repo = BadgeRepository()

    def mark_badge_as_seen(self, db: Session, badge_id: int, user_id: int) -> Dict[str, Any]:
        """Mark a specific badge as seen by the user"""

        badge = db.query(UserBadge).filter(
            UserBadge.id == badge_id,
            UserBadge.user_id == user_id,
            UserBadge.is_active == True
        ).first()

        if not badge:
            raise ResourceNotFoundException("Badge", "Badge not found or doesn't belong to user")

        if badge.is_seen:
            return {
                "success": True,
                "message": "Badge was already marked as seen",
                "badge_id": badge_id,
                "was_already_seen": True
            }

        # Mark as seen
        badge.mark_as_seen()
        db.commit()

        return {
            "success": True,
            "message": "Badge marked as seen",
            "badge_id": badge_id,
            "seen_at": badge.seen_at,
            "was_already_seen": False
        }

    def mark_badges_as_seen(self, db: Session, badge_ids: List[int], user_id: int) -> Dict[str, Any]:
        """Mark multiple badges as seen"""

        badges = db.query(UserBadge).filter(
            UserBadge.id.in_(badge_ids),
            UserBadge.user_id == user_id,
            UserBadge.is_active == True
        ).all()

        if not badges:
            raise ResourceNotFoundException("Badges", "No valid badges found for user")

        marked_count = 0
        already_seen_count = 0

        for badge in badges:
            if not badge.is_seen:
                badge.mark_as_seen()
                marked_count += 1
            else:
                already_seen_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Processed {len(badges)} badges",
            "marked_as_seen": marked_count,
            "already_seen": already_seen_count,
            "badge_ids": badge_ids
        }

    def mark_all_badges_as_seen(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Mark all unseen badges as seen for a user"""

        unseen_badges = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.is_seen == False,
            UserBadge.is_active == True
        ).all()

        if not unseen_badges:
            return {
                "success": True,
                "message": "No unseen badges found",
                "marked_count": 0
            }

        for badge in unseen_badges:
            badge.mark_as_seen()

        db.commit()

        return {
            "success": True,
            "message": f"Marked {len(unseen_badges)} badges as seen",
            "marked_count": len(unseen_badges)
        }

    def get_unseen_badges(self, db: Session, user_id: int) -> List[UserBadge]:
        """Get all unseen badges for a user"""

        return db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.is_seen == False,
            UserBadge.is_active == True
        ).order_by(UserBadge.earned_at.desc()).all()

    def get_badge_notifications(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get badge notification summary for user"""

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResourceNotFoundException("User", "User not found")

        unseen_badges = self.get_unseen_badges(db, user_id)

        # Recent achievements (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_badges = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.earned_at >= yesterday,
            UserBadge.is_active == True
        ).count()

        # Recent level ups (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_level_ups = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.earned_at >= week_ago,
            UserBadge.level > 1,  # Only level 2+ badges
            UserBadge.is_active == True
        ).count()

        return {
            "user_id": user_id,
            "unseen_badges_count": len(unseen_badges),
            "has_new_badges": len(unseen_badges) > 0,
            "unseen_badges": unseen_badges,
            "new_achievements_24h": recent_badges,
            "recent_level_ups_7d": recent_level_ups,
            "total_badges": len(user.user_badges)
        }

    def award_badge_with_notification(self, db: Session, user_id: int, badge_type: str,
                                      level: int = 1, count: int = 1, context: str = None) -> Dict[str, Any]:
        """Award a badge and automatically mark it as unseen for notification"""

        # Check if badge already exists
        existing_badge = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.badge_type == badge_type,
            UserBadge.is_active == True
        ).first()

        if existing_badge:
            # Update existing badge
            old_level = existing_badge.level
            old_count = existing_badge.count

            existing_badge.level = max(existing_badge.level, level)
            existing_badge.count = max(existing_badge.count, count)
            existing_badge.context = context
            existing_badge.earned_at = datetime.utcnow()

            # Mark as unseen if significant change
            if existing_badge.level > old_level or existing_badge.count > old_count:
                existing_badge.mark_as_unseen()

            db.commit()
            db.refresh(existing_badge)

            return {
                "success": True,
                "message": "Badge updated successfully",
                "badge": existing_badge,
                "is_new_badge": False,
                "level_up": existing_badge.level > old_level,
                "count_increase": existing_badge.count > old_count
            }
        else:
            # Create new badge (automatically unseen)
            new_badge = UserBadge(
                user_id=user_id,
                badge_type=badge_type,
                level=level,
                count=count,
                context=context,
                earned_at=datetime.utcnow(),
                is_seen=False,  # New badges are always unseen
                is_active=True
            )

            db.add(new_badge)
            db.commit()
            db.refresh(new_badge)

            return {
                "success": True,
                "message": "New badge awarded!",
                "badge": new_badge,
                "is_new_badge": True,
                "level_up": False,
                "count_increase": False
            }

    def get_user_badge_summary(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive badge summary for user dashboard"""

        user_badges = self.badge_repo.get_user_badges(db, user_id)
        unseen_badges = [b for b in user_badges if not b.is_seen]

        # Group badges by type
        badge_types = {}
        for badge in user_badges:
            if badge.badge_type not in badge_types:
                badge_types[badge.badge_type] = {
                    "badge_type": badge.badge_type,
                    "badge_name": badge.badge_name,
                    "badge_icon": badge.badge_icon,
                    "highest_level": badge.level,
                    "total_count": badge.count,
                    "is_seen": badge.is_seen,
                    "latest_earned": badge.earned_at
                }
            else:
                # Update with highest level/count
                badge_types[badge.badge_type]["highest_level"] = max(
                    badge_types[badge.badge_type]["highest_level"], badge.level
                )
                badge_types[badge.badge_type]["total_count"] = max(
                    badge_types[badge.badge_type]["total_count"], badge.count
                )

        return {
            "user_id": user_id,
            "total_badges": len(user_badges),
            "unseen_badges": len(unseen_badges),
            "badge_types": list(badge_types.values()),
            "recent_badges": sorted(user_badges, key=lambda x: x.earned_at, reverse=True)[:5],
            "has_notifications": len(unseen_badges) > 0
        }

    def cleanup_old_seen_badges(self, db: Session, days: int = 90) -> int:
        """Clean up old seen badges to keep database lean"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Only delete very old badges that are seen and not the user's best badges
        deleted_count = db.query(UserBadge).filter(
            UserBadge.earned_at < cutoff_date,
            UserBadge.is_seen == True,
            UserBadge.level <= 3,  # Keep high-level badges
            UserBadge.is_active == True
        ).update({"is_active": False})

        db.commit()
        return deleted_count

    def reset_badge_notifications(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Reset all badge notifications for a user (mark all as unseen)"""

        updated_count = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.is_active == True
        ).update({
            "is_seen": False,
            "seen_at": None
        })

        db.commit()

        return {
            "success": True,
            "message": f"Reset notifications for {updated_count} badges",
            "updated_count": updated_count
        }