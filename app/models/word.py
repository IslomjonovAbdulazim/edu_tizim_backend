from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..database import Base


class WordDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    definition = Column(Text, nullable=True)
    sentence = Column(String, nullable=True)
    difficulty = Column(Enum(WordDifficulty), nullable=False)
    audio = Column(String, nullable=True)
    image = Column(String, nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    order = Column(Integer, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    lesson = relationship("Lesson", back_populates="words")
    word_history = relationship("WordHistory", back_populates="word")
    
    # Indexes
    __table_args__ = (
        Index("ix_word_lesson", "lesson_id"),
        Index("ix_word_lesson_order", "lesson_id", "order"),
    )