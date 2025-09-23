from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="lessons")
    words = relationship("Word", back_populates="lesson")
    lesson_progress = relationship("LessonProgress", back_populates="lesson")
    coin_transactions = relationship("CoinTransaction", back_populates="lesson")
    
    # Indexes
    __table_args__ = (
        Index("ix_lesson_course", "course_id"),
    )