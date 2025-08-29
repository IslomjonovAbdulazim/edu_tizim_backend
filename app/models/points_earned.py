from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Date
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime, date


class PointsEarned(BaseModel):
    __tablename__ = "points_earned"

    # User who earned points
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="points_earned")

    # Points details
    points_amount = Column(Integer, nullable=False)  # How many points earned
    source_type = Column(String(20), nullable=False)  # "lesson" or "weaklist"
    date_earned = Column(Date, nullable=False, default=date.today)

    # Source references (optional - depends on source_type)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)  # If from lesson
    lesson = relationship("Lesson")

    # Additional context
    description = Column(String(200))  # "Completed Lesson: Basic Greetings" or "Weaklist Practice"
    bonus_multiplier = Column(Integer, default=1)  # For future bonus systems

    # Metadata
    earned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __str__(self):
        return f"PointsEarned({self.user.full_name}, {self.points_amount} pts from {self.source_type})"

    @property
    def is_today(self):
        """Check if points were earned today"""
        return self.date_earned == date.today()

    @property
    def effective_points(self):
        """Calculate effective points with bonus multiplier"""
        return self.points_amount * self.bonus_multiplier

    @classmethod
    def create_lesson_points(cls, user_id: int, lesson_id: int, points: int,
                             lesson_title: str = None):
        """Create points record for lesson completion"""
        description = f"Completed Lesson: {lesson_title}" if lesson_title else "Lesson Completed"

        return cls(
            user_id=user_id,
            points_amount=points,
            source_type="lesson",
            lesson_id=lesson_id,
            description=description,
            date_earned=date.today(),
            earned_at=datetime.utcnow()
        )

    @classmethod
    def create_weaklist_points(cls, user_id: int, words_practiced: int,
                               accuracy: float = None):
        """Create points record for weaklist practice"""
        # Standard: 10 points per word practiced
        points = words_practiced * 10

        # Bonus for high accuracy
        bonus_multiplier = 1
        if accuracy and accuracy >= 90:
            bonus_multiplier = 2  # Double points for 90%+ accuracy
        elif accuracy and accuracy >= 80:
            bonus_multiplier = 1.5  # 1.5x points for 80%+ accuracy

        description = f"Weaklist Practice: {words_practiced} words"
        if accuracy:
            description += f" ({accuracy:.1f}% accuracy)"

        return cls(
            user_id=user_id,
            points_amount=points,
            source_type="weaklist",
            description=description,
            bonus_multiplier=bonus_multiplier,
            date_earned=date.today(),
            earned_at=datetime.utcnow()
        )

    @classmethod
    def create_bonus_points(cls, user_id: int, points: int, reason: str):
        """Create bonus points record"""
        return cls(
            user_id=user_id,
            points_amount=points,
            source_type="bonus",
            description=f"Bonus: {reason}",
            date_earned=date.today(),
            earned_at=datetime.utcnow()
        )