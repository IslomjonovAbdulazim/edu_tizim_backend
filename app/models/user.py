from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="student")
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Learning center
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="users")

    # Role profiles (one-to-one)
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Learning data
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    weekly_lists = relationship("WeekList", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('phone_number', 'learning_center_id', name='uq_user_phone_center'),
    )

    def __str__(self):
        return f"User({self.full_name}, {self.role})"

    @property
    def total_points(self):
        """Total points from progress records"""
        return sum(p.points for p in self.progress_records)

    def has_role(self, role: str) -> bool:
        """Check user role"""
        return self.role == role

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the roles"""
        return self.role in roles