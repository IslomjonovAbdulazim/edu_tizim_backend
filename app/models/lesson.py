from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Lesson(BaseModel):
    __tablename__ = "lessons"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    content = Column(Text)  # Lesson instructions
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)
    base_points = Column(Integer, default=100)

    # Module relationship
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    module = relationship("Module", back_populates="lessons")

    # Relationships
    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan", order_by="Word.order_index")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="lesson", cascade="all, delete-orphan")

    def __str__(self):
        return f"Lesson({self.title}, {self.module.title})"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def completion_points(self):
        """Total points for completing lesson (base + word points)"""
        word_points = self.total_words * 10  # 10 points per word
        return self.base_points + word_points

    @property
    def course(self):
        return self.module.course

    @property
    def total_quiz_sessions(self):
        """Get total number of quiz sessions for this lesson"""
        return len(self.quiz_sessions)

    @property
    def completed_sessions(self):
        """Get number of completed quiz sessions"""
        return len([session for session in self.quiz_sessions if session.is_completed])

    @property
    def average_session_accuracy(self):
        """Get average accuracy across all completed sessions"""
        completed = [session for session in self.quiz_sessions if session.is_completed]
        if not completed:
            return 0.0
        return sum(session.accuracy_percentage for session in completed) / len(completed)

    def get_user_sessions(self, user_id: int):
        """Get all quiz sessions for this lesson by a specific user"""
        return [session for session in self.quiz_sessions if session.user_id == user_id]

    def get_user_best_session(self, user_id: int):
        """Get user's best quiz session for this lesson"""
        user_sessions = self.get_user_sessions(user_id)
        completed_sessions = [s for s in user_sessions if s.is_completed]
        if not completed_sessions:
            return None
        return max(completed_sessions, key=lambda s: s.accuracy_percentage)

    def get_lesson_stats(self):
        """Get comprehensive lesson statistics"""
        all_sessions = self.quiz_sessions
        completed_sessions = [s for s in all_sessions if s.is_completed]

        if not completed_sessions:
            return {
                'total_sessions': len(all_sessions),
                'completed_sessions': 0,
                'average_accuracy': 0,
                'completion_rate': 0,
                'average_duration': 0
            }

        total_duration = sum(s.duration_seconds or 0 for s in completed_sessions)
        avg_duration = total_duration / len(completed_sessions) if completed_sessions else 0

        return {
            'total_sessions': len(all_sessions),
            'completed_sessions': len(completed_sessions),
            'average_accuracy': self.average_session_accuracy,
            'completion_rate': (len(completed_sessions) / len(all_sessions)) * 100 if all_sessions else 0,
            'average_duration': avg_duration
        }