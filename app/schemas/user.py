from pydantic import BaseModel, validator, Field
from typing import Optional
from enum import Enum
from .base import BaseSchema, TimestampMixin


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    CONTENT_MANAGER = "content_manager"
    RECEPTION = "reception"
    GROUP_MANAGER = "group_manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Base User Schemas
class UserBase(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number in international format")
    role: UserRole = UserRole.STUDENT
    is_active: bool = True

    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate full name format"""
        name = v.strip()
        if len(name) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        if not name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValueError('Full name can only contain letters, spaces, hyphens, and apostrophes')
        return name

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate and normalize phone number"""
        import re

        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)

        # Ensure international format
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format starting with +')

        # Validate format: +[country_code][number]
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid international phone number format')

        return cleaned


# FIXED: Make telegram_id optional during user creation
class UserCreate(UserBase):
    telegram_id: Optional[int] = Field(None, gt=0, description="Telegram ID (linked during verification)")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")
    branch_id: Optional[int] = Field(None, gt=0, description="Branch ID (optional)")

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        """Validate Telegram ID if provided"""
        if v is not None:
            if v <= 0 or v < 10000:
                raise ValueError('Invalid Telegram ID format')
        return v

    @validator('learning_center_id', 'branch_id')
    def validate_ids(cls, v, field):
        """Validate that IDs are positive integers"""
        if v is not None and v <= 0:
            raise ValueError(f'{field.name} must be a positive integer')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    branch_id: Optional[int] = Field(None, gt=0)
    # FIXED: Allow updating telegram_id (for admin linking)
    telegram_id: Optional[int] = Field(None, gt=0)

    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None:
            name = v.strip()
            if len(name) < 2:
                raise ValueError('Full name must be at least 2 characters long')
            if not name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
                raise ValueError('Full name can only contain letters, spaces, hyphens, and apostrophes')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None:
            import re
            cleaned = re.sub(r'[\s\-\(\)]', '', v)
            if not cleaned.startswith('+'):
                raise ValueError('Phone number must be in international format starting with +')
            if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
                raise ValueError('Invalid international phone number format')
        return v

    @validator('telegram_id', 'branch_id')
    def validate_ids(cls, v, field):
        if v is not None and v <= 0:
            raise ValueError(f'{field.name} must be a positive integer')
        return v


class UserResponse(UserBase, TimestampMixin):
    telegram_id: Optional[int] = None  # FIXED: Make optional in response too
    learning_center_id: int
    branch_id: Optional[int]
    is_verified: bool
    total_points: int = 0

    # FIXED: Add computed fields for better API responses
    has_telegram_linked: bool = False
    verification_status: str = "pending"  # pending, verified, blocked

    @validator('has_telegram_linked', pre=True, always=True)
    def set_has_telegram_linked(cls, v, values):
        """Set has_telegram_linked based on telegram_id"""
        return values.get('telegram_id') is not None

    @validator('verification_status', pre=True, always=True)
    def set_verification_status(cls, v, values):
        """Set verification status based on user state"""
        if not values.get('is_active'):
            return "blocked"
        elif values.get('is_verified'):
            return "verified"
        else:
            return "pending"


class UserWithDetails(UserResponse):
    """User with additional computed fields"""
    learning_center_name: Optional[str] = None
    branch_title: Optional[str] = None
    last_login_at: Optional[str] = None
    days_since_registration: Optional[int] = None


# Login/Auth Schemas
class LoginRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    learning_center_id: int = Field(..., gt=0)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        import re
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format')
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


class LoginResponse(BaseModel):
    user: UserResponse
    verification_required: bool
    message: str
    next_step: str = "verify_phone"  # FIXED: Add guidance for what to do next

    @validator('next_step', pre=True, always=True)
    def set_next_step(cls, v, values):
        """Set appropriate next step based on verification status"""
        if values.get('verification_required'):
            return "verify_phone"
        else:
            return "access_dashboard"


# User Statistics Schema
class UserStats(BaseModel):
    user_id: int
    total_points: int
    lessons_completed: int
    perfect_lessons: int
    weaklist_solved: int
    position_improvements: int
    current_streak: int
    badges_count: int
    # FIXED: Add more detailed stats
    learning_days: int = 0
    average_lesson_score: float = 0.0
    last_activity: Optional[str] = None
    rank_global: Optional[int] = None
    rank_group: Optional[int] = None


# FIXED: Add additional schemas for user management
class BulkUserCreate(BaseModel):
    """Schema for creating multiple users at once"""
    users: list[UserCreate] = Field(..., min_items=1, max_items=50)

    @validator('users')
    def validate_unique_phones(cls, v):
        """Ensure all phone numbers are unique in the batch"""
        phones = [user.phone_number for user in v]
        if len(phones) != len(set(phones)):
            raise ValueError('Duplicate phone numbers found in batch')
        return v


class UserSearchRequest(BaseModel):
    """Schema for user search requests"""
    query: str = Field(..., min_length=2, max_length=100)
    learning_center_id: int = Field(..., gt=0)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    branch_id: Optional[int] = Field(None, gt=0)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PasswordResetRequest(BaseModel):
    """Schema for password reset (if implemented)"""
    phone_number: str = Field(..., min_length=10, max_length=20)
    learning_center_id: int = Field(..., gt=0)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        import re
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must be in international format')
        return cleaned