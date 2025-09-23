from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..database import Base


class TransactionType(str, enum.Enum):
    LESSON_SCORE = "lesson_score"
    BONUS = "bonus"
    PENALTY = "penalty"


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    best_score = Column(Integer, default=0)
    total_coins_earned = Column(Integer, default=0)
    lesson_attempts = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="lesson_progress")
    
    # Indexes
    __table_args__ = (
        Index("ix_lesson_progress_student_lesson", "student_id", "lesson_id", unique=True),
        Index("ix_lesson_progress_student", "student_id"),
        Index("ix_lesson_progress_lesson", "lesson_id"),
    )


class WordHistory(Base):
    __tablename__ = "word_history"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    attempted_at = Column(DateTime, default=func.now())
    
    # Relationships
    student = relationship("User", back_populates="word_history")
    word = relationship("Word", back_populates="word_history")
    
    # Indexes
    __table_args__ = (
        Index("ix_word_history_student_word", "student_id", "word_id"),
        Index("ix_word_history_student", "student_id"),
        Index("ix_word_history_word", "word_id"),
    )


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    student = relationship("User", back_populates="coin_transactions")
    lesson = relationship("Lesson", back_populates="coin_transactions")
    
    # Indexes
    __table_args__ = (
        Index("ix_coin_transaction_student", "student_id"),
        Index("ix_coin_transaction_lesson", "lesson_id"),
        Index("ix_coin_transaction_created", "created_at"),
    )


class Leaderboard(Base):
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, index=True)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_coins = Column(Integer, default=0)
    rank = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    learning_center = relationship("LearningCenter", back_populates="leaderboard")
    student = relationship("User", back_populates="leaderboard")
    
    # Indexes
    __table_args__ = (
        Index("ix_leaderboard_learning_center", "learning_center_id"),
        Index("ix_leaderboard_center_rank", "learning_center_id", "rank"),
        Index("ix_leaderboard_student", "student_id", unique=True),
    )