from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import date
from .base import BaseModel


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info
    brand_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)

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
    user_roles = relationship("UserCenterRole", back_populates="learning_center", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="learning_center")
    progress_records = relationship("Progress", back_populates="learning_center")
    quiz_sessions = relationship("QuizSession", back_populates="learning_center")
    weak_words = relationship("WeakWord", back_populates="learning_center")
    badges = relationship("UserBadge", back_populates="learning_center")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="learning_center")

    # Indexes
    __table_args__ = (
        Index('idx_active_expires', 'is_active', 'expires_at'),
    )

    def __str__(self):
        return f"LearningCenter({self.brand_name})"

    @property
    def is_expired(self):
        return self.remaining_days <= 0

    @property
    def is_expiring_soon(self):
        return 0 < self.remaining_days <= 7

    def get_users_by_role(self, role: str, active_only: bool = True):
        """Get users with specific role in this center"""
        roles = self.user_roles
        if active_only:
            roles = [r for r in roles if r.is_active]
        if role:
            roles = [r for r in roles if r.role.lower() == role.lower()]
        return [r.user for r in roles]


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

    # Indexes
    __table_args__ = (
        Index('idx_center_active', 'learning_center_id', 'is_active'),
        Index('idx_location', 'latitude', 'longitude'),
    )

    def __str__(self):
        return f"Branch({self.title})"

    @property
    def coordinates(self):
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

    # Audit
    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_center_date', 'learning_center_id', 'payment_date'),
        Index('idx_status_date', 'status', 'payment_date'),
    )

    def __str__(self):
        return f"Payment({self.amount} UZS, {self.days_added} days)"