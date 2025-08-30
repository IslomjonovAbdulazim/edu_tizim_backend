from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Float, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class Progress(BaseModel):
    __tablename__ = "progress"

    # User and lesson
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Progress tracking (percentage-based points: 90% = 90 points)
    completion_percentage = Column(Float, default=0.0)  # 0-100
    points = Column(Integer, default=0)  # Matches completion percentage
    is_completed = Column(Boolean, default=False)

    # Performance data
    total_attempts = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="progress_records")
    lesson = relationship("Lesson", back_populates="progress_records")
    learning_center = relationship("LearningCenter", back_populates="progress_records")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', 'learning_center_id', name='uq_progress_user_lesson_center'),
        Index('idx_user_center', 'user_id', 'learning_center_id'),
        Index('idx_lesson_user', 'lesson_id', 'user_id'),
        Index('idx_center_completed', 'learning_center_id', 'is_completed'),
        Index('idx_last_attempt', 'last_attempt_at'),
    )

    def __str__(self):
        return f"Progress({self.user_id}, {self.lesson_id}, {self.completion_percentage}%)"

    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.total_attempts == 0:
            return 0.0
        return round((self.correct_answers / self.total_attempts) * 100, 1)

    def update_progress(self, new_percentage: float, correct: int, total: int):
        """Update progress with new results"""
        if new_percentage > self.completion_percentage:
            self.completion_percentage = new_percentage
            self.points = int(new_percentage)
            self.is_completed = new_percentage >= 100
            self.total_attempts = total
            self.correct_answers = correct
            self.last_attempt_at = datetime.utcnow()


class QuizSession(BaseModel):
    __tablename__ = "quiz_sessions"

    # Session identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Session data
    quiz_results = Column(JSON)  # Store word_id -> correct/incorrect mapping
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    completion_percentage = Column(Float, default=0.0)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    is_completed = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    lesson = relationship("Lesson", back_populates="quiz_sessions")
    learning_center = relationship("LearningCenter", back_populates="quiz_sessions")

    # Indexes
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'started_at'),
        Index('idx_lesson_session', 'lesson_id', 'started_at'),
        Index('idx_center_session', 'learning_center_id', 'started_at'),
        Index('idx_completed_session', 'is_completed', 'completed_at'),
    )

    def __str__(self):
        return f"QuizSession({self.user_id}, {self.lesson_id})"

    @property
    def accuracy(self):
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_answers / self.total_questions) * 100, 1)

    def complete_session(self, quiz_results: dict):
        """Complete quiz session with results"""
        self.quiz_results = quiz_results
        self.total_questions = len(quiz_results)
        self.correct_answers = sum(1 for is_correct in quiz_results.values() if is_correct)
        self.completion_percentage = (self.correct_answers / self.total_questions * 100) if self.total_questions > 0 else 0
        self.is_completed = True
        self.completed_at = datetime.utcnow()


class WeakWord(BaseModel):
    __tablename__ = "weak_words"

    # User and word
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Performance tracking (last 7 quiz results)
    last_7_results = Column(String(7), default="")  # "1010110" format
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)

    # Status
    strength = Column(String(10), default="weak")  # weak, medium, strong
    last_attempt_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="weak_words")
    word = relationship("Word", back_populates="weak_words")
    learning_center = relationship("LearningCenter", back_populates="weak_words")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', 'learning_center_id', name='uq_weak_word'),
        Index('idx_user_center_strength', 'user_id', 'learning_center_id', 'strength'),
        Index('idx_word_center', 'word_id', 'learning_center_id'),
        Index('idx_strength_attempt', 'strength', 'last_attempt_at'),
    )

    def __str__(self):
        return f"WeakWord({self.user_id}, {self.word_id}, {self.strength})"

    @property
    def recent_accuracy(self):
        """Calculate accuracy from last 7 attempts"""
        if not self.last_7_results:
            return 0.0
        correct = self.last_7_results.count('1')
        total = len(self.last_7_results)
        return (correct / total) * 100 if total > 0 else 0.0

    def add_attempt(self, is_correct: bool):
        """Add new attempt result and update strength"""
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1

        # Update last 7 results
        new_result = '1' if is_correct else '0'
        self.last_7_results = (self.last_7_results + new_result)[-7:]

        # Update strength based on recent performance
        recent_acc = self.recent_accuracy
        if recent_acc >= 80:
            self.strength = "strong"
        elif recent_acc >= 60:
            self.strength = "medium"
        else:
            self.strength = "weak"

        self.last_attempt_at = datetime.utcnow()