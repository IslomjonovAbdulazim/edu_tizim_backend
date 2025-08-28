from sqlalchemy import Column, Integer, ForeignKey, Date, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class DailyLeaderboard(BaseModel):
    __tablename__ = "daily_leaderboards"

    # Learning center and date
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    leaderboard_date = Column(Date, nullable=False)

    # User and ranking
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=0)

    # Position change from previous day
    previous_rank = Column(Integer, nullable=True)  # None for first day
    position_change = Column(Integer, nullable=False, default=0)  # +/- change in position

    # User info snapshot (for performance)
    user_full_name = Column(String(100), nullable=False)
    user_avatar_url = Column(String(255), nullable=True)  # For future avatar support

    # Relationships
    learning_center = relationship("LearningCenter", back_populates="daily_leaderboards")
    user = relationship("User")

    def __str__(self):
        return f"DailyLeaderboard(date={self.leaderboard_date}, rank={self.rank}, user='{self.user_full_name}')"

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
        """Check if this entry is in top 3"""
        return self.rank <= 3

    @property
    def is_first_place(self):
        """Check if this entry is first place"""
        return self.rank == 1

    @property
    def improved_position(self):
        """Check if position improved from previous day"""
        return self.position_change > 0