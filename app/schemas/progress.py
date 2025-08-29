from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Progress status
class ProgressStatus:
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Base progress schemas
class ProgressBase(BaseModel):
    user_id: int = Field(..., gt=0)
    lesson_id: int = Field(..., gt=0)
    status: str = Field(default=ProgressStatus.NOT_STARTED)
    attempts: int = Field(default=0, ge=0)
    correct_answers: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    points: int = Field(default=0, ge=0)
    is_completed: bool = False

class ProgressCreate(ProgressBase):
    pass

class ProgressUpdate(BaseModel):
    status: Optional[str] = None
    correct_answers: Optional[int] = Field(None, ge=0)
    total_questions: Optional[int] = Field(None, ge=0)
    points: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None
    completion_time_seconds: Optional[int] = Field(None, ge=0)

class ProgressResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    status: str
    attempts: int
    correct_answers: int
    total_questions: int
    points: int
    is_completed: bool
    accuracy: float = 0.0
    completion_percentage: float = 0.0
    last_attempt_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Progress with context
class ProgressWithContext(ProgressResponse):
    lesson_title: str
    module_title: str
    course_name: str
    course_level: str

class UserProgressSummary(BaseModel):
    user_id: int
    user_name: str
    total_lessons_attempted: int
    lessons_completed: int
    lessons_in_progress: int
    total_points: int
    average_accuracy: float
    completion_rate: float
    last_activity: Optional[datetime] = None

# Leaderboard
class LeaderboardEntry(BaseModel):
    rank: int = Field(..., ge=1)
    user_id: int
    user_name: str
    total_points: int
    lessons_completed: int
    accuracy: float = 0.0
    position_change: int = 0  # Change from previous ranking

class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    last_updated: datetime

# Course progress
class CourseProgressSummary(BaseModel):
    course_id: int
    course_name: str
    level: str
    total_modules: int
    completed_modules: int
    total_lessons: int
    completed_lessons: int
    total_points: int
    possible_points: int
    progress_percentage: float
    estimated_completion_time: Optional[str] = None

# Learning analytics
class LearningAnalytics(BaseModel):
    user_id: int
    period_days: int = 30
    lessons_completed: int
    points_earned: int
    time_spent_hours: float
    average_accuracy: float
    streak_days: int
    most_difficult_words: List[dict] = []
    learning_velocity: float = 0.0  # lessons per day

# Progress filters
class ProgressFilters(BaseModel):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None
    status: Optional[str] = None
    is_completed: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# Batch progress update
class BatchProgressUpdate(BaseModel):
    user_id: int = Field(..., gt=0)
    progress_updates: List[dict] = Field(..., min_items=1, max_items=20)