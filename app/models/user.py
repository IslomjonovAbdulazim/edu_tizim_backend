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

    # Learning center and branch
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    learning_center = relationship("LearningCenter", back_populates="users")
    branch = relationship("Branch", back_populates="users")

    # Role profiles (one-to-one)
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Learning data
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    weak_lists = relationship("WeakList", back_populates="user", cascade="all, delete-orphan")
    points_earned = relationship("PointsEarned", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('phone_number', 'learning_center_id', name='uq_user_phone_center'),
    )

    def __str__(self):
        return f"User({self.full_name}, {self.role})"

    @property
    def total_points(self):
        """Total points from all point earning events"""
        return sum(pe.effective_points for pe in self.points_earned)

    @property
    def points_today(self):
        """Points earned today"""
        from datetime import date
        today = date.today()
        return sum(pe.effective_points for pe in self.points_earned if pe.date_earned == today)

    @property
    def points_this_week(self):
        """Points earned this week"""
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        return sum(pe.effective_points for pe in self.points_earned
                  if pe.date_earned >= week_start)

    def has_role(self, role: str) -> bool:
        """Check user role"""
        return self.role == role

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the roles"""
        return self.role in roles

    @property
    def unseen_badges_count(self):
        """Count of unseen badges"""
        return len([badge for badge in self.user_badges if not badge.is_seen and badge.is_active])

    @property
    def has_new_badges(self):
        """Check if user has new unseen badges"""
        return self.unseen_badges_count > 0