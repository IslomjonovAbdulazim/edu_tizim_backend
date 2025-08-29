from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    CONTENT_MANAGER = "content_manager"
    RECEPTION = "reception"
    GROUP_MANAGER = "group_manager"
    ADMIN = "admin"  # CEO of learning center
    SUPER_ADMIN = "super_admin"  # Our admin


class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Learning center and branch
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    # Relationships
    learning_center = relationship("LearningCenter", back_populates="users")
    branch = relationship("Branch", back_populates="users")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint: phone number must be unique within learning center
    __table_args__ = (
        UniqueConstraint('phone_number', 'learning_center_id', name='uq_user_phone_center'),
    )

    def __str__(self):
        return f"User({self.full_name}, {self.role})"

    @property
    def total_points(self):
        """Total points from all completed lessons"""
        return sum(progress.points for progress in self.progress_records if progress.points)

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role.lower() == role.lower()

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        return self.role.lower() in [role.lower() for role in roles]