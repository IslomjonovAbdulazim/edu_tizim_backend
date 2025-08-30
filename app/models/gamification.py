from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Date, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import date
import enum
from .base import BaseModel


class LeaderboardType(enum.Enum):
    GLOBAL_3_DAILY = "global_3_daily"
    GLOBAL_ALL_TIME = "global_all_time"
    GROUP_3_DAILY = "group_3_daily"
    GROUP_ALL_TIME = "group_all_time"


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
    position_change = Column(Integer, default=0)

    # Denormalized data for performance
    user_full_name = Column(String(100), nullable=False)

    # Relationships
    user = relationship("User", back_populates="leaderboard_entries")
    group = relationship("Group", back_populates="leaderboard_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'leaderboard_type', 'group_id', 'leaderboard_date',
                         name='uq_leaderboard_entry'),
    )

    def __str__(self):
        return f"LeaderboardEntry({self.user_full_name}, Rank {self.rank})"

    @property
    def is_top_3(self):
        return self.rank <= 3

    @property
    def position_improved(self):
        return self.position_change > 0


class BadgeCategory(str, enum.Enum):
    DAILY_FIRST = "daily_first"
    PERFECT_LESSON = "perfect_lesson"
    WEAKLIST_SOLVER = "weaklist_solver"
    POSITION_CLIMBER = "position_climber"


class UserBadge(BaseModel):
    __tablename__ = "user_badges"

    # User and badge - include learning_center_id for separation
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(Enum(BadgeCategory), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Badge level
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
    learning_center = relationship("LearningCenter")

    # Unique constraint: one badge per category per user per center
    __table_args__ = (
        UniqueConstraint('user_id', 'category', 'learning_center_id', name='uq_user_badge_category_center'),
    )

    def __str__(self):
        return f"UserBadge({self.user_id}, {self.category.value}, Level {self.level})"