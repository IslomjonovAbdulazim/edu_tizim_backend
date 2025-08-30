from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from .base import BaseSchema, TimestampMixin, PhoneNumberMixin, NameMixin


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
class UserBase(BaseSchema, PhoneNumberMixin, NameMixin):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)

    @validator('full_name')
    def validate_full_name(cls, v):
        return cls.validate_name(v)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)


class UserCreate(UserBase):
    telegram_id: Optional[int] = Field(None, gt=0, description="Telegram ID (optional during creation)")
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")
    branch_id: Optional[int] = Field(None, gt=0, description="Branch ID (optional)")
    role: UserRole = Field(UserRole.STUDENT, description="User role in the system")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    telegram_id: Optional[int] = Field(None, gt=0)
    branch_id: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

    @validator('full_name')
    def validate_full_name(cls, v):
        return NameMixin.validate_name(v) if v else v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return PhoneNumberMixin.validate_phone(v) if v else v


class UserResponse(UserBase, TimestampMixin):
    telegram_id: Optional[int] = None
    is_verified: bool = Field(..., description="Phone verification status")

    # Computed fields
    has_telegram_linked: bool = Field(False, description="Whether Telegram is linked")
    verification_status: str = Field("pending", description="Verification status")

    @validator('has_telegram_linked', pre=True, always=True)
    def set_has_telegram_linked(cls, v, values):
        return values.get('telegram_id') is not None

    @validator('verification_status', pre=True, always=True)
    def set_verification_status(cls, v, values):
        if not values.get('is_active'):
            return "blocked"
        elif values.get('is_verified'):
            return "verified"
        return "pending"


class UserWithDetails(UserResponse):
    """User with additional details and relationships"""
    learning_center_id: int = Field(..., gt=0)
    learning_center_name: Optional[str] = None
    branch_id: Optional[int] = Field(None, gt=0)
    branch_name: Optional[str] = None
    role: Optional[UserRole] = None
    total_points: int = Field(0, ge=0)


# User Center Role Schemas
class UserCenterRoleBase(BaseSchema):
    user_id: int = Field(..., gt=0)
    learning_center_id: int = Field(..., gt=0)
    role: UserRole = Field(..., description="Role in this learning center")


class UserCenterRoleCreate(UserCenterRoleBase):
    pass


class UserCenterRoleUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserCenterRoleResponse(UserCenterRoleBase, TimestampMixin):
    pass


# Authentication Schemas
class LoginRequest(BaseModel, PhoneNumberMixin):
    phone_number: str = Field(..., min_length=10, max_length=20)
    learning_center_id: int = Field(..., gt=0)

    @validator('phone_number')
    def validate_phone_number(cls, v):
        return cls.validate_phone(v)


class LoginResponse(BaseModel):
    user: UserResponse
    verification_required: bool = Field(..., description="Whether phone verification is needed")
    message: str = Field(..., description="Login status message")
    next_step: str = Field("verify_phone", description="Next action for client")

    @validator('next_step', pre=True, always=True)
    def set_next_step(cls, v, values):
        return "verify_phone" if values.get('verification_required') else "access_dashboard"


# User Statistics
class UserStats(BaseModel):
    user_id: int = Field(..., gt=0)
    total_points: int = Field(0, ge=0)
    lessons_completed: int = Field(0, ge=0)
    perfect_lessons: int = Field(0, ge=0)
    weaklist_solved: int = Field(0, ge=0)
    position_improvements: int = Field(0, ge=0)
    current_streak: int = Field(0, ge=0)
    badges_count: int = Field(0, ge=0)
    learning_days: int = Field(0, ge=0)
    average_accuracy: float = Field(0.0, ge=0.0, le=100.0)
    last_activity: Optional[str] = None
    global_rank: Optional[int] = Field(None, gt=0)
    group_rank: Optional[int] = Field(None, gt=0)


# Bulk Operations
class BulkUserCreate(BaseModel):
    users: List[UserCreate] = Field(..., min_items=1, max_items=50)

    @validator('users')
    def validate_unique_phones(cls, users):
        phones = [user.phone_number for user in users]
        if len(phones) != len(set(phones)):
            raise ValueError('Duplicate phone numbers found in batch')
        return users


class UserSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=100)
    learning_center_id: int = Field(..., gt=0)
    role: Optional[UserRole] = None
    branch_id: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


# Role Management
class ChangeRoleRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    new_role: UserRole = Field(..., description="New role to assign")
    learning_center_id: int = Field(..., gt=0)


class RoleChangeResponse(BaseModel):
    user_id: int = Field(..., gt=0)
    old_role: Optional[UserRole] = None
    new_role: UserRole = Field(..., description="New role assigned")
    learning_center_id: int = Field(..., gt=0)
    changed_at: str = Field(..., description="Timestamp of role change")
    changed_by: int = Field(..., gt=0, description="ID of user who made the change")