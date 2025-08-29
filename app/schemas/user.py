from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

# User roles
class UserRole:
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"
    RECEPTION = "reception"

# Base user schemas
class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=9, max_length=20)
    telegram_id: int = Field(..., gt=0)
    role: str = Field(default=UserRole.STUDENT)
    learning_center_id: int = Field(..., gt=0)

    @validator('phone_number')
    def validate_phone(cls, v):
        # Simple phone validation
        if not (v.startswith('+') or v.isdigit()):
            raise ValueError('Invalid phone number format')
        return v

    @validator('role')
    def validate_role(cls, v):
        valid_roles = [UserRole.STUDENT, UserRole.PARENT, UserRole.TEACHER, UserRole.ADMIN, UserRole.RECEPTION]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=9, max_length=20)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    telegram_id: int
    role: str
    is_active: bool
    is_verified: bool
    learning_center_id: int
    total_points: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int

# User with role profiles
class UserWithProfile(UserResponse):
    student_profile: Optional[dict] = None
    parent_profile: Optional[dict] = None
    teacher_profile: Optional[dict] = None

# User statistics
class UserStatistics(BaseModel):
    user_id: int
    full_name: str
    total_points: int
    lessons_completed: int
    lessons_in_progress: int
    average_accuracy: float
    days_active: int
    last_activity: Optional[datetime] = None

# Authentication schemas
class LoginRequest(BaseModel):
    telegram_id: int = Field(..., gt=0)
    phone_number: str = Field(..., min_length=9, max_length=20)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

# User search and filters
class UserFilters(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    learning_center_id: Optional[int] = None
    search: Optional[str] = None  # Search in name or phone