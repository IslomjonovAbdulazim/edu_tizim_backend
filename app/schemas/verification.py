from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from .base import BaseSchema, TimestampMixin


# Verification Code Schemas
class VerificationCodeCreate(BaseSchema):
    telegram_id: int
    phone_number: str
    code: str
    expires_in_minutes: int = 10


class VerificationCodeResponse(BaseSchema, TimestampMixin):
    telegram_id: int
    phone_number: str
    code: str
    is_used: bool
    is_expired: bool
    expires_at: datetime
    used_at: Optional[datetime]
    verification_attempts: int
    max_attempts: int
    is_valid: bool = False


# Verification Request/Response
class SendVerificationRequest(BaseModel):
    telegram_id: int
    phone_number: str


class SendVerificationResponse(BaseModel):
    success: bool
    message: str
    expires_at: datetime
    attempts_remaining: int = 3


class VerifyCodeRequest(BaseModel):
    telegram_id: int
    phone_number: str
    code: str


class VerifyCodeResponse(BaseModel):
    success: bool
    message: str
    user_verified: bool = False
    attempts_remaining: int = 0

    @validator('attempts_remaining')
    def validate_attempts(cls, v, values):
        if not values.get('success', False) and v <= 0:
            # If verification failed and no attempts remaining
            values['message'] = "Maximum verification attempts exceeded. Please request a new code."
        return v