from typing import Optional
from pydantic import BaseModel, validator, Field
from app.constants.roles import UserRole


# Telegram authentication schemas
class TelegramAuthRequest(BaseModel):
    telegram_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=100)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class VerificationCodeRequest(BaseModel):
    telegram_id: int
    code: str = Field(..., min_length=6, max_length=6)

    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v


class VerificationCodeResponse(BaseModel):
    success: bool
    message: str
    code: Optional[str] = None  # Only for development/testing
    expires_in_minutes: int = 10


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    user_id: Optional[int] = None
    telegram_id: Optional[int] = None
    role: Optional[str] = None


# Login response
class LoginResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    tokens: Optional[Token] = None


class AuthenticatedUser(BaseModel):
    id: int
    full_name: str
    phone_number: str
    telegram_id: int
    role: str
    is_active: bool
    is_verified: bool
    learning_center_id: int


class LoginSuccessData(BaseModel):
    user: AuthenticatedUser
    tokens: Token


# Refresh token schema
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Registration schemas (for CEO/Super Admin creating accounts)
class RegisterUserRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int
    role: UserRole
    learning_center_id: Optional[int] = None  # Required for non-super-admin

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


# CEO creation (Super Admin only)
class CreateCEORequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int
    learning_center_name: str = Field(..., min_length=2, max_length=100)
    learning_center_location: str = Field(default="uz", max_length=10)

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


# Logout schema
class LogoutResponse(BaseModel):
    success: bool
    message: str = "Successfully logged out"