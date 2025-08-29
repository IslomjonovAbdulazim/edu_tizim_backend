from pydantic import BaseModel, validator
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
    full_name: str
    phone_number: str
    role: UserRole = UserRole.STUDENT
    is_active: bool = True


class UserCreate(UserBase):
    telegram_id: int
    learning_center_id: int
    branch_id: Optional[int] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    branch_id: Optional[int] = None


class UserResponse(UserBase, TimestampMixin):
    telegram_id: int
    learning_center_id: int
    branch_id: Optional[int]
    is_verified: bool
    total_points: int = 0


class UserWithDetails(UserResponse):
    """User with additional computed fields"""
    learning_center_name: Optional[str] = None
    branch_title: Optional[str] = None


# Login/Auth Schemas
class LoginRequest(BaseModel):
    phone_number: str
    learning_center_id: int


class LoginResponse(BaseModel):
    user: UserResponse
    verification_required: bool
    message: str


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