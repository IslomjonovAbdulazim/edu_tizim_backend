from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
import re
from .base import BaseSchema, TimestampMixin


# Verification Code Schemas
class VerificationCodeCreate(BaseSchema):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID must be positive")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number in international format")
    code: str = Field(..., min_length=4, max_length=10, description="Verification code")
    expires_in_minutes: int = Field(default=10, ge=1, le=60, description="Expiration time in minutes")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format"""
        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)

        # Check if it's a valid international format
        if not re.match(r'^\+?[1-9]\d{9,19}$', cleaned):
            raise ValueError('Phone number must be in valid international format')

        return cleaned

    @validator('code')
    def validate_code(cls, v):
        """Validate verification code format"""
        # Remove whitespace
        code = v.strip()

        # Must be numeric
        if not code.isdigit():
            raise ValueError('Verification code must contain only digits')

        return code


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
    time_remaining_minutes: int = 0
    attempts_remaining: int = 0


# Verification Request/Response
class SendVerificationRequest(BaseModel):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID must be positive")
    phone_number: str = Field(..., min_length=10, max_length=20)
    learning_center_id: int = Field(..., gt=0, description="Learning center ID must be positive")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate and normalize phone number"""
        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)

        # Ensure it starts with + for international format
        if not cleaned.startswith('+'):
            # If it's a local number, we might need to add country code
            # For now, require international format
            raise ValueError('Phone number must start with + (international format)')

        # Validate international format: +[country_code][number]
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid international phone number format')

        return cleaned

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        """Validate Telegram ID"""
        if v <= 0:
            raise ValueError('Telegram ID must be a positive integer')

        # Telegram IDs are typically large numbers, but let's set a reasonable minimum
        if v < 10000:
            raise ValueError('Invalid Telegram ID format')

        return v


class SendVerificationResponse(BaseModel):
    success: bool
    message: str
    expires_at: Optional[datetime] = None
    attempts_remaining: int = 3
    code_length: int = 6
    expires_in_minutes: int = 10

    @validator('message')
    def validate_message(cls, v, values):
        """Ensure message is descriptive based on success status"""
        if values.get('success') and not v:
            return "Verification code sent successfully"
        elif not values.get('success') and not v:
            return "Failed to send verification code"
        return v


class VerifyCodeRequest(BaseModel):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID must be positive")
    phone_number: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=10, description="Verification code received")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID must be positive")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate and normalize phone number"""
        cleaned = re.sub(r'[\s\-\(\)]', '', v)

        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format with +')

        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid international phone number format')

        return cleaned

    @validator('code')
    def validate_code(cls, v):
        """Validate verification code"""
        code = v.strip()

        if not code.isdigit():
            raise ValueError('Verification code must contain only digits')

        if len(code) < 4 or len(code) > 10:
            raise ValueError('Verification code must be between 4-10 digits')

        return code

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        """Validate Telegram ID"""
        if v <= 0 or v < 10000:
            raise ValueError('Invalid Telegram ID')
        return v


class VerifyCodeResponse(BaseModel):
    success: bool
    message: str
    user_verified: bool = False
    attempts_remaining: int = 0
    user_id: Optional[int] = None
    is_new_user: bool = False

    @validator('attempts_remaining')
    def validate_attempts(cls, v, values):
        """Provide helpful message when attempts are exhausted"""
        if not values.get('success', False) and v <= 0:
            values['message'] = "Maximum verification attempts exceeded. Please request a new code."
        return v

    @validator('message')
    def validate_message(cls, v, values):
        """Provide appropriate message based on verification status"""
        if values.get('success') and values.get('user_verified'):
            return "Phone number verified successfully. Account activated."
        elif values.get('success') and not values.get('user_verified'):
            return "Code verified, but user account needs activation."
        elif not values.get('success') and v == "":
            return "Invalid verification code."
        return v


# Additional schemas for advanced operations
class ResendCodeRequest(BaseModel):
    telegram_id: int = Field(..., gt=0)
    phone_number: str = Field(..., min_length=10, max_length=20)
    learning_center_id: int = Field(..., gt=0)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format')
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


class VerificationStatusRequest(BaseModel):
    telegram_id: int = Field(..., gt=0)
    phone_number: str = Field(..., min_length=10, max_length=20)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format')
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


class VerificationStatusResponse(BaseModel):
    has_valid_code: bool
    attempts_remaining: int
    expires_at: Optional[datetime]
    time_remaining_minutes: int
    can_request_new_code: bool
    rate_limited: bool = False
    rate_limit_reset_at: Optional[datetime] = None