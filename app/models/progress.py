from sqlalchemy import Column, Integer, ForeignKey, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Progress(BaseModel):
    __tablename__ = "progress"

    # User and lesson relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)

    # Progress data
    completion_percentage = Column(Float, nullable=False, default=0.0)  # 0.0 to 100.0
    points = Column(Integer, nullable=False, default=0)  # Points earned for this lesson
    is_completed = Column(Boolean, default=False, nullable=False)  # True if 100% completed

    # Attempts tracking
    total_attempts = Column(Integer, nullable=False, default=0)
    best_score = Column(Float, nullable=False, default=0.0)  # Best percentage achieved

    # Time tracking
    time_spent_seconds = Column(Integer, nullable=False, default=0)  # Total time spent in seconds
    first_attempt_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)  # When first completed

    # Relationships
    user = relationship("User", back_populates="progress_records")
    lesson = relationship("Lesson", back_populates="progress_records")

    def __str__(self):
        return f"Progress(user='{self.user.full_name}', lesson='{self.lesson.title}', {self.completion_percentage}%)"

    def update_progress(self, new_percentage: float, time_spent: int = 0):
        """Update progress with new completion percentage"""
        self.total_attempts += 1
        self.last_attempt_at = func.now()

        if self.first_attempt_at is None:
            self.first_attempt_at = func.now()

        # Update best score
        if new_percentage > self.best_score:
            self.best_score = new_percentage

        # Update completion percentage (can only increase or stay same)
        if new_percentage > self.completion_percentage:
            old_points = self.points
            self.completion_percentage = new_percentage

            # Calculate points based on lesson's completion points
            self.points = int((new_percentage / 100.0) * self.lesson.completion_points)

            # Check if completed
            if new_percentage >= 100.0 and not self.is_completed:
                self.is_completed = True
                self.completed_at = func.now()

        # Add time spent
        self.time_spent_seconds += time_spent

    @property
    def points_gained_today(self):
        """Points gained today (for leaderboard calculation)"""
        # This would need to be calculated based on today's attempts
        # For now, return current points
        return self.points

    @property
    def module(self):
        return self.lesson.module

    @property
    def course(self):
        return self.lesson.module.course