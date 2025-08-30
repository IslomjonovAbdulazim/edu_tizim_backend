from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, ForeignKey
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
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")

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