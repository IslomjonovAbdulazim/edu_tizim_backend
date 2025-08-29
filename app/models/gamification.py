from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Date, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import date
import enum
from .base import BaseModel
from ..constants.badge_types import LEVEL_THRESHOLDS, BADGE_INFO


class LeaderboardType(enum.Enum):
    GLOBAL_3_DAILY = "global_3_daily"  # Global 3-day leaderboard
    GLOBAL_ALL_TIME = "global_all_time"  # Global all-time leaderboard
    GROUP_3_DAILY = "group_3_daily"  # Group 3-day leaderboard
    GROUP_ALL_TIME = "group_all_time"  # Group all-time leaderboard


class LeaderboardEntry(BaseModel):
    __tablename__ = "leaderboard_entries"

    # Core identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False)

    # Optional group (for group leaderboards)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    # Date (for 3-daily leaderboards, null for all-time)
    leaderboard_date = Column(Date, nullable=True)

    # Ranking data
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)
    previous_rank = Column(Integer, nullable=True)
    position_change = Column(Integer, default=0)  # Positive = moved up, negative = moved down

    # Denormalized data for performance
    user_full_name = Column(String(100), nullable=False)

    # Relationships
    user = relationship("User", back_populates="leaderboard_entries")
    group = relationship("Group", back_populates="leaderboard_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'leaderboard_type', 'group_id', 'leaderboard_date',
                         name='uix_leaderboard_entry'),
    )

    def __str__(self):
        return f"LeaderboardEntry({self.user_full_name}, {self.leaderboard_type.value}, Rank {self.rank})"

    @property
    def is_3_daily(self):
        return self.leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]

    @property
    def is_top_3(self):
        return self.rank <= 3

    @property
    def position_improved(self):
        """Check if position improved from previous rank"""
        return self.position_change > 0


class BadgeCategory(str, enum.Enum):
    DAILY_FIRST = "daily_first"  # Top 1 in 3-daily leaderboard
    PERFECT_LESSON = "perfect_lesson"  # 100% lesson completion
    WEAKLIST_SOLVER = "weaklist_solver"  # WeakList completion
    POSITION_CLIMBER = "position_climber"  # Position improvement


class UserBadge(BaseModel):
    __tablename__ = "user_badges"

    # User and badge
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(Enum(BadgeCategory), nullable=False)

    # Badge level (not count)
    level = Column(Integer, default=1)

    # Badge info
    title = Column(String(100), nullable=False)
    description = Column(String(200), nullable=False)
    image_url = Column(String(500), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    earned_at = Column(Date, default=date.today)

    # Relationships
    user = relationship("User", back_populates="user_badges")

    # Unique constraint: one badge per category per user (level can increase)
    __table_args__ = (
        UniqueConstraint('user_id', 'category', name='uix_user_badge_category'),
    )

    def __str__(self):
        return f"UserBadge({self.user_id}, {self.category.value}, Level {self.level})"

    def can_level_up(self, current_count: int) -> bool:
        """Check if badge can be leveled up based on current count"""

        thresholds = LEVEL_THRESHOLDS.get(self.category.value, [])
        if not thresholds:
            return False

        max_level = len(thresholds)
        return self.level < max_level and current_count >= thresholds[self.level]

    def level_up(self) -> bool:
        """Level up the badge"""

        thresholds = LEVEL_THRESHOLDS.get(self.category.value, [])
        if self.level < len(thresholds):
            self.level += 1
            # Update badge info for new level
            badge_info = BADGE_INFO.get(self.category.value, {})
            self.title = f"{badge_info.get('name', '')} Level {self.level}"
            self.description = f"{badge_info.get('description', '')} - Level {self.level}"
            return True
        return False