from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime
from app.constants.roles import UserRole


# Base User schemas
class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    telegram_id: int
    learning_center_id: int

    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic phone number validation (you can make this more sophisticated)
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    is_active: Optional[bool] = None

    @validator('phone_number', pre=True, always=True)
    def validate_phone(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone number must start with + or contain only digits')
        return v


class UserInDB(UserBase):
    id: int
    telegram_id: int
    learning_center_id: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    telegram_id: int
    role: str
    is_active: bool
    is_verified: bool
    learning_center_id: int
    total_points: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Staff creation schemas (CEO creates staff)
class StaffCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int
    role: UserRole

    @validator('role')
    def validate_staff_role(cls, v):
        allowed_roles = [UserRole.RECEPTION, UserRole.CONTENT_MANAGER, UserRole.GROUP_MANAGER]
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


# User list response
class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# User profile with additional info
class UserProfile(UserResponse):
    # Additional fields that might be useful in profile
    badge_count: Optional[int] = 0
    completed_lessons: Optional[int] = 0
    current_streak: Optional[int] = 0

    class Config:
        from_attributes = True