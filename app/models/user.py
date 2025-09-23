from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    coins = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    learning_center = relationship("LearningCenter", back_populates="users")
    groups_as_teacher = relationship("Group", back_populates="teacher", foreign_keys="Group.teacher_id")
    group_memberships = relationship("GroupStudent", back_populates="student")
    lesson_progress = relationship("LessonProgress", back_populates="student")
    word_history = relationship("WordHistory", back_populates="student")
    coin_transactions = relationship("CoinTransaction", back_populates="student")
    leaderboard = relationship("Leaderboard", back_populates="student", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_user_phone_center", "phone", "learning_center_id"),
        Index("ix_user_learning_center", "learning_center_id"),
    )