from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Float, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date
from .base import BaseModel


class AllTimeLeaderboard(BaseModel):
    """All-time leaderboard model - cumulative points across all time"""
    __tablename__ = "all_time_leaderboards"

    # Core identification
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Ranking data
    rank = Column(Integer, nullable=False)
    total_points = Column(Integer, nullable=False, default=0)

    # Performance metrics
    points_this_month = Column(Integer, nullable=False, default=0)
    lessons_completed = Column(Integer, nullable=False, default=0)
    days_active = Column(Integer, nullable=False, default=0)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    average_daily_points = Column(Float, nullable=False, default=0.0)

    # Activity tracking
    last_activity_date = Column(Date, nullable=True)
    first_activity_date = Column(Date, nullable=True)

    # Denormalized user data for performance
    user_full_name = Column(String(255), nullable=False)
    user_avatar_url = Column(String(500), nullable=True)

    # Metadata
    last_calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    learning_center = relationship("LearningCenter", back_populates="all_time_leaderboards")
    user = relationship("User", back_populates="all_time_leaderboard_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint('learning_center_id', 'user_id', name='uix_all_time_center_user'),
    )

    @property
    def is_active_this_month(self):
        """Check if user has points this month"""
        return self.points_this_month > 0

    @property
    def days_since_last_activity(self):
        """Calculate days since last activity"""
        if not self.last_activity_date:
            return None
        return (date.today() - self.last_activity_date).days

    @property
    def is_recent_participant(self):
        """Check if user was active in last 7 days"""
        days_since = self.days_since_last_activity
        return days_since is not None and days_since <= 7

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'is_active_this_month': self.is_active_this_month,
            'days_since_last_activity': self.days_since_last_activity,
            'is_recent_participant': self.is_recent_participant
        })
        return data