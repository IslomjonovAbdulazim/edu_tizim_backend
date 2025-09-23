from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class LearningCenter(Base):
    __tablename__ = "learning_centers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    logo = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    student_limit = Column(Integer, nullable=False)
    teacher_limit = Column(Integer, nullable=False)
    group_limit = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    users = relationship("User", back_populates="learning_center")
    courses = relationship("Course", back_populates="learning_center")
    groups = relationship("Group", back_populates="learning_center")
    leaderboard = relationship("Leaderboard", back_populates="learning_center")