from pydantic import BaseModel, validator
from typing import Optional, Dict
from decimal import Decimal
from datetime import date
from .base import BaseSchema, TimestampMixin


# Learning Center Schemas
class LearningCenterBase(BaseSchema):
    brand_name: str
    phone_number: str
    telegram_contact: Optional[str] = None
    instagram_contact: Optional[str] = None
    max_students: int = 1000
    max_branches: int = 5


class LearningCenterCreate(LearningCenterBase):
    pass


class LearningCenterUpdate(BaseModel):
    brand_name: Optional[str] = None
    phone_number: Optional[str] = None
    telegram_contact: Optional[str] = None
    instagram_contact: Optional[str] = None
    max_students: Optional[int] = None
    max_branches: Optional[int] = None


class LearningCenterResponse(LearningCenterBase, TimestampMixin):
    remaining_days: int
    expires_at: Optional[date]
    total_paid: Decimal
    is_active: bool

    # Computed fields
    is_expired: bool = False
    is_expiring_soon: bool = False


# Branch Schemas
class BranchBase(BaseSchema):
    title: str
    description: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None


class BranchCreate(BranchBase):
    learning_center_id: int


class BranchUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase, TimestampMixin):
    learning_center_id: int
    is_active: bool
    coordinates: Optional[Dict[str, float]] = None


# Payment Schemas
class PaymentBase(BaseSchema):
    amount: Decimal
    days_added: int
    payment_date: date = date.today()
    status: str = "completed"
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    learning_center_id: int


class PaymentResponse(PaymentBase, TimestampMixin):
    learning_center_id: int


# Combined schemas for admin views
class LearningCenterWithStats(LearningCenterResponse):
    total_users: int = 0
    active_users: int = 0
    total_branches: int = 0
    total_courses: int = 0


class BranchWithStats(BranchResponse):
    total_groups: int = 0
    active_groups: int = 0
    total_students: int = 0