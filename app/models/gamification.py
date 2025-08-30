from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Date, UniqueConstraint, Index, Enum
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
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
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
    learning_center = relationship("LearningCenter", back_populates="leaderboard_entries")
    group = relationship("Group", back_populates="leaderboard_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'learning_center_id', 'leaderboard_type', 'group_id', 'leaderboard_date',
                         name='uq_leaderboard_entry'),
        Index('idx_center_type_date', 'learning_center_id', 'leaderboard_type', 'leaderboard_date'),
        Index('idx_group_type_date', 'group_id', 'leaderboard_type', 'leaderboard_date'),
        Index('idx_user_center', 'user_id', 'learning_center_id'),
        Index('idx_rank_points', 'rank', 'points'),
    )

    def __str__(self):
        return f"LeaderboardEntry({self.user_full_name}, Rank {self.rank})"

    @property
    def is_top_3(self):
        return self.rank <= 3

    @property
    def position_improved(self):
        return self.position_change > 0

    @property
    def is_3_daily(self):
        return self.leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]


class BadgeCategory(str, enum.Enum):
    DAILY_FIRST = "daily_first"
    PERFECT_LESSON = "perfect_lesson"
    WEAKLIST_SOLVER = "weaklist_solver"
    POSITION_CLIMBER = "position_climber"


class UserBadge(BaseModel):
    __tablename__ = "user_badges"

    # User and badge
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    category = Column(Enum(BadgeCategory), nullable=False)

    # Badge level
    level = Column(Integer, default=1)

    # Badge info
    title = Column(String(100), nullable=False)
    description = Column(String(200), nullable=False)
    image_url = Column(String(500), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    earned_at = Column(Date, default=date.today)
    is_seen = Column(Boolean, default=False)
    seen_at = Column(Date, nullable=True)

    # Relationships
    user = relationship("User", back_populates="badges")
    learning_center = relationship("LearningCenter", back_populates="badges")

    # Unique constraint: one badge per category per user per center
    __table_args__ = (
        UniqueConstraint('user_id', 'learning_center_id', 'category', name='uq_user_badge_category_center'),
        Index('idx_user_center', 'user_id', 'learning_center_id'),
        Index('idx_center_active', 'learning_center_id', 'is_active'),
        Index('idx_user_seen', 'user_id', 'is_seen'),
        Index('idx_earned_date', 'earned_at'),
    )

    def __str__(self):
        return f"UserBadge({self.user_id}, {self.category.value}, Level {self.level})"

    def mark_as_seen(self):
        """Mark badge as seen by user"""
        if not self.is_seen:
            self.is_seen = True
            self.seen_at = date.today()

    def can_level_up(self, current_count: int) -> bool:
        """Check if badge can be leveled up based on current count"""
        # Define thresholds for each category
        thresholds = {
            BadgeCategory.DAILY_FIRST: [1, 3, 5, 10, 20, 30, 50],
            BadgeCategory.PERFECT_LESSON: [1, 5, 10, 25, 50, 100, 200],
            BadgeCategory.WEAKLIST_SOLVER: [1, 5, 10, 25, 50, 100, 200],
            BadgeCategory.POSITION_CLIMBER: [1, 3, 5, 10, 20, 30, 50]
        }

        category_thresholds = thresholds.get(self.category, [])
        if not category_thresholds or self.level >= len(category_thresholds):
            return False

        return current_count >= category_thresholds[self.level]

    def level_up(self):
        """Level up the badge"""
        self.level += 1
        self.earned_at = date.today()
        self.is_seen = False  # New level needs to be seen
        self.seen_at = None