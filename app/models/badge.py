from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class UserBadge(BaseModel):
    __tablename__ = "user_badges"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="user_badges")

    # Badge info
    badge_type = Column(String(50), nullable=False)  # lesson_master, streak_holder, etc.
    level = Column(Integer, default=1)
    count = Column(Integer, default=1)  # Number of achievements of this type
    earned_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Optional metadata
    context = Column(String(200))  # Additional info about achievement

    def __str__(self):
        return f"Badge({self.user.full_name}, {self.badge_type}, Level {self.level})"

    @property
    def badge_name(self):
        """Human readable badge name"""
        names = {
            "lesson_master": "Lesson Master",
            "streak_holder": "Streak Holder",
            "top_performer": "Top Performer",
            "consistent_learner": "Consistent Learner",
            "word_collector": "Word Collector",
            "perfect_score": "Perfect Score"
        }
        return names.get(self.badge_type, self.badge_type.replace("_", " ").title())

    @property
    def badge_icon(self):
        """Badge icon/emoji"""
        icons = {
            "lesson_master": "🎓",
            "streak_holder": "🔥",
            "top_performer": "👑",
            "consistent_learner": "📚",
            "word_collector": "📝",
            "perfect_score": "💯"
        }
        return icons.get(self.badge_type, "🏆")