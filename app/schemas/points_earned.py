from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime, date


# Points earned schemas
class PointsEarnedBase(BaseModel):
    points_amount: int = Field(..., gt=0)
    source_type: str = Field(...)
    description: Optional[str] = Field(None, max_length=200)
    bonus_multiplier: int = Field(default=1, ge=1, le=5)

    @validator('source_type')
    def validate_source_type(cls, v):
        allowed_sources = ["lesson", "weaklist", "bonus", "achievement", "daily_login"]
        if v not in allowed_sources:
            raise ValueError(f'Source type must be one of: {", ".join(allowed_sources)}')
        return v


class PointsEarnedCreate(PointsEarnedBase):
    user_id: int = Field(..., gt=0)
    lesson_id: Optional[int] = Field(None, gt=0)
    date_earned: date = Field(default_factory=date.today)


class LessonPointsRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    lesson_id: int = Field(..., gt=0)
    points: int = Field(..., gt=0)
    lesson_title: Optional[str] = None


class WeaklistPointsRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    words_practiced: int = Field(..., gt=0)
    accuracy: Optional[float] = Field(None, ge=0.0, le=100.0)


class BonusPointsRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    points: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=100)


class PointsEarnedInDB(PointsEarnedBase):
    id: int
    user_id: int
    lesson_id: Optional[int]
    date_earned: date
    earned_at: datetime

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id: int
    full_name: str


class LessonInfo(BaseModel):
    id: int
    title: str


class PointsEarnedResponse(BaseModel):
    id: int
    user: UserInfo
    points_amount: int
    source_type: str
    date_earned: date
    earned_at: datetime
    description: Optional[str]
    bonus_multiplier: int
    effective_points: int
    is_today: bool
    lesson: Optional[LessonInfo] = None

    class Config:
        from_attributes = True


class PointsEarnedListResponse(BaseModel):
    points_records: List[PointsEarnedResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Points analytics
class UserPointsSummary(BaseModel):
    user_id: int
    user_name: str
    total_points: int
    points_today: int
    points_this_week: int
    points_this_month: int
    points_from_lessons: int
    points_from_weaklist: int
    points_from_bonus: int
    average_daily_points: float
    best_day_points: int
    current_streak_days: int


class PointsBreakdown(BaseModel):
    lesson_points: int = 0
    weaklist_points: int = 0
    bonus_points: int = 0
    achievement_points: int = 0
    daily_login_points: int = 0


class DailyPointsReport(BaseModel):
    date: date
    total_points: int
    points_breakdown: PointsBreakdown
    rank_in_center: Optional[int] = None
    rank_in_group: Optional[int] = None


class PointsAnalytics(BaseModel):
    user_id: int
    period_days: int
    total_points_earned: int
    daily_average: float
    best_day: DailyPointsReport
    points_by_source: PointsBreakdown
    trend: str  # "increasing", "decreasing", "stable"
    daily_reports: List[DailyPointsReport] = []


# Leaderboard integration
class PointsLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    user_name: str
    points: int
    points_today: int = 0  # For daily leaderboards
    source_breakdown: Optional[PointsBreakdown] = None


# Points filters
class PointsFilters(BaseModel):
    user_id: Optional[int] = None
    source_type: Optional[str] = None
    lesson_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_points: Optional[int] = Field(None, ge=0)
    max_points: Optional[int] = Field(None, ge=0)


# Bulk points operations
class BulkPointsCreate(BaseModel):
    points_records: List[PointsEarnedCreate] = Field(..., min_items=1, max_items=100)


# Points milestones and achievements
class PointsMilestone(BaseModel):
    milestone_type: str  # "total_points", "daily_points", "weekly_points"
    threshold: int
    user_id: int
    achieved_at: datetime
    bonus_points_awarded: int = 0


class PointsAchievement(BaseModel):
    achievement_name: str
    description: str
    points_reward: int
    requirements: dict  # Flexible JSON for different achievement criteria