from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    learning_center = relationship("LearningCenter", back_populates="courses")
    lessons = relationship("Lesson", back_populates="course")
    groups = relationship("Group", back_populates="course")
    
    # Indexes
    __table_args__ = (
        Index("ix_course_learning_center", "learning_center_id"),
    )