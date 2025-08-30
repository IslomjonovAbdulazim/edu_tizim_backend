from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint, Index, DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from .base import BaseModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    CONTENT_MANAGER = "content_manager"
    RECEPTION = "reception"
    GROUP_MANAGER = "group_manager"
    ADMIN = "admin"  # CEO of learning center
    SUPER_ADMIN = "super_admin"  # System admin


class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    center_roles = relationship("UserCenterRole", back_populates="user", cascade="all, delete-orphan")
    teacher_groups = relationship("Group", foreign_keys="Group.teacher_id", back_populates="teacher")
    student_memberships = relationship("StudentGroup", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):
        return f"User({self.full_name}, {self.phone_number})"

    def get_role_in_center(self, center_id: int) -> str:
        """Get user's role in specific learning center"""
        for role_mapping in self.center_roles:
            if role_mapping.learning_center_id == center_id and role_mapping.is_active:
                return role_mapping.role
        return None

    def has_role_in_center(self, center_id: int, role: str) -> bool:
        """Check if user has specific role in learning center"""
        user_role = self.get_role_in_center(center_id)
        return user_role and user_role.lower() == role.lower()

    def has_any_role_in_center(self, center_id: int, roles: list) -> bool:
        """Check if user has any of the specified roles in learning center"""
        user_role = self.get_role_in_center(center_id)
        return user_role and user_role.lower() in [r.lower() for r in roles]

    def get_accessible_centers(self):
        """Get all learning centers user has access to"""
        return [r.learning_center for r in self.center_roles if r.is_active]

    def get_total_points_in_center(self, center_id: int) -> int:
        """Get total points for user in specific center"""
        return sum(p.points for p in self.progress_records if p.learning_center_id == center_id)


class UserCenterRole(BaseModel):
    __tablename__ = "user_center_roles"

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Role in this specific learning center
    role = Column(String(20), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)

    # When assigned
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="center_roles", foreign_keys=[user_id])
    learning_center = relationship("LearningCenter", back_populates="user_roles")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'learning_center_id', name='uq_user_center'),
        Index('idx_center_role', 'learning_center_id', 'role', 'is_active'),
        Index('idx_user_active', 'user_id', 'is_active'),
    )

    def __str__(self):
        return f"UserCenterRole({self.user_id}, {self.learning_center_id}, {self.role})"


class StudentGroup(BaseModel):
    __tablename__ = "student_groups"

    # Direct student-group relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="student_memberships", foreign_keys=[user_id])
    group = relationship("Group", back_populates="student_memberships")
    learning_center = relationship("LearningCenter")
    added_by = relationship("User", foreign_keys=[added_by_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='uq_student_group'),
        Index('idx_group_active', 'group_id', 'is_active'),
        Index('idx_user_center', 'user_id', 'learning_center_id', 'is_active'),
    )

    def __str__(self):
        return f"StudentGroup({self.user_id}, {self.group_id})"