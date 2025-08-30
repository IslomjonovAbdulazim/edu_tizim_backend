from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint, Index, CheckConstraint
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
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(BaseModel):
    __tablename__ = "users"

    # Core info with proper constraints
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    center_roles = relationship("UserCenterRole", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(full_name) >= 2", name='chk_name_length'),
        CheckConstraint("length(phone_number) >= 10", name='chk_phone_length'),
    )

    def __str__(self):
        return f"User({self.full_name})"

    def get_role_in_center(self, center_id: int) -> str:
        """Get user's role in specific learning center"""
        role = next((r for r in self.center_roles
                    if r.learning_center_id == center_id and r.is_active), None)
        return role.role if role else None

    def has_role_in_center(self, center_id: int, role: str) -> bool:
        """Check if user has specific role in learning center"""
        return self.get_role_in_center(center_id) == role.lower()

    def get_accessible_centers(self):
        """Get all learning centers user has access to"""
        return [r.learning_center for r in self.center_roles if r.is_active]


class UserCenterRole(BaseModel):
    __tablename__ = "user_center_roles"

    # Simple one-to-one user-center-role mapping
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.STUDENT)

    # Relationships
    user = relationship("User", back_populates="center_roles")
    learning_center = relationship("LearningCenter", back_populates="user_roles")

    # Constraints - one role per user per center
    __table_args__ = (
        UniqueConstraint('user_id', 'learning_center_id', name='uq_user_center'),
        Index('idx_center_role', 'learning_center_id', 'role'),
        Index('idx_user_center', 'user_id', 'learning_center_id'),
    )

    def __str__(self):
        return f"UserCenterRole({self.user_id}, {self.learning_center_id}, {self.role})"


class StudentGroup(BaseModel):
    __tablename__ = "student_groups"

    # Simple student-group relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

    # Relationships
    user = relationship("User")
    group = relationship("Group", back_populates="student_memberships")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='uq_student_group'),
        Index('idx_group_active', 'group_id', 'is_active'),
        Index('idx_user_active', 'user_id', 'is_active'),
    )

    def __str__(self):
        return f"StudentGroup({self.user_id}, {self.group_id})"