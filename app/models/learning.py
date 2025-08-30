from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Float, DateTime, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class Progress(BaseModel):
    __tablename__ = "progress"

    # User and lesson
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)

    # ADDED: Learning center for separation
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
    learning_center = relationship("LearningCenter")

    # Unique constraint: one progress record per user per lesson per learning center
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', 'learning_center_id', name='uq_progress_user_lesson_center'),
    )

    def __str__(self):
        return f"Progress({self.user_id}, {self.lesson_id}, {self.learning_center_id}, {self.completion_percentage}%)"

    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.total_attempts == 0:
            return 0.0
        return round((self.correct_answers / self.total_attempts) * 100, 1)

    def update_progress(self, new_percentage: float):
        """Update progress and calculate point difference"""
        if new_percentage > self.completion_percentage:
            points_gained = int(new_percentage - self.completion_percentage)
            self.completion_percentage = new_percentage
            self.points = int(new_percentage)  # Points = percentage
            self.is_completed = new_percentage >= 100
            self.last_attempt_at = datetime.utcnow()
            return points_gained
        return 0


class QuizSession(BaseModel):
    __tablename__ = "quiz_sessions"

    # Session identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)  # Nullable for practice sessions

    # ADDED: Learning center for separation
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
    learning_center = relationship("LearningCenter")

    def __str__(self):
        return f"QuizSession({self.user_id}, {self.lesson_id}, {self.learning_center_id})"

    @property
    def accuracy(self):
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_answers / self.total_questions) * 100, 1)

    def complete_session(self):
        """Mark session as completed"""
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        if self.total_questions > 0:
            self.completion_percentage = (self.correct_answers / self.total_questions) * 100


class WeakWord(BaseModel):
    __tablename__ = "weak_words"

    # User and word
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    # ADDED: Learning center for separation - same word can be weak in one center, strong in another
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Performance tracking (last 7 quiz results)
    last_7_results = Column(String(7), default="")  # "1010110" format: 1=correct, 0=incorrect
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)

    # Status
    strength = Column(String(10), default="weak")  # weak, medium, strong
    last_attempt_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="weak_words")
    word = relationship("Word", back_populates="weak_words")
    learning_center = relationship("LearningCenter")

    # Unique constraint: one weak word record per user per word per learning center
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', 'learning_center_id', name='uq_weak_word_user_word_center'),
    )

    def __str__(self):
        return f"WeakWord({self.user_id}, {self.word_id}, {self.learning_center_id}, {self.strength})"

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
        self.last_7_results = (self.last_7_results + new_result)[-7:]  # Keep only last 7

        # Update strength based on recent performance
        recent_acc = self.recent_accuracy
        if recent_acc >= 80:
            self.strength = "strong"
        elif recent_acc >= 60:
            self.strength = "medium"
        else:
            self.strength = "weak"

        self.last_attempt_at = datetime.utcnow()