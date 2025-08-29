from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from decimal import Decimal


# Payment schemas
class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)  # Amount in UZS (e.g., 1200000.00)
    currency: str = Field(default="UZS", max_length=3)
    days_added: int = Field(..., gt=0)
    payment_method: str = Field(default="manual", max_length=50)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    @validator('currency')
    def validate_currency(cls, v):
        # Always UZS for Uzbekistan market
        allowed_currencies = ["UZS"]
        if v.upper() not in allowed_currencies:
            raise ValueError(f'Currency must be: UZS (Uzbek Som)')
        return v.upper()

    @validator('payment_method')
    def validate_payment_method(cls, v):
        allowed_methods = ["manual", "bank_transfer", "cash", "click", "payme", "uzcard", "humo"]
        if v not in allowed_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(allowed_methods)}')
        return v


class PaymentCreate(PaymentBase):
    learning_center_id: int = Field(..., gt=0)
    payment_date: date = Field(default_factory=date.today)
    processed_by: str = Field(..., min_length=2, max_length=100)


class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    days_added: Optional[int] = Field(None, gt=0)
    payment_method: Optional[str] = Field(None, max_length=50)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ["pending", "completed", "cancelled", "refunded"]
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v


class PaymentInDB(PaymentBase):
    id: int
    learning_center_id: int
    payment_date: date
    status: str = "completed"
    is_processed: bool = True
    processed_by: str
    processed_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningCenterInfo(BaseModel):
    id: int
    name: str
    main_phone: Optional[str]


class PaymentResponse(BaseModel):
    id: int
    learning_center: LearningCenterInfo
    amount: Decimal
    currency: str
    days_added: int
    payment_date: date
    payment_method: str
    reference_number: Optional[str]
    status: str
    is_processed: bool
    processed_by: str
    processed_at: datetime
    notes: Optional[str]
    days_per_som: float  # Changed from days_per_dollar
    is_recent: bool

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Payment statistics
class PaymentStatistics(BaseModel):
    total_payments: int
    total_amount: Decimal
    total_days_sold: int
    average_payment: Decimal
    average_days_per_payment: float
    recent_payments_30d: int
    revenue_this_month: Decimal
    top_paying_centers: List[dict]


class LearningCenterPaymentSummary(BaseModel):
    learning_center_id: int
    learning_center_name: str
    total_payments: int
    total_paid: Decimal
    total_days_purchased: int
    remaining_days: int
    last_payment_date: Optional[date]
    account_status: str  # active, expired, expiring_soon, active_warning
    expires_at: Optional[date]
    average_monthly_cost: Decimal


# Account management
class ExtendTrialRequest(BaseModel):
    learning_center_id: int = Field(..., gt=0)
    trial_days: int = Field(default=7, ge=1, le=30)
    reason: Optional[str] = None


class BulkPaymentCreate(BaseModel):
    payments: List[PaymentCreate] = Field(..., min_items=1, max_items=50)


class PaymentFilters(BaseModel):
    learning_center_id: Optional[int] = None
    status: Optional[str] = None
    payment_method: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = Field(None, ge=0)
    amount_max: Optional[Decimal] = Field(None, ge=0)


# Account status responses
class AccountStatusResponse(BaseModel):
    learning_center_id: int
    learning_center_name: str
    is_active: bool
    remaining_days: int
    account_status: str
    expires_at: Optional[date]
    days_until_expiration: int
    needs_payment_soon: bool
    last_payment_date: Optional[date]
    total_paid: Decimal
    recent_payments: List[PaymentResponse] = []


# Dashboard/reporting
class PaymentDashboard(BaseModel):
    total_active_centers: int
    total_expired_centers: int
    centers_expiring_soon: int  # Within 7 days
    monthly_revenue: Decimal
    pending_payments: int
    average_days_per_center: float
    top_revenue_centers: List[LearningCenterPaymentSummary]


class MonthlyRevenue(BaseModel):
    month: str  # "2024-01"
    revenue: Decimal
    payments_count: int
    days_sold: int
    active_centers: int


class RevenueReport(BaseModel):
    period_months: int
    total_revenue: Decimal
    monthly_breakdown: List[MonthlyRevenue]
    growth_percentage: float
    trends: dict


# Quick actions
class QuickPaymentRequest(BaseModel):
    learning_center_id: int = Field(..., gt=0)
    payment_package: str = Field(...)  # "1month", "3months", "6months", "1year", "custom"
    custom_amount: Optional[Decimal] = Field(None, gt=0)
    custom_days: Optional[int] = Field(None, gt=0)
    payment_method: str = Field(default="click")  # Default to Click for Uzbekistan
    reference_number: Optional[str] = None

    @validator('payment_package')
    def validate_package(cls, v):
        allowed_packages = ["1month", "3months", "6months", "1year", "custom"]
        if v not in allowed_packages:
            raise ValueError(f'Package must be one of: {", ".join(allowed_packages)}')
        return v

    @validator('custom_amount', 'custom_days')
    def validate_custom_fields(cls, v, values):
        if 'payment_package' in values and values['payment_package'] == 'custom':
            if v is None:
                raise ValueError('Custom amount and days are required for custom package')
        return v