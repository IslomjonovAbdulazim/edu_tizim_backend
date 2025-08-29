from sqlalchemy import Column, String, Integer, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class DailyLeaderboard(BaseModel):
    __tablename__ = "daily_leaderboards"

    # Key identifiers
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    leaderboard_date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Ranking data
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)
    previous_rank = Column(Integer)
    position_change = Column(Integer, default=0)

    # User display info (denormalized for performance)
    user_full_name = Column(String(100), nullable=False)
    user_avatar_url = Column(String(500))

    # Relationships
    learning_center = relationship("LearningCenter", back_populates="daily_leaderboards")
    user = relationship("User", back_populates="daily_leaderboard_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint('learning_center_id', 'user_id', 'leaderboard_date',
                        name='uix_daily_center_user_date'),
    )

    def __str__(self):
        return f"DailyLeaderboard({self.leaderboard_date}, {self.user_full_name}, Rank {self.rank})"

    @property
    def position_change_text(self):
        """Human readable position change"""
        if self.position_change > 0:
            return f"↑{self.position_change}"
        elif self.position_change < 0:
            return f"↓{abs(self.position_change)}"
        else:
            return "→"

    @property
    def is_top_3(self):
        return self.rank <= 3

    @property
    def is_first_place(self):
        return self.rank == 1

    @property
    def is_top_10(self):
        return self.rank <= 10

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'position_change_text': self.position_change_text,
            'is_top_3': self.is_top_3,
            'is_first_place': self.is_first_place,
            'is_top_10': self.is_top_10
        })
        return data