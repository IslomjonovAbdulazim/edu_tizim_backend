from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, time
from app.schemas.branch import BranchResponse


class LearningCenterBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    country_code: str = Field(default="uz", max_length=10)  # ISO country code
    timezone: str = Field(default="Asia/Tashkent", max_length=50)
    main_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=200)
    is_active: bool = True
    leaderboard_reset_time: time = Field(default=time(0, 0))  # Default 00:00
    logo_url: Optional[str] = Field(None, max_length=500)
    brand_color: Optional[str] = Field(None, max_length=7, min_length=7)  # Hex color #FFFFFF

    # LIMITS
    max_branches: int = Field(default=5, ge=1, le=50)  # 1-50 branches allowed
    max_students: int = Field(default=1000, ge=10, le=100000)  # 10-100,000 students allowed

    @validator('country_code')
    def validate_country_code(cls, v):
        allowed_codes = ["uz", "kg", "kz", "tj", "tm", "af", "ru", "tr", "us", "uk"]
        if v.lower() not in allowed_codes:
            raise ValueError(f'Country code must be one of: {", ".join(allowed_codes)}')
        return v.lower()

    @validator('timezone')
    def validate_timezone(cls, v):
        allowed_timezones = [
            "Asia/Tashkent", "Asia/Almaty", "Asia/Bishkek",
            "Asia/Dushanbe", "Asia/Ashgabat", "Asia/Kabul",
            "Europe/Moscow", "Europe/Istanbul", "UTC",
            "America/New_York", "America/Los_Angeles", "Europe/London"
        ]
        if v not in allowed_timezones:
            raise ValueError(f'Timezone must be one of: {", ".join(allowed_timezones)}')
        return v

    @validator('main_phone')
    def validate_phone(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone number must start with + or contain only digits')
        return v

    @validator('brand_color')
    def validate_brand_color(cls, v):
        if v is not None:
            if not v.startswith('#') or len(v) != 7:
                raise ValueError('Brand color must be in hex format #FFFFFF')
            try:
                int(v[1:], 16)  # Validate hex
            except ValueError:
                raise ValueError('Invalid hex color code')
        return v

    @validator('website')
    def validate_website(cls, v):
        if v is not None:
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError('Website must start with http:// or https://')
        return v


class LearningCenterCreate(LearningCenterBase):
    pass


class LearningCenterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    country_code: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    main_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None
    leaderboard_reset_time: Optional[time] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    brand_color: Optional[str] = Field(None, max_length=7, min_length=7)
    max_branches: Optional[int] = Field(None, ge=1, le=50)
    max_students: Optional[int] = Field(None, ge=10, le=100000)

    @validator('max_branches', 'max_students')
    def validate_limits_not_below_current(cls, v, values, field):
        # NOTE: This validation should be done in the service layer where we have access to current data
        return v


class LearningCenterInDB(LearningCenterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningCenterStats(BaseModel):
    total_branches: int = 0
    active_branches: int = 0
    total_students: int = 0
    max_branches: int = 0
    max_students: int = 0
    branches_remaining: int = 0
    students_remaining: int = 0
    branch_utilization: float = 0.0
    student_utilization: float = 0.0
    can_add_branch: bool = True
    can_add_student: bool = True


class LearningCenterResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    country_code: str
    timezone: str
    main_phone: Optional[str]
    website: Optional[str]
    is_active: bool
    leaderboard_reset_time: time
    logo_url: Optional[str]
    brand_color: Optional[str]
    max_branches: int
    max_students: int
    created_at: datetime
    stats: Optional[LearningCenterStats] = None

    class Config:
        from_attributes = True


class LearningCenterWithBranches(LearningCenterResponse):
    """Learning center response with branches included"""
    branches: List[BranchResponse] = []


class LearningCenterListResponse(BaseModel):
    centers: List[LearningCenterResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Limit validation responses
class LimitCheckResponse(BaseModel):
    success: bool
    message: str
    current_count: int
    limit: int
    remaining: int
    can_proceed: bool


class BranchLimitCheck(LimitCheckResponse):
    """Check if can add branch"""
    pass


class StudentLimitCheck(LimitCheckResponse):
    """Check if can add student"""
    pass


# Limit increase requests
class IncreaseLimitRequest(BaseModel):
    new_max_branches: Optional[int] = Field(None, ge=1, le=50)
    new_max_students: Optional[int] = Field(None, ge=10, le=100000)
    reason: Optional[str] = None

    @validator('new_max_branches', 'new_max_students')
    def validate_increase_only(cls, v):
        if v is not None and v <= 0:
            raise ValueError('New limit must be positive')
        return v


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


# Analytics
class LearningCenterAnalytics(BaseModel):
    center_id: int
    center_name: str

    # Utilization metrics
    branch_utilization: float
    student_utilization: float

    # Growth tracking
    branches_added_this_month: int = 0
    students_added_this_month: int = 0

    # Capacity planning
    projected_branch_needs: int = 0
    projected_student_capacity_needed: int = 0

    # Recommendations
    recommendations: List[str] = []


class LearningCenterFilters(BaseModel):
    search: Optional[str] = None  # Search in name
    country_code: Optional[str] = None
    is_active: Optional[bool] = True
    near_limit: Optional[bool] = None  # Centers near their limits
    timezone: Optional[str] = None


# Settings management (simplified)
class LearningCenterSettings(BaseModel):
    # Gamification settings
    points_per_word: int = Field(default=10, ge=1, le=100)
    points_per_lesson: int = Field(default=50, ge=10, le=1000)

    # Leaderboard settings
    leaderboard_reset_time: time = Field(default=time(0, 0))
    show_position_changes: bool = True

    # Notification settings
    daily_reminder_enabled: bool = True
    achievement_notifications: bool = True


class UpdateLearningCenterSettings(BaseModel):
    settings: LearningCenterSettings