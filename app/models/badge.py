from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime


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

    # Notification tracking - NEW FIELDS!
    is_seen = Column(Boolean, default=False, nullable=False)  # Has user seen this badge?
    seen_at = Column(DateTime, nullable=True)  # When user viewed the badge

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

    @property
    def is_new(self):
        """Check if badge is new/unseen"""
        return not self.is_seen

    def mark_as_seen(self):
        """Mark badge as seen by user"""
        self.is_seen = True
        self.seen_at = datetime.utcnow()

    def mark_as_unseen(self):
        """Mark badge as unseen (when updated/level up)"""
        self.is_seen = False
        self.seen_at = None

    def level_up(self, new_level: int):
        """Increase badge level and mark as unseen"""
        if new_level > self.level:
            self.level = new_level
            self.mark_as_unseen()  # User needs to see the level up
            self.earned_at = datetime.utcnow()  # Update earned time

    def increment_count(self, increment: int = 1):
        """Increment badge count and mark as unseen if significant"""
        old_count = self.count
        self.count += increment

        # Mark as unseen if it's a milestone (every 10 counts or first few)
        if self.count <= 5 or self.count % 10 == 0 or old_count < 10:
            self.mark_as_unseen()