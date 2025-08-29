from typing import Optional
from pydantic import BaseModel, validator, Field
from datetime import datetime


class VerificationCodeBase(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=6, max_length=6)
    expires_at: datetime
    is_used: bool = False
    is_expired: bool = False
    verification_attempts: int = Field(default=0, ge=0, le=10)
    max_attempts: int = Field(default=3, ge=1, le=10)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v

    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v


class VerificationCodeCreate(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)
    expires_in_minutes: int = Field(default=10, ge=5, le=60)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class VerificationCodeInDB(VerificationCodeBase):
    id: int
    used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VerificationCodeResponse(BaseModel):
    """Response when requesting a verification code"""
    success: bool
    message: str
    telegram_id: int
    phone_number: str
    expires_at: datetime
    expires_in_minutes: int
    code: Optional[str] = None  # Only included in development/testing
    attempts_remaining: int = 3


class VerifyCodeRequest(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=6, max_length=6)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v

    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v


class VerifyCodeResponse(BaseModel):
    """Response when verifying a code"""
    success: bool
    message: str
    is_valid: bool = False
    is_expired: bool = False
    is_used: bool = False
    attempts_remaining: int = 0
    can_request_new: bool = True
    user_exists: bool = False
    user_id: Optional[int] = None


class RequestNewCodeRequest(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)
    reason: str = Field(default="expired")  # "expired", "not_received", "invalid_attempts"

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v

    @validator('reason')
    def validate_reason(cls, v):
        allowed_reasons = ["expired", "not_received", "invalid_attempts", "other"]
        if v not in allowed_reasons:
            raise ValueError(f'Reason must be one of: {", ".join(allowed_reasons)}')
        return v


# Admin schemas for managing verification codes
class VerificationCodeListResponse(BaseModel):
    codes: List[VerificationCodeInDB]
    total: int
    page: int
    per_page: int
    total_pages: int


class VerificationCodeFilters(BaseModel):
    telegram_id: Optional[int] = None
    phone_number: Optional[str] = None
    is_used: Optional[bool] = None
    is_expired: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ExpireCodeRequest(BaseModel):
    """Admin request to manually expire a verification code"""
    verification_code_id: int
    reason: str = Field(default="admin_action")


class VerificationCodeStats(BaseModel):
    """Statistics for verification codes"""
    total_codes_generated: int
    codes_used_successfully: int
    codes_expired: int
    codes_max_attempts_reached: int
    success_rate: float
    average_verification_time: int  # in seconds
    most_common_failure_reason: str

    # Daily breakdown
    daily_stats: List[dict]  # Daily verification statistics


# Rate limiting schemas
class RateLimitInfo(BaseModel):
    telegram_id: int
    phone_number: str
    requests_today: int
    max_requests_per_day: int = 10
    last_request_at: datetime
    is_rate_limited: bool = False
    reset_time: datetime


class CheckRateLimitRequest(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v

