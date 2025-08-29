from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel


class QuizSession(BaseModel):
    """Quiz session model - tracks learning sessions and their performance"""
    __tablename__ = "quiz_sessions"

    # Session identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)  # Can be general practice
    session_type = Column(String(50), nullable=False, default="lesson")  # lesson, practice, review, weak_list

    # Session timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Calculated when completed

    # Session performance
    total_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    incorrect_answers = Column(Integer, nullable=False, default=0)
    skipped_answers = Column(Integer, nullable=False, default=0)

    # Performance metrics
    accuracy_percentage = Column(Float, nullable=False, default=0.0)
    average_response_time_ms = Column(Integer, nullable=True)  # Average time per question
    points_earned = Column(Integer, nullable=False, default=0)

    # Session details
    quiz_data = Column(JSON, nullable=True)  # Store question IDs, answers, etc.
    session_notes = Column(Text, nullable=True)  # Optional notes

    # Status
    is_completed = Column(Boolean, default=False)
    is_paused = Column(Boolean, default=False)
    completion_status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned

    # Device/context info
    device_type = Column(String(20), nullable=True)  # mobile, desktop, tablet
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # For analytics

    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    lesson = relationship("Lesson", back_populates="quiz_sessions")

    def __str__(self):
        return f"QuizSession({self.user_id}, {self.session_type}, {self.started_at})"

    @property
    def is_active(self):
        """Check if session is currently active"""
        return not self.is_completed and not self.is_abandoned

    @property
    def is_abandoned(self):
        """Check if session was abandoned (no activity for 30+ minutes)"""
        if self.is_completed:
            return False

        time_since_start = datetime.utcnow() - self.started_at
        return time_since_start > timedelta(minutes=30)

    @property
    def questions_answered(self):
        """Total questions answered (correct + incorrect)"""
        return self.correct_answers + self.incorrect_answers

    @property
    def completion_percentage(self):
        """Percentage of questions completed"""
        if self.total_questions == 0:
            return 0
        return (self.questions_answered / self.total_questions) * 100

    @property
    def session_duration_formatted(self):
        """Get formatted session duration"""
        if not self.duration_seconds:
            return "Unknown"

        minutes, seconds = divmod(self.duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    @property
    def performance_rating(self):
        """Get performance rating based on accuracy"""
        if self.accuracy_percentage >= 90:
            return "excellent"
        elif self.accuracy_percentage >= 75:
            return "good"
        elif self.accuracy_percentage >= 60:
            return "average"
        elif self.accuracy_percentage >= 40:
            return "below_average"
        else:
            return "poor"

    def add_question_result(self, is_correct: bool, response_time_ms: int = None):
        """Add a question result to the session"""
        self.total_questions += 1

        if is_correct:
            self.correct_answers += 1
        else:
            self.incorrect_answers += 1

        # Update accuracy
        self.accuracy_percentage = (self.correct_answers / self.total_questions) * 100

        # Update average response time
        if response_time_ms:
            current_total_time = (self.average_response_time_ms or 0) * (self.total_questions - 1)
            new_total_time = current_total_time + response_time_ms
            self.average_response_time_ms = int(new_total_time / self.total_questions)

    def skip_question(self):
        """Record a skipped question"""
        self.total_questions += 1
        self.skipped_answers += 1

        # Update accuracy (skipped questions don't count as correct)
        self.accuracy_percentage = (self.correct_answers / self.total_questions) * 100

    def pause_session(self):
        """Pause the session"""
        self.is_paused = True

    def resume_session(self):
        """Resume the session"""
        self.is_paused = False

    def complete_session(self):
        """Mark session as completed"""
        if not self.completed_at:
            self.completed_at = datetime.utcnow()
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())

        self.is_completed = True
        self.is_paused = False
        self.completion_status = "completed"

    def abandon_session(self):
        """Mark session as abandoned"""
        self.completion_status = "abandoned"
        if not self.completed_at:
            self.completed_at = datetime.utcnow()
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())

    def get_session_summary(self):
        """Get session summary for reporting"""
        return {
            "session_id": self.id,
            "user_id": self.user_id,
            "lesson_id": self.lesson_id,
            "session_type": self.session_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.session_duration_formatted,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "skipped_answers": self.skipped_answers,
            "accuracy": self.accuracy_percentage,
            "performance_rating": self.performance_rating,
            "points_earned": self.points_earned,
            "completion_status": self.completion_status
        }

    @classmethod
    def create_lesson_session(cls, user_id: int, lesson_id: int, **kwargs):
        """Factory method for creating lesson sessions"""
        return cls(
            user_id=user_id,
            lesson_id=lesson_id,
            session_type="lesson",
            **kwargs
        )

    @classmethod
    def create_practice_session(cls, user_id: int, **kwargs):
        """Factory method for creating practice sessions"""
        return cls(
            user_id=user_id,
            lesson_id=None,
            session_type="practice",
            **kwargs
        )

    @classmethod
    def create_review_session(cls, user_id: int, **kwargs):
        """Factory method for creating review sessions"""
        return cls(
            user_id=user_id,
            lesson_id=None,
            session_type="review",
            **kwargs
        )

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'is_active': self.is_active,
            'is_abandoned': self.is_abandoned,
            'questions_answered': self.questions_answered,
            'completion_percentage': self.completion_percentage,
            'session_duration_formatted': self.session_duration_formatted,
            'performance_rating': self.performance_rating
        })
        return data