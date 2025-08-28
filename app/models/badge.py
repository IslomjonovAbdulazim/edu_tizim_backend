from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class UserBadge(BaseModel):
    __tablename__ = "user_badges"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="user_badges")

    # Badge information
    badge_type = Column(String(50), nullable=False)  # From BadgeType enum
    level = Column(Integer, nullable=False, default=1)  # For level badges
    count = Column(Integer, nullable=False, default=1)  # How many times achieved

    # Badge metadata
    description = Column(String(255), nullable=True)  # Custom description for this instance
    earned_at = Column(DateTime, default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Additional context (optional)
    context_data = Column(String(500), nullable=True)  # JSON string for additional context

    def __str__(self):
        return f"UserBadge(user='{self.user.full_name}', type='{self.badge_type}', level={self.level})"

    @property
    def badge_info(self):
        """Get badge information from constants"""
        from app.constants.badge_types import BADGE_INFO
        return BADGE_INFO.get(self.badge_type, {})

    @property
    def name(self):
        """Get badge name"""
        info = self.badge_info
        if self.level > 1:
            return f"{info.get('name', 'Unknown')} Level {self.level}"
        return info.get('name', 'Unknown Badge')

    @property
    def icon(self):
        """Get badge icon"""
        return self.badge_info.get('icon', '🏅')

    @property
    def category(self):
        """Get badge category"""
        return self.badge_info.get('category', 'unknown')

    @property
    def is_level_badge(self):
        """Check if this is a level badge"""
        from app.constants.badge_types import BadgeCategory
        return self.category == BadgeCategory.LEVEL