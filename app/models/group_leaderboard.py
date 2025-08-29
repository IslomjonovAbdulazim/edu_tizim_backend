from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Float, Text, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum
from .base import BaseModel


class LeaderboardType(enum.Enum):
    """Leaderboard type enumeration"""
    DAILY = "daily"
    ALL_TIME = "all_time"


class GroupLeaderboard(BaseModel):
    """Group leaderboard model - supports both daily and all-time group rankings"""
    __tablename__ = "group_leaderboards"

    # Core identification
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False)

    # Date field - only used for daily leaderboards
    leaderboard_date = Column(Date, nullable=True)  # NULL for all-time, date for daily

    # Ranking data
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)

    # Performance metrics
    lessons_completed = Column(Integer, nullable=False, default=0)

    # Daily leaderboard specific fields
    points_today = Column(Integer, nullable=True)  # Only for daily
    previous_rank = Column(Integer, nullable=True)  # Only for daily
    position_change = Column(Integer, nullable=False, default=0)  # Only for daily

    # All-time specific fields
    days_active = Column(Integer, nullable=True)  # Only for all-time
    current_streak = Column(Integer, nullable=True)  # Only for all-time
    average_daily_points = Column(Float, nullable=True)  # Only for all-time

    # Denormalized data for performance
    user_full_name = Column(String(255), nullable=False)
    user_avatar_url = Column(String(500), nullable=True)
    group_name = Column(String(255), nullable=False)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="leaderboard_entries")
    user = relationship("User", back_populates="group_leaderboard_entries")

    # Constraints
    __table_args__ = (
        # For daily leaderboards: unique per group, user, date
        UniqueConstraint('group_id', 'user_id', 'leaderboard_date', 'leaderboard_type',
                         name='uix_group_daily_user'),
        # For all-time leaderboards: unique per group, user
        # This is handled by the combination above since all-time has NULL date
    )

    @property
    def is_daily(self):
        """Check if this is a daily leaderboard entry"""
        return self.leaderboard_type == LeaderboardType.DAILY

    @property
    def is_all_time(self):
        """Check if this is an all-time leaderboard entry"""
        return self.leaderboard_type == LeaderboardType.ALL_TIME

    @property
    def position_change_text(self):
        """Get formatted position change text"""
        if self.position_change > 0:
            return f"↑{self.position_change}"
        elif self.position_change < 0:
            return f"↓{abs(self.position_change)}"
        else:
            return "→"

    @property
    def is_top_3(self):
        """Check if user is in top 3"""
        return self.rank <= 3

    @property
    def is_first_place(self):
        """Check if user is in first place"""
        return self.rank == 1

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'leaderboard_type': self.leaderboard_type.value,
            'is_daily': self.is_daily,
            'is_all_time': self.is_all_time,
            'position_change_text': self.position_change_text,
            'is_top_3': self.is_top_3,
            'is_first_place': self.is_first_place
        })
        return data

    @classmethod
    def create_daily_entry(cls, group_id: int, user_id: int, leaderboard_date: date, **kwargs):
        """Factory method for creating daily leaderboard entries"""
        return cls(
            group_id=group_id,
            user_id=user_id,
            leaderboard_type=LeaderboardType.DAILY,
            leaderboard_date=leaderboard_date,
            **kwargs
        )

    @classmethod
    def create_all_time_entry(cls, group_id: int, user_id: int, **kwargs):
        """Factory method for creating all-time leaderboard entries"""
        return cls(
            group_id=group_id,
            user_id=user_id,
            leaderboard_type=LeaderboardType.ALL_TIME,
            leaderboard_date=None,  # All-time entries have no date
            **kwargs
        )