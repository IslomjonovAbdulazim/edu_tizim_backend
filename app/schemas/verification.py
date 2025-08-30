from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from .base import BaseSchema, TimestampMixin, PhoneNumberMixin


# Verification Code Base Schemas
class VerificationCodeBase(BaseSchema):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number to verify")
    code: str = Field(..., min_length=4, max_length=10, regex="^[0-9]+$", description="Verification code")

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v < 10000:  # Telegram IDs are typically large numbers
            raise ValueError('Invalid Telegram ID format')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return PhoneNumberMixin.validate_phone(v)

    @validator('code')
    def validate_code(cls, v):
        code = v.strip()
        if not code.isdigit():
            raise ValueError('Verification code must contain only digits')
        return code


class VerificationCodeCreate(VerificationCodeBase):
    expires_in_minutes: int = Field(10, ge=1, le=60, description="Expiration time in minutes")


class VerificationCodeResponse(VerificationCodeBase, TimestampMixin):
    expires_at: datetime = Field(..., description="Code expiration timestamp")
    is_used: bool = Field(False, description="Whether code has been used")
    attempts: int = Field(0, ge=0, description="Number of verification attempts")
    max_attempts: int = Field(3, gt=0, description="Maximum allowed attempts")

    # Computed fields
    is_valid: bool = Field(False, description="Whether code is currently valid")
    is_expired: bool = Field(False, description="Whether code has expired")
    can_retry: bool = Field(False, description="Whether user can still attempt verification")
    time_remaining_minutes: int = Field(0, ge=0, description="Minutes remaining until expiration")
    attempts_remaining: int = Field(0, ge=0, description="Attempts remaining")

    @validator('is_expired', pre=True, always=True)
    def set_is_expired(cls, v, values):
        expires_at = values.get('expires_at')
        return expires_at < datetime.utcnow() if expires_at else True

    @validator('is_valid', pre=True, always=True)
    def set_is_valid(cls, v, values):
        is_active = values.get('is_active', False)
        is_used = values.get('is_used', False)
        is_expired = values.get('is_expired', True)
        attempts = values.get('attempts', 0)
        max_attempts = values.get('max_attempts', 3)

        return (is_active and not is_used and not is_expired and attempts < max_attempts)

    @validator('can_retry', pre=True, always=True)
    def set_can_retry(cls, v, values):
        attempts = values.get('attempts', 0)
        max_attempts = values.get('max_attempts', 3)
        is_expired = values.get('is_expired', True)
        is_active = values.get('is_active', False)

        return attempts < max_attempts and not is_expired and is_active

    @validator('time_remaining_minutes', pre=True, always=True)
    def calculate_time_remaining(cls, v, values):
        expires_at = values.get('expires_at')
        if expires_at and expires_at > datetime.utcnow():
            delta = expires_at - datetime.utcnow()
            return max(0, int(delta.total_seconds() / 60))
        return 0

    @validator('attempts_remaining', pre=True, always=True)
    def calculate_attempts_remaining(cls, v, values):
        attempts = values.get('attempts', 0)
        max_attempts = values.get('max_attempts', 3)
        return max(0, max_attempts - attempts)


# Request/Response Schemas for API endpoints
class SendVerificationRequest(BaseModel, PhoneNumberMixin):
    """Request to send verification code"""
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number to verify")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID for validation")

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v < 10000:
            raise ValueError('Invalid Telegram ID format')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)


class SendVerificationResponse(BaseModel):
    """Response after sending verification code"""
    success: bool = Field(..., description="Whether code was sent successfully")
    message: str = Field(..., description="Status message")
    expires_at: Optional[datetime] = Field(None, description="When code expires")
    attempts_remaining: int = Field(3, ge=0, description="Verification attempts remaining")
    code_length: int = Field(6, ge=4, le=10, description="Length of verification code")
    expires_in_minutes: int = Field(10, ge=1, description="Minutes until expiration")

    # Rate limiting info
    next_code_allowed_at: Optional[datetime] = Field(None, description="When next code can be requested")

    @validator('message')
    def validate_message(cls, v, values):
        success = values.get('success', False)
        if success and not v:
            return "Verification code sent successfully"
        elif not success and not v:
            return "Failed to send verification code"
        return v


class VerifyCodeRequest(BaseModel, PhoneNumberMixin):
    """Request to verify code"""
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number being verified")
    code: str = Field(..., min_length=4, max_length=10, regex="^[0-9]+$", description="Verification code")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID for validation")

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v < 10000:
            raise ValueError('Invalid Telegram ID')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return self.validate_phone(v)

    @validator('code')
    def validate_code(cls, v):
        code = v.strip()
        if not code.isdigit():
            raise ValueError('Verification code must contain only digits')
        if not (4 <= len(code) <= 10):
            raise ValueError('Verification code must be between 4-10 digits')
        return code


class VerifyCodeResponse(BaseModel):
    """Response after code verification attempt"""
    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Verification result message")
    user_verified: bool = Field(False, description="Whether user account is now verified")
    attempts_remaining: int = Field(0, ge=0, description="Remaining verification attempts")
    user_id: Optional[int] = Field(None, gt=0, description="User ID if verification successful")
    is_new_user: bool = Field(False, description="Whether this created a new user account")

    # Next steps guidance
    next_step: str = Field("", description="What user should do next")
    access_token: Optional[str] = Field(None, description="Access token if applicable")

    @validator('next_step', pre=True, always=True)
    def set_next_step(cls, v, values):
        success = values.get('success', False)
        user_verified = values.get('user_verified', False)

        if success and user_verified:
            return "access_dashboard"
        elif success and not user_verified:
            return "complete_profile"
        elif not success and values.get('attempts_remaining', 0) > 0:
            return "retry_verification"
        else:
            return "request_new_code"

    @validator('message')
    def validate_message(cls, v, values):
        success = values.get('success', False)
        user_verified = values.get('user_verified', False)
        attempts = values.get('attempts_remaining', 0)

        if success and user_verified:
            return "Phone number verified successfully. Account activated."
        elif success and not user_verified:
            return "Code verified, but user account needs activation."
        elif not success and attempts > 0:
            return f"Invalid verification code. {attempts} attempts remaining."
        elif not success and attempts == 0:
            return "Maximum verification attempts exceeded. Please request a new code."

        return v or "Verification failed."


# Additional Verification Operations
class ResendCodeRequest(BaseModel, PhoneNumberMixin):
    """Request to resend verification code"""
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)


class VerificationStatusRequest(BaseModel, PhoneNumberMixin):
    """Request to check verification status"""
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)


class VerificationStatusResponse(BaseModel):
    """Current verification status"""
    has_valid_code: bool = Field(..., description="Whether user has a valid code")
    attempts_remaining: int = Field(..., ge=0, description="Remaining attempts for current code")
    expires_at: Optional[datetime] = Field(None, description="When current code expires")
    time_remaining_minutes: int = Field(0, ge=0, description="Minutes until code expires")
    can_request_new_code: bool = Field(..., description="Whether user can request a new code")

    # Rate limiting
    rate_limited: bool = Field(False, description="Whether user is rate limited")
    rate_limit_reset_at: Optional[datetime] = Field(None, description="When rate limit resets")

    # Usage statistics
    codes_sent_today: int = Field(0, ge=0, description="Codes sent today")
    daily_limit: int = Field(10, gt=0, description="Daily code limit")


# Admin and Analytics
class VerificationAnalytics(BaseModel):
    """Verification system analytics"""
    date_range: str = Field(..., description="Analytics date range")

    # Volume metrics
    total_codes_sent: int = Field(..., ge=0, description="Total verification codes sent")
    total_verifications: int = Field(..., ge=0, description="Total successful verifications")
    success_rate: float = Field(..., ge=0.0, le=100.0, description="Verification success rate")

    # Performance metrics
    average_attempts_per_verification: float = Field(..., ge=1.0, description="Average attempts needed")
    average_time_to_verify: float = Field(..., ge=0.0, description="Average time to verify (minutes)")

    # Error metrics
    expired_codes: int = Field(..., ge=0, description="Codes that expired unused")
    max_attempts_exceeded: int = Field(..., ge=0, description="Codes that hit max attempts")
    invalid_phone_numbers: int = Field(..., ge=0, description="Invalid phone number attempts")


class VerificationCleanupRequest(BaseModel):
    """Request to cleanup old verification codes"""
    days_old: int = Field(7, ge=1, le=90, description="Delete codes older than this many days")
    dry_run: bool = Field(True, description="Whether to do a dry run first")


class VerificationCleanupResponse(BaseModel):
    """Response from cleanup operation"""
    codes_deleted: int = Field(..., ge=0, description="Number of codes deleted")
    codes_found: int = Field(..., ge=0, description="Number of codes found for deletion")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    cleanup_date: datetime = Field(..., description="When cleanup was performed")


# Rate Limiting
class RateLimitStatus(BaseModel):
    """Rate limit status for verification requests"""
    telegram_id: int = Field(..., gt=0)
    can_send: bool = Field(..., description="Whether user can send code now")
    requests_made_hour: int = Field(..., ge=0, description="Requests made in last hour")
    requests_made_day: int = Field(..., ge=0, description="Requests made today")
    hourly_limit: int = Field(5, gt=0, description="Hourly request limit")
    daily_limit: int = Field(10, gt=0, description="Daily request limit")
    next_allowed_at: Optional[datetime] = Field(None, description="When next request is allowed")
    reset_at: datetime = Field(..., description="When limits reset")


# Phone Number Validation
class PhoneValidationRequest(BaseModel):
    """Request to validate phone number format"""
    phone_number: str = Field(..., min_length=5, max_length=25, description="Phone number to validate")


class PhoneValidationResponse(BaseModel):
    """Phone number validation response"""
    is_valid: bool = Field(..., description="Whether phone number is valid")
    formatted_number: Optional[str] = Field(None, description="Formatted phone number")
    country_code: Optional[str] = Field(None, description="Detected country code")
    carrier: Optional[str] = Field(None, description="Detected carrier (if available)")
    number_type: Optional[str] = Field(None, description="Number type (mobile, landline, etc.)")
    error_message: Optional[str] = Field(None, description="Error message if invalid")