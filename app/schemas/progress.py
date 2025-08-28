from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime


# Progress tracking schemas
class ProgressBase(BaseModel):
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    points: int = Field(default=0, ge=0)
    is_completed: bool = False
    time_spent_seconds: int = Field(default=0, ge=0)


class ProgressCreate(BaseModel):
    user_id: int
    lesson_id: int
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    time_spent_seconds: int = Field(default=0, ge=0)


class ProgressUpdate(BaseModel):
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    time_spent_seconds: int = Field(default=0, ge=0)


class ProgressInDB(ProgressBase):
    id: int
    user_id: int
    lesson_id: int
    total_attempts: int
    best_score: float
    first_attempt_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProgressResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    lesson_title: str
    module_title: str
    course_name: str
    completion_percentage: float
    points: int
    is_completed: bool
    total_attempts: int
    best_score: float
    time_spent_seconds: int
    last_attempt_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserProgressSummary(BaseModel):
    user_id: int
    user_full_name: str
    total_points: int
    completed_lessons: int
    total_lessons_attempted: int
    average_completion: float
    total_time_spent_hours: float
    current_streak: int = 0


class LessonProgressSummary(BaseModel):
    lesson_id: int
    lesson_title: str
    module_title: str
    course_name: str
    total_students: int
    completed_students: int
    average_completion: float
    average_attempts: float


class CourseProgressSummary(BaseModel):
    course_id: int
    course_name: str
    total_modules: int
    total_lessons: int
    enrolled_students: int
    average_progress: float
    completion_rate: float


# Weekly and daily progress
class DailyProgressUpdate(BaseModel):
    lesson_id: int
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    time_spent_seconds: int = Field(default=0, ge=0)
    date: Optional[datetime] = None


class WeeklyProgressSummary(BaseModel):
    week_start: datetime
    week_end: datetime
    lessons_attempted: int
    lessons_completed: int
    points_earned: int
    time_spent_hours: float
    average_score: float


# Leaderboard related
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    full_name: str
    avatar_url: Optional[str] = None
    points: int
    position_change: int = 0
    is_current_user: bool = False


class LeaderboardResponse(BaseModel):
    date: datetime
    entries: List[LeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None


# Badge and achievement progress
class BadgeProgressUpdate(BaseModel):
    badge_type: str
    count: int
    context: Optional[str] = None


class AchievementResponse(BaseModel):
    badge_type: str
    badge_name: str
    badge_icon: str
    level: int
    count: int
    earned_at: datetime
    is_new: bool = False


# Progress list responses
class ProgressListResponse(BaseModel):
    progress_records: List[ProgressResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProgressFilters(BaseModel):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    is_completed: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None