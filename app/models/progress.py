from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Progress(BaseModel):
    __tablename__ = "progress"

    # User and lesson
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)

    # Progress data
    status = Column(String(20), default="not_started")  # not_started, in_progress, completed
    attempts = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    points = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)

    # Time tracking
    last_attempt_at = Column(DateTime)
    completion_time_seconds = Column(Integer)

    # Relationships
    user = relationship("User", back_populates="progress_records")
    lesson = relationship("Lesson", back_populates="progress_records")

    def __str__(self):
        return f"Progress({self.user.full_name}, {self.lesson.title}, {self.status})"

    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_answers / self.total_questions) * 100, 1)

    @property
    def completion_percentage(self):
        """Lesson completion percentage"""
        if not self.lesson:
            return 0.0

        total_words = self.lesson.total_words
        if total_words == 0:
            return 100.0 if self.is_completed else 0.0

        # Estimate completion based on correct answers vs total words
        return min(100.0, round((self.correct_answers / total_words) * 100, 1))