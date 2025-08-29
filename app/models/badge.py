from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class UserBadge(BaseModel):
    """User badge model - tracks badges earned by users"""
    __tablename__ = "user_badges"

    # User and badge references
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_type_id = Column(Integer, ForeignKey("badge_types.id"), nullable=False)

    # Badge instance details
    level = Column(Integer, default=1)  # For progressive badges
    count = Column(Integer, default=1)  # For repeatable badges

    # Earning details
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    context = Column(JSON, nullable=True)  # Context when earned (rank, points, etc.)

    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Show prominently on profile

    # Relationships
    user = relationship("User", back_populates="user_badges")
    badge_type = relationship("BadgeType", back_populates="user_badges")

    def __str__(self):
        level_str = f" (Level {self.level})" if self.level > 1 else ""
        return f"UserBadge({self.user_id}, {self.badge_type.name}{level_str})"

    @property
    def badge_name(self):
        """Get badge name with level if applicable"""
        if self.badge_type.is_progressive and self.level > 1:
            return f"{self.badge_type.name} (Level {self.level})"
        return self.badge_type.name

    @property
    def badge_icon(self):
        """Get badge icon"""
        return self.badge_type.icon

    @property
    def badge_description(self):
        """Get badge description"""
        return self.badge_type.description

    @property
    def badge_color_primary(self):
        """Get badge primary color"""
        return self.badge_type.color_primary

    @property
    def badge_color_secondary(self):
        """Get badge secondary color"""
        return self.badge_type.color_secondary

    @property
    def badge_rarity(self):
        """Get badge rarity"""
        return self.badge_type.rarity

    @property
    def is_daily_badge(self):
        """Check if this is a daily badge"""
        return self.badge_type.is_daily

    @property
    def is_streak_badge(self):
        """Check if this is a streak badge"""
        return self.badge_type.is_streak

    @property
    def is_achievement_badge(self):
        """Check if this is an achievement badge"""
        return self.badge_type.is_achievement

    @property
    def can_level_up(self):
        """Check if badge can be leveled up"""
        return (self.badge_type.is_progressive and
                self.level < self.badge_type.max_level)

    @property
    def is_max_level(self):
        """Check if badge is at maximum level"""
        return (not self.badge_type.is_progressive or
                self.level >= self.badge_type.max_level)

    def get_context_value(self, key: str, default=None):
        """Get value from context data"""
        if not self.context:
            return default
        return self.context.get(key, default)

    def level_up(self):
        """Level up the badge if possible"""
        if self.can_level_up:
            self.level += 1
            return True
        return False

    def increment_count(self):
        """Increment count for repeatable badges"""
        if self.badge_type.is_repeatable:
            self.count += 1
            self.earned_at = datetime.utcnow()  # Update earned time
            return True
        return False

    @classmethod
    def create_daily_badge(
            cls,
            user_id: int,
            badge_type_id: int,
            rank: int,
            points: int,
            date: str = None
    ):
        """Factory method for daily badges"""
        context = {
            "rank": rank,
            "points": points,
            "leaderboard_type": "daily"
        }
        if date:
            context["date"] = date

        return cls(
            user_id=user_id,
            badge_type_id=badge_type_id,
            level=1,
            count=1,
            context=context,
            is_featured=rank <= 3  # Feature top 3 badges
        )

    @classmethod
    def create_achievement_badge(
            cls,
            user_id: int,
            badge_type_id: int,
            achievement_data: dict = None
    ):
        """Factory method for achievement badges"""
        return cls(
            user_id=user_id,
            badge_type_id=badge_type_id,
            level=1,
            count=1,
            context=achievement_data or {},
            is_featured=True  # Feature achievements
        )

    @classmethod
    def create_streak_badge(
            cls,
            user_id: int,
            badge_type_id: int,
            streak_days: int,
            level: int = 1
    ):
        """Factory method for streak badges"""
        return cls(
            user_id=user_id,
            badge_type_id=badge_type_id,
            level=level,
            count=1,
            context={"streak_days": streak_days},
            is_featured=True  # Feature streak badges
        )

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'badge_name': self.badge_name,
            'badge_icon': self.badge_icon,
            'badge_description': self.badge_description,
            'badge_color_primary': self.badge_color_primary,
            'badge_color_secondary': self.badge_color_secondary,
            'badge_rarity': self.badge_rarity,
            'is_daily_badge': self.is_daily_badge,
            'is_streak_badge': self.is_streak_badge,
            'is_achievement_badge': self.is_achievement_badge,
            'can_level_up': self.can_level_up,
            'is_max_level': self.is_max_level
        })
        return data