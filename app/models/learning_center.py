from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import date
from .base import BaseModel


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info with constraints
    brand_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)

    # Contact info
    telegram_contact = Column(String(100))
    instagram_contact = Column(String(100))

    # Business limits
    max_students = Column(Integer, default=1000, nullable=False)
    max_branches = Column(Integer, default=5, nullable=False)

    # Subscription
    remaining_days = Column(Integer, default=0, nullable=False)
    total_paid = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Relationships
    user_roles = relationship("UserCenterRole", back_populates="learning_center", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="learning_center")

    # Constraints
    __table_args__ = (
        CheckConstraint('max_students > 0', name='chk_max_students_positive'),
        CheckConstraint('max_branches > 0', name='chk_max_branches_positive'),
        CheckConstraint('remaining_days >= 0', name='chk_remaining_days_valid'),
        CheckConstraint('total_paid >= 0', name='chk_total_paid_valid'),
        CheckConstraint("length(brand_name) >= 2", name='chk_brand_name_length'),
        Index('idx_learningcenter_active_remaining', 'is_active', 'remaining_days'),
    )

    def __str__(self):
        return f"LearningCenter({self.brand_name})"

    @property
    def is_expired(self):
        return self.remaining_days <= 0

    @property
    def is_expiring_soon(self):
        return 0 < self.remaining_days <= 7


class Branch(BaseModel):
    __tablename__ = "branches"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)

    # Location (optional)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="branches")

    # Relationships
    groups = relationship("Group", back_populates="branch", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(title) >= 2", name='chk_title_length'),
        Index('idx_branch_center_active', 'learning_center_id', 'is_active'),
    )

    def __str__(self):
        return f"Branch({self.title})"


class Payment(BaseModel):
    __tablename__ = "payments"

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="payments")

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    days_added = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    status = Column(String(20), default="completed", nullable=False)
    notes = Column(Text)

    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='chk_amount_positive'),
        CheckConstraint('days_added > 0', name='chk_days_positive'),
        Index('idx_payment_center_date', 'learning_center_id', 'payment_date'),
    )

    def __str__(self):
        return f"Payment({self.amount} UZS, {self.days_added} days)"