from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Users get access through group memberships
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint: phone number must be globally unique
    __table_args__ = (
        UniqueConstraint('phone_number', name='uq_user_phone'),
    )

    def __str__(self):
        return f"User({self.full_name}, {self.role})"

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role.lower() == role.lower()

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        return self.role.lower() in [role.lower() for role in roles]

    def get_learning_centers(self):
        """Get all learning centers user has access to through groups"""
        centers = set()
        for group in self.student_groups:
            if group.is_active:
                centers.add(group.branch.learning_center)
        return list(centers)

    def get_branches(self):
        """Get all branches user has access to through groups"""
        branches = set()
        for group in self.student_groups:
            if group.is_active:
                branches.add(group.branch)
        return list(branches)

    def get_branches_in_center(self, learning_center_id: int):
        """Get branches user has access to in specific learning center"""
        branches = set()
        for group in self.student_groups:
            if group.is_active and group.branch.learning_center_id == learning_center_id:
                branches.add(group.branch)
        return list(branches)

    def has_access_to_center(self, learning_center_id: int) -> bool:
        """Check if user has access to learning center through any group"""
        return any(
            group.is_active and group.branch.learning_center_id == learning_center_id
            for group in self.student_groups
        )