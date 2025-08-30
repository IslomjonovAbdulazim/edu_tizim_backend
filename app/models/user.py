from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"  # CEO of learning center


class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)  # GLOBALLY unique now
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # No direct branch relationship - branches determined through group memberships

    # Relationships
    learning_center_associations = relationship("UserLearningCenter", back_populates="user",
                                                cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="user", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):
        return f"User({self.full_name}, {self.phone_number})"

    @property
    def total_points(self):
        """Total points from all completed lessons (across all learning centers)"""
        return sum(progress.points for progress in self.progress_records if progress.points)

    def get_total_points_in_center(self, learning_center_id: int):
        """Total points from completed lessons in specific learning center"""
        return sum(
            progress.points
            for progress in self.progress_records
            if progress.points and progress.learning_center_id == learning_center_id
        )

    def get_progress_in_center(self, learning_center_id: int):
        """Get all progress records for specific learning center"""
        return [
            progress for progress in self.progress_records
            if progress.learning_center_id == learning_center_id
        ]

    def get_badges_in_center(self, learning_center_id: int):
        """Get all badges earned in specific learning center"""
        return [
            badge for badge in self.user_badges
            if badge.learning_center_id == learning_center_id and badge.is_active
        ]

    def get_weak_words_in_center(self, learning_center_id: int):
        """Get all weak words in specific learning center"""
        return [
            weak_word for weak_word in self.weak_words
            if weak_word.learning_center_id == learning_center_id
        ]

    def get_role_in_center(self, learning_center_id: int) -> str:
        """Get user's role in specific learning center"""
        for association in self.learning_center_associations:
            if association.learning_center_id == learning_center_id and association.is_active:
                return association.role
        return None

    def has_role_in_center(self, learning_center_id: int, role: str) -> bool:
        """Check if user has specific role in a learning center"""
        user_role = self.get_role_in_center(learning_center_id)
        return user_role and user_role.lower() == role.lower()

    def has_any_role_in_center(self, learning_center_id: int, roles: list) -> bool:
        """Check if user has any of the specified roles in a learning center"""
        user_role = self.get_role_in_center(learning_center_id)
        return user_role and user_role.lower() in [role.lower() for role in roles]

    def get_learning_centers(self, active_only: bool = True):
        """Get all learning centers user is associated with"""
        associations = self.learning_center_associations
        if active_only:
            associations = [a for a in associations if a.is_active]
        return [a.learning_center for a in associations]

    def is_member_of_center(self, learning_center_id: int) -> bool:
        """Check if user is active member of learning center"""
        return any(
            a.learning_center_id == learning_center_id and a.is_active
            for a in self.learning_center_associations
        )

    def get_branches_in_center(self, learning_center_id: int):
        """Get all branches user is active in within a learning center (through groups)"""
        from .group import student_groups
        from sqlalchemy.orm import sessionmaker

        # Get groups this user is in
        user_groups = [group for group in self.student_groups
                       if group.branch.learning_center_id == learning_center_id and group.is_active]

        # Extract unique branches
        branches = list(set([group.branch for group in user_groups]))
        return branches

    def get_groups_in_center(self, learning_center_id: int):
        """Get all groups user belongs to in a learning center"""
        return [group for group in self.student_groups
                if group.branch.learning_center_id == learning_center_id and group.is_active]