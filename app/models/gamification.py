from sqlalchemy import Column, String, Integer, ForeignKey, Date, UniqueConstraint, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import date
import enum
from .base import BaseModel


class LeaderboardType(enum.Enum):
    DAILY = "daily"  # Simple daily leaderboard
    ALL_TIME = "all_time"  # All-time leaderboard
    GROUP = "group"  # Group-specific leaderboard


class LeaderboardEntry(BaseModel):
    __tablename__ = "leaderboard_entries"

    # Core identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False)

    # Optional group (for group leaderboards)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    # Date (for daily leaderboards, null for all-time)
    leaderboard_date = Column(Date, nullable=True)

    # Ranking data with validation
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)
    user_full_name = Column(String(100), nullable=False)

    # Relationships
    user = relationship("User", back_populates="leaderboard_entries")
    group = relationship("Group", back_populates="leaderboard_entries")

    # Get learning center through relationships
    @property
    def learning_center_id(self):
        if self.group:
            return self.group.learning_center_id
        # For non-group leaderboards, get from user's first center role
        user_roles = [r for r in self.user.center_roles if r.is_active]
        return user_roles[0].learning_center_id if user_roles else None

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'leaderboard_type', 'group_id', 'leaderboard_date', name='uq_leaderboard'),
        CheckConstraint('rank > 0', name='chk_rank_positive'),
        CheckConstraint('points >= 0', name='chk_points_positive'),
        CheckConstraint("length(user_full_name) >= 1", name='chk_name_length'),
        Index('idx_type_date_rank', 'leaderboard_type', 'leaderboard_date', 'rank'),
        Index('idx_group_type_rank', 'group_id', 'leaderboard_type', 'rank'),
        Index('idx_user_type', 'user_id', 'leaderboard_type'),
    )

    def __str__(self):
        return f"LeaderboardEntry({self.user_full_name}, Rank {self.rank})"

    @property
    def is_top_3(self):
        return self.rank <= 3