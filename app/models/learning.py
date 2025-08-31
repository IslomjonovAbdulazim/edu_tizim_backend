from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Float, DateTime, JSON, UniqueConstraint, Index, CheckConstraint
# SQLAlchemy naming convention to stabilize Alembic diffs
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class Progress(BaseModel):
    __tablename__ = "progress"

    # User and lesson - clean relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)

    # Progress tracking with validation
    completion_percentage = Column(Float, default=0.0, nullable=False)
    points = Column(Integer, default=0, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Performance metrics
    total_attempts = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="progress_records")
    lesson = relationship("Lesson", back_populates="progress_records")

    # Get learning center through lesson relationship
    @property
    def learning_center_id(self):
        return self.lesson.module.course.learning_center_id if self.lesson else None

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson'),
        CheckConstraint('completion_percentage >= 0 AND completion_percentage <= 100', name='chk_percentage_valid'),
        CheckConstraint('points >= 0', name='chk_points_positive'),
        CheckConstraint('total_attempts >= 0', name='chk_attempts_positive'),
        CheckConstraint('correct_answers >= 0', name='chk_correct_positive'),
        CheckConstraint('correct_answers <= total_attempts', name='chk_correct_not_exceed'),
        Index('idx_progress_user_completed', 'user_id', 'is_completed'),
        Index('idx_progress_lesson_user', 'lesson_id', 'user_id'),
        Index('idx_progress_last_attempt', 'last_attempt_at'),
    )

    def __str__(self):
        return f"Progress({self.user_id}, {self.lesson_id}, {self.completion_percentage}%)"

    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.total_attempts == 0:
            return 0.0
        return round((self.correct_answers / self.total_attempts) * 100, 1)


class QuizSession(BaseModel):
    __tablename__ = "quiz_sessions"

    # Session identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)

    # Session data with validation
    quiz_results = Column(JSON)  # word_id -> correct/incorrect mapping
    total_questions = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    completion_percentage = Column(Float, default=0.0, nullable=False)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    lesson = relationship("Lesson", back_populates="quiz_sessions")

    # Get learning center through lesson
    @property
    def learning_center_id(self):
        return self.lesson.module.course.learning_center_id if self.lesson else None

    # Constraints
    __table_args__ = (
        CheckConstraint('total_questions >= 0', name='chk_total_positive'),
        CheckConstraint('correct_answers >= 0', name='chk_correct_positive'),
        CheckConstraint('correct_answers <= total_questions', name='chk_correct_not_exceed'),
        CheckConstraint('completion_percentage >= 0 AND completion_percentage <= 100', name='chk_percentage_valid'),
        Index('idx_quizsession_user_session', 'user_id', 'started_at'),
        Index('idx_quizsession_lesson_session', 'lesson_id', 'started_at'),
        Index('idx_quizsession_completed', 'is_completed', 'completed_at'),
    )

    def __str__(self):
        return f"QuizSession({self.user_id}, {self.lesson_id})"

    @property
    def accuracy(self):
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_answers / self.total_questions) * 100, 1)


class WeakWord(BaseModel):
    __tablename__ = "weak_words"

    # User and word - clean relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    # Simplified performance tracking
    last_7_results = Column(String(7), default="", nullable=False)
    total_attempts = Column(Integer, default=0, nullable=False)
    correct_attempts = Column(Integer, default=0, nullable=False)
    strength = Column(String(10), default="weak", nullable=False)
    last_attempt_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="weak_words")
    word = relationship("Word", back_populates="weak_words")

    # Get learning center through word relationship
    @property
    def learning_center_id(self):
        return self.word.lesson.module.course.learning_center_id if self.word else None

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', name='uq_user_word'),
        CheckConstraint('total_attempts >= 0', name='chk_attempts_positive'),
        CheckConstraint('correct_attempts >= 0', name='chk_correct_positive'),
        CheckConstraint('correct_attempts <= total_attempts', name='chk_correct_not_exceed'),
        CheckConstraint("strength IN ('weak', 'medium', 'strong')", name='chk_strength_valid'),
        CheckConstraint("length(last_7_results) <= 7", name='chk_results_length'),
        Index('idx_weakword_user_strength', 'user_id', 'strength'),
        Index('idx_weakword_word_user', 'word_id', 'user_id'),
        Index('idx_weakword_strength_attempt', 'strength', 'last_attempt_at'),
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
        """Add new attempt and update strength"""
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1

        # Update last 7 results (sliding window)
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