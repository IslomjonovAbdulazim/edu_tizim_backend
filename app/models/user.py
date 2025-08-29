from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.constants.roles import UserRole


class User(BaseModel):
    __tablename__ = "users"

    # Basic Info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)  # Removed unique=True
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Learning Center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="users")

    # Role-specific relationships
    # For students
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # For parents
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # For teachers
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Progress and gamification
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    weekly_lists = relationship("WeekList", back_populates="user", cascade="all, delete-orphan")

    # Composite unique constraint: phone_number + learning_center_id must be unique
    __table_args__ = (
        UniqueConstraint('phone_number', 'learning_center_id',
                        name='uq_user_phone_learning_center'),
    )

    def __str__(self):
        return f"User(full_name='{self.full_name}', role='{self.role}')"

    @property
    def total_points(self):
        """Calculate total points from progress"""
        return sum(progress.points for progress in self.progress_records)

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role == role

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        return self.role in roles