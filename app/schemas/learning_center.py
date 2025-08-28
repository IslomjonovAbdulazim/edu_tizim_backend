from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, time


class LearningCenterBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    location: str = Field(default="uz", max_length=10)  # Country code
    timezone: str = Field(default="Asia/Tashkent", max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    leaderboard_reset_time: time = Field(default=time(0, 0))  # Default 00:00

    @validator('location')
    def validate_location(cls, v):
        # Add more country codes as needed
        allowed_locations = ["uz", "kg", "kz", "tj", "tm", "af", "ru", "tr"]
        if v not in allowed_locations:
            raise ValueError(f'Location must be one of: {", ".join(allowed_locations)}')
        return v

    @validator('timezone')
    def validate_timezone(cls, v):
        # Common timezones for the region
        allowed_timezones = [
            "Asia/Tashkent", "Asia/Almaty", "Asia/Bishkek",
            "Asia/Dushanbe", "Asia/Ashgabat", "Asia/Kabul",
            "Europe/Moscow", "Europe/Istanbul", "UTC"
        ]
        if v not in allowed_timezones:
            raise ValueError(f'Timezone must be one of: {", ".join(allowed_timezones)}')
        return v

    @validator('phone_number')
    def validate_phone(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone number must start with + or contain only digits')
        return v


class LearningCenterCreate(LearningCenterBase):
    pass


class LearningCenterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    location: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    leaderboard_reset_time: Optional[time] = None

    @validator('phone_number')
    def validate_phone(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone number must start with + or contain only digits')
        return v


class LearningCenterInDB(LearningCenterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningCenterStats(BaseModel):
    total_users: int = 0
    total_students: int = 0
    total_parents: int = 0
    total_staff: int = 0
    total_courses: int = 0
    total_groups: int = 0
    active_groups: int = 0
    total_lessons: int = 0
    total_words: int = 0


class LearningCenterResponse(BaseModel):
    id: int
    name: str
    location: str
    timezone: str
    phone_number: Optional[str]
    address: Optional[str]
    is_active: bool
    leaderboard_reset_time: time
    created_at: datetime
    stats: Optional[LearningCenterStats] = None

    class Config:
        from_attributes = True


class LearningCenterListResponse(BaseModel):
    centers: List[LearningCenterResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# CEO management schemas
class AssignCEORequest(BaseModel):
    user_id: int
    learning_center_id: int


class CEOInfo(BaseModel):
    id: int
    full_name: str
    phone_number: str
    telegram_id: int
    is_active: bool
    created_at: datetime


class LearningCenterWithCEO(LearningCenterResponse):
    ceo: Optional[CEOInfo] = None


# Analytics and reporting
class LearningCenterAnalytics(BaseModel):
    center_id: int
    center_name: str
    date_range: dict  # start_date and end_date

    # User metrics
    new_students_count: int
    active_students_count: int
    student_retention_rate: float

    # Learning metrics
    lessons_completed: int
    average_lesson_completion_rate: float
    total_practice_sessions: int

    # Engagement metrics
    daily_active_users: List[dict]  # Daily activity data
    peak_usage_hours: List[int]
    average_session_duration: int

    # Performance metrics
    top_performers: List[dict]
    struggling_students: List[dict]
    course_completion_rates: dict

    # Badge and gamification metrics
    badges_awarded: int
    leaderboard_participation_rate: float


class LearningCenterFilters(BaseModel):
    search: Optional[str] = None  # Search in name
    location: Optional[str] = None
    is_active: Optional[bool] = True
    timezone: Optional[str] = None


# Settings management
class LearningCenterSettings(BaseModel):
    # Gamification settings
    points_per_word: int = Field(default=10, ge=1, le=100)
    points_per_lesson: int = Field(default=50, ge=10, le=1000)
    points_per_module: int = Field(default=200, ge=50, le=5000)

    # Weeklist algorithm settings
    max_weekly_words: int = Field(default=50, ge=10, le=100)
    difficulty_multiplier: float = Field(default=1.2, ge=1.0, le=3.0)

    # Leaderboard settings
    leaderboard_reset_time: time = Field(default=time(0, 0))
    show_position_changes: bool = True
    max_leaderboard_entries: int = Field(default=100, ge=10, le=500)

    # Notification settings
    daily_reminder_enabled: bool = True
    weekly_report_enabled: bool = True
    achievement_notifications: bool = True


class UpdateLearningCenterSettings(BaseModel):
    settings: LearningCenterSettings