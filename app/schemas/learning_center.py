from pydantic import BaseModel, Field, ConfigDict, field_validator
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


from typing import Optional, List, Generic, TypeVar
from decimal import Decimal
from datetime import date, datetime
from .base import BaseSchema, TimestampMixin, PhoneNumberMixin


# Learning Center Schemas
class LearningCenterBase(BaseSchema, PhoneNumberMixin):
    brand_name: str = Field(..., min_length=2, max_length=100, description="Learning center brand name")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Contact phone number")
    telegram_contact: Optional[str] = Field(None, max_length=100, description="Telegram contact")
    instagram_contact: Optional[str] = Field(None, max_length=100, description="Instagram contact")
    max_students: int = Field(1000, gt=0, le=10000, description="Maximum students allowed")
    max_branches: int = Field(5, gt=0, le=50, description="Maximum branches allowed")

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)

    @field_validator('telegram_contact')
    def validate_telegram_contact(cls, v):
        if v and not v.startswith('@'):
            return f"@{v}"
        return v

    @field_validator('instagram_contact')
    def validate_instagram_contact(cls, v):
        if v and not v.startswith('@'):
            return f"@{v}"
        return v



class LearningCenterOut(LearningCenterBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class LearningCenterCreate(LearningCenterBase):
    pass


class LearningCenterUpdate(BaseSchema):
    brand_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    telegram_contact: Optional[str] = Field(None, max_length=100)
    instagram_contact: Optional[str] = Field(None, max_length=100)
    max_students: Optional[int] = Field(None, gt=0, le=10000)
    max_branches: Optional[int] = Field(None, gt=0, le=50)

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        return PhoneNumberMixin.validate_phone(v) if v else v


class LearningCenterResponse(LearningCenterBase, TimestampMixin):
    remaining_days: int = Field(..., ge=0, description="Days remaining in subscription")
    total_paid: Decimal = Field(..., ge=0, description="Total amount paid")

    # Computed fields
    is_expired: bool = Field(False, description="Whether subscription has expired")
    is_expiring_soon: bool = Field(False, description="Whether subscription expires within 7 days")
    expires_at: Optional[date] = Field(None, description="Subscription expiry date")

    @field_validator('is_expired', mode='before', validate_default=True)
    def set_is_expired(cls, v, values):
        return values.get('remaining_days', 0) <= 0

    @field_validator('is_expiring_soon', mode='before', validate_default=True)
    def set_is_expiring_soon(cls, v, values):
        days = values.get('remaining_days', 0)
        return 0 < days <= 7


class LearningCenterWithStats(LearningCenterResponse):
    """Learning center with usage statistics"""
    total_users: int = Field(0, ge=0, description="Total users in center")
    active_users: int = Field(0, ge=0, description="Active users in center")
    total_branches: int = Field(0, ge=0, description="Number of branches")
    total_courses: int = Field(0, ge=0, description="Number of courses")
    total_groups: int = Field(0, ge=0, description="Number of groups")
    current_students: int = Field(0, ge=0, description="Currently enrolled students")


# Branch Schemas

class BranchOut(BranchBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class BranchBase(BaseSchema):
    title: str = Field(..., min_length=2, max_length=100, description="Branch name")
    description: Optional[str] = Field(None, max_length=500, description="Branch description")
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="Longitude coordinate")


class BranchCreate(BranchBase):
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")


class BranchUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None


class BranchResponse(BranchBase, TimestampMixin):
    learning_center_id: int = Field(..., gt=0)

    # Computed fields
    has_coordinates: bool = Field(False, description="Whether branch has location coordinates")

    @field_validator('has_coordinates', mode='before', validate_default=True)
    def set_has_coordinates(cls, v, values):
        return values.get('latitude') is not None and values.get('longitude') is not None


class BranchWithStats(BranchResponse):
    """Branch with usage statistics"""
    total_groups: int = Field(0, ge=0, description="Number of groups in branch")
    active_groups: int = Field(0, ge=0, description="Number of active groups")
    total_students: int = Field(0, ge=0, description="Number of students in branch")


# Payment Schemas

class PaymentOut(PaymentBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class PaymentBase(BaseSchema):
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    days_added: int = Field(..., gt=0, description="Days added to subscription")
    payment_date: date = Field(default_factory=date.today, description="Payment date")
    status: str = Field("completed", regex="^(pending|completed|failed|cancelled)$", description="Payment status")
    notes: Optional[str] = Field(None, max_length=500, description="Payment notes")


class PaymentCreate(PaymentBase):
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")


class PaymentUpdate(BaseSchema):
    status: Optional[str] = Field(None, regex="^(pending|completed|failed|cancelled)$")
    notes: Optional[str] = Field(None, max_length=500)


class PaymentResponse(PaymentBase, TimestampMixin):
    learning_center_id: int = Field(..., gt=0)

    # Computed fields
    days_per_amount: float = Field(0.0, ge=0.0, description="Days per unit amount ratio")

    @field_validator('days_per_amount', mode='before', validate_default=True)
    def calculate_days_per_amount(cls, v, values):
        amount = values.get('amount')
        days = values.get('days_added')
        return float(days / amount) if amount and amount > 0 else 0.0


# Location-based queries
class LocationQuery(BaseSchema):
    """Query for finding branches by location"""
    latitude: float = Field(..., ge=-90, le=90, description="Center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Center longitude")
    radius_km: float = Field(10.0, gt=0, le=100, description="Search radius in kilometers")


class NearbyBranchResponse(BranchResponse):
    """Branch response with distance information"""
    distance_km: Optional[float] = Field(None, ge=0, description="Distance in kilometers")


# Analytics and reporting
class LearningCenterAnalytics(BaseSchema):
    """Learning center analytics data"""
    center_id: int = Field(..., gt=0)
    date_range: str = Field(..., description="Analytics date range")

    # User metrics
    new_users: int = Field(0, ge=0)
    active_users: int = Field(0, ge=0)
    retention_rate: float = Field(0.0, ge=0.0, le=100.0)

    # Learning metrics
    lessons_completed: int = Field(0, ge=0)
    average_progress: float = Field(0.0, ge=0.0, le=100.0)
    quiz_completion_rate: float = Field(0.0, ge=0.0, le=100.0)

    # Revenue metrics
    total_revenue: Decimal = Field(Decimal('0.00'), ge=0)
    average_payment: Decimal = Field(Decimal('0.00'), ge=0)
    subscription_renewals: int = Field(0, ge=0)


class SubscriptionAlert(BaseSchema):
    """Subscription expiration alert"""
    center_id: int = Field(..., gt=0)
    center_name: str = Field(..., min_length=1)
    remaining_days: int = Field(..., ge=0)
    alert_type: str = Field(..., regex="^(expiring_soon|expired|renewed)$")
    alert_date: date = Field(default_factory=date.today)

# === Standard response wrappers ===
T = TypeVar('T')
class ResponseEnvelope(Generic[T], BaseSchema):
    data: T
    meta: Optional[dict] = None

class Paginated(Generic[T], BaseSchema):
    items: List[T]
    total: int
    page: int
    size: int
    has_next: bool
