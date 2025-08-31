from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from .models import UserRole

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 2592000  # 30 days in seconds

class UserLogin(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class PhoneLogin(BaseModel):
    phone: str
    telegram_id: Optional[str] = None

class VerificationRequest(BaseModel):
    phone: str

class VerificationCode(BaseModel):
    phone: str
    code: str

# User Schemas
class UserBase(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Learning Center Schemas
class LearningCenterCreate(BaseModel):
    title: str
    logo: Optional[str] = None
    student_limit: int = 50
    owner_email: str
    owner_password: str

class LearningCenter(BaseModel):
    id: int
    title: str
    logo: Optional[str] = None
    days_remaining: int
    student_limit: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Profile Schemas
class StudentCreate(BaseModel):
    full_name: str
    phone: str
    telegram_id: Optional[str] = None

class TeacherCreate(BaseModel):
    full_name: str
    email: str
    password: str

class Profile(BaseModel):
    id: int
    full_name: str
    role_in_center: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Group Schemas
class GroupCreate(BaseModel):
    name: str
    teacher_id: Optional[int] = None
    course_id: Optional[int] = None

class Group(BaseModel):
    id: int
    name: str
    center_id: int
    teacher_id: Optional[int] = None
    course_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

class GroupMemberAdd(BaseModel):
    profile_ids: List[int]

# Course Content Schemas
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None

class Course(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    center_id: int
    is_active: bool

    class Config:
        from_attributes = True

class ModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0

class Module(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    order_index: int
    is_active: bool

    class Config:
        from_attributes = True

class LessonCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0

class Lesson(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    order_index: int
    is_active: bool

    class Config:
        from_attributes = True

class WordCreate(BaseModel):
    word: str
    meaning: str
    definition: Optional[str] = None
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    order_index: int = 0

class Word(BaseModel):
    id: int
    word: str
    meaning: str
    definition: Optional[str] = None
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    order_index: int

    class Config:
        from_attributes = True

class BulkWordCreate(BaseModel):
    words: List[WordCreate]

# Progress Schemas
class ProgressUpdate(BaseModel):
    lesson_id: int
    percentage: int

    @validator('percentage')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Percentage must be between 0 and 100')
        return v

class WordAttempt(BaseModel):
    word_id: int
    correct: bool

class Progress(BaseModel):
    id: int
    profile_id: int
    lesson_id: int
    percentage: int
    completed: bool
    last_practiced: datetime

    class Config:
        from_attributes = True

# Leaderboard Schema
class LeaderboardEntry(BaseModel):
    profile_id: int
    full_name: str
    total_coins: int
    avatar: Optional[str] = None

# Payment Schemas
class PaymentCreate(BaseModel):
    center_id: int
    amount: float
    days_added: int
    description: Optional[str] = None

class Payment(BaseModel):
    id: int
    center_id: int
    amount: float
    days_added: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Response Schemas
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class PaginatedResponse(BaseModel):
    success: bool
    data: dict  # Contains items and pagination info