from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date
from .base import BaseModel


class UserLearningCenter(BaseModel):
    __tablename__ = "user_learning_centers"

    # Association details
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Role in this learning center
    role = Column(String(20), nullable=False, default="student")

    # Association metadata
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # No direct branch assignment - branches determined through group memberships

    # Relationships
    user = relationship("User", back_populates="learning_center_associations")
    learning_center = relationship("LearningCenter", back_populates="user_associations")

    # Unique constraint: one active association per user per learning center
    __table_args__ = (
        UniqueConstraint('user_id', 'learning_center_id', name='uq_user_learning_center'),
    )

    def __str__(self):
        return f"UserLearningCenter({self.user_id}, {self.learning_center_id}, {self.role})"


class Invitation(BaseModel):
    __tablename__ = "invitations"

    # Contact info of person being invited
    phone_number = Column(String(20), nullable=False, index=True)
    full_name = Column(String(100), nullable=True)  # Optional if known

    # Learning center doing the inviting
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Who sent the invitation
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Invitation details
    role = Column(String(20), nullable=False, default="student")
    message = Column(Text)  # Optional invitation message

    # Status tracking
    is_accepted = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Relationships
    learning_center = relationship("LearningCenter", back_populates="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])

    def __str__(self):
        return f"Invitation({self.phone_number}, {self.learning_center_id})"

    @property
    def is_valid(self):
        """Check if invitation is still valid"""
        if self.is_accepted or self.is_expired:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def accept(self, user_id: int):
        """Mark invitation as accepted"""
        self.is_accepted = True
        self.accepted_at = datetime.utcnow()

        # Create the user-learning center association
        return UserLearningCenter(
            user_id=user_id,
            learning_center_id=self.learning_center_id,
            role=self.role
        )

    def expire(self):
        """Manually expire the invitation"""
        self.is_expired = True


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info
    brand_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)

    # Contact info
    telegram_contact = Column(String(100))
    instagram_contact = Column(String(100))

    # Limitations
    max_students = Column(Integer, default=1000)
    max_branches = Column(Integer, default=5)

    # Payment & Subscription
    remaining_days = Column(Integer, default=0, nullable=False)
    expires_at = Column(Date)
    total_paid = Column(Numeric(10, 2), default=0.00)

    # Status
    is_active = Column(Boolean, default=False, nullable=False)  # Blocked until payment

    # Relationships
    user_associations = relationship("UserLearningCenter", back_populates="learning_center",
                                     cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="learning_center", cascade="all, delete-orphan")

    # ADDED: Learning progress relationships per center
    progress_records = relationship("Progress", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", cascade="all, delete-orphan")
    weak_words = relationship("WeakWord", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter({self.brand_name})"

    @property
    def is_expired(self):
        """Check if subscription has expired"""
        return self.remaining_days <= 0

    @property
    def is_expiring_soon(self):
        """Check if expiring within 7 days"""
        return 0 < self.remaining_days <= 7

    def get_users(self, role: str = None, active_only: bool = True):
        """Get users associated with this learning center"""
        associations = self.user_associations

        if active_only:
            associations = [a for a in associations if a.is_active]

        if role:
            associations = [a for a in associations if a.role.lower() == role.lower()]

        return [a.user for a in associations]

    def get_students(self, active_only: bool = True):
        """Get all students in this learning center"""
        return self.get_users(role="student", active_only=active_only)

    def get_teachers(self, active_only: bool = True):
        """Get all teachers in this learning center"""
        return self.get_users(role="teacher", active_only=active_only)

    def get_admins(self, active_only: bool = True):
        """Get all admins in this learning center"""
        return self.get_users(role="admin", active_only=active_only)

    def find_user_by_phone(self, phone_number: str):
        """Find a user by phone number within this learning center"""
        for association in self.user_associations:
            if association.is_active and association.user.phone_number == phone_number:
                return association.user
        return None

    def invite_user(self, phone_number: str, invited_by_user_id: int, role: str = "student", message: str = None):
        """Create an invitation for a phone number"""
        return Invitation(
            phone_number=phone_number,
            learning_center_id=self.id,
            invited_by_user_id=invited_by_user_id,
            role=role,
            message=message
        )

    def get_user_progress_summary(self, user_id: int):
        """Get progress summary for a user in this learning center"""
        user_progress = [p for p in self.progress_records if p.user_id == user_id]
        total_lessons = len(user_progress)
        completed_lessons = len([p for p in user_progress if p.is_completed])
        total_points = sum(p.points for p in user_progress if p.points)

        return {
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'completion_rate': (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0,
            'total_points': total_points
        }

    def get_center_statistics(self):
        """Get overall statistics for this learning center"""
        total_students = len(self.get_students())
        total_progress_records = len(self.progress_records)
        total_badges_earned = len([b for b in self.user_badges if b.is_active])

        return {
            'total_students': total_students,
            'total_progress_records': total_progress_records,
            'total_badges_earned': total_badges_earned,
            'avg_progress_per_student': total_progress_records / total_students if total_students > 0 else 0
        }


class Branch(BaseModel):
    __tablename__ = "branches"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)

    # Location
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="branches")

    # Relationships
    groups = relationship("Group", back_populates="branch", cascade="all, delete-orphan")

    def __str__(self):
        return f"Branch({self.title})"

    @property
    def coordinates(self):
        """Get coordinates as dict"""
        if self.latitude and self.longitude:
            return {"latitude": float(self.latitude), "longitude": float(self.longitude)}
        return None


class Payment(BaseModel):
    __tablename__ = "payments"

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="payments")

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    days_added = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)

    # Status
    status = Column(String(20), default="completed", nullable=False)
    notes = Column(Text)

    def __str__(self):
        return f"Payment({self.learning_center.brand_name}, {self.amount} UZS, {self.days_added} days)"