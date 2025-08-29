from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .base import BaseSchema, TimestampMixin


# Core Verification Requests
class SendVerificationRequest(BaseModel):
    telegram_id: int
    phone_number: str


class VerifyCodeRequest(BaseModel):
    telegram_id: int
    phone_number: str
    code: str


# Core Verification Responses
class SendVerificationResponse(BaseModel):
    success: bool
    message: str
    expires_at: datetime
    attempts_remaining: int = 3


class VerifyCodeResponse(BaseModel):
    success: bool
    message: str
    user_verified: bool = False
    attempts_remaining: int = 0
    user_data: Optional[dict] = None  # User info if verification successful


# Status Check (for telegram bot)
class VerificationStatusResponse(BaseModel):
    has_valid_code: bool
    code: Optional[str] = None  # Return actual code for telegram bot
    expires_at: Optional[datetime] = None
    attempts_remaining: int = 0


# Rate Limit Check
class RateLimitResponse(BaseModel):
    can_send: bool
    seconds_remaining: int = 0
    message: str