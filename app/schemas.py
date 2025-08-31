from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole


# User Schemas
class UserBase(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: UserRole


class UserCreate(UserBase):
    password: Optional[str] = None
    telegram_id: Optional[str] = None


class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Learning Center Schemas
class LearningCenterBase(BaseModel):
    title: str
    logo: Optional[str] = None
    student_limit: int = 50


class LearningCenterCreate(LearningCenterBase):
    owner_id: int


class LearningCenter(LearningCenterBase):
    id: int
    days_remaining: int
    is_active: bool
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Learning Center Profile Schemas
class ProfileBase(BaseModel):
    full_name: str
    role_in_center: UserRole


class ProfileCreate(ProfileBase):
    user_id: int
    center_id: int


class Profile(ProfileBase):
    id: int
    user_id: int
    center_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Group Schemas
class GroupBase(BaseModel):
    name: str


class GroupCreate(GroupBase):
    teacher_id: Optional[int] = None
    course_id: Optional[int] = None


class Group(GroupBase):
    id: int
    center_id: int
    teacher_id: Optional[int] = None
    course_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Course Content Schemas
class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None


class CourseCreate(CourseBase):
    center_id: int


class Course(CourseBase):
    id: int
    center_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ModuleBase(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0


class ModuleCreate(ModuleBase):
    course_id: int


class Module(ModuleBase):
    id: int
    course_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0


class LessonCreate(LessonBase):
    module_id: int


class Lesson(LessonBase):
    id: int
    module_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WordBase(BaseModel):
    word: str
    meaning: str
    definition: Optional[str] = None
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    order_index: int = 0


class WordCreate(WordBase):
    lesson_id: int


class Word(WordBase):
    id: int
    lesson_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Progress Schemas
class ProgressUpdate(BaseModel):
    lesson_id: int
    percentage: int
    completed: bool = False


class Progress(BaseModel):
    id: int
    profile_id: int
    lesson_id: int
    percentage: int
    completed: bool
    last_practiced: datetime

    class Config:
        from_attributes = True


class WordAttempt(BaseModel):
    word_id: int
    correct: bool


class WordProgress(BaseModel):
    id: int
    profile_id: int
    word_id: int
    last_seven_attempts: str
    total_correct: int
    total_attempts: int
    last_practiced: datetime

    class Config:
        from_attributes = True


# Coin/Points Schemas
class CoinCreate(BaseModel):
    amount: int = 1
    source: str
    source_id: Optional[int] = None


class Coin(BaseModel):
    id: int
    profile_id: int
    amount: int
    source: str
    source_id: Optional[int] = None
    earned_at: datetime

    class Config:
        from_attributes = True


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
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    center_id: Optional[int] = None


# Phone Verification
class PhoneVerification(BaseModel):
    phone: str
    telegram_id: str


# Bulk Operations
class BulkWordCreate(BaseModel):
    lesson_id: int
    words: List[WordBase]


class GroupMemberAdd(BaseModel):
    group_id: int
    profile_ids: List[int]