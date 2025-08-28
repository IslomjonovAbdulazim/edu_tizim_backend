from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, date


class WeekListBase(BaseModel):
    week_start_date: date
    week_end_date: date
    is_active: bool = True
    is_completed: bool = False
    generation_context: Optional[str] = None  # JSON string with algorithm details

    @validator('week_end_date')
    def validate_week_dates(cls, v, values):
        if 'week_start_date' in values:
            start_date = values['week_start_date']
            if v <= start_date:
                raise ValueError('Week end date must be after start date')
            # Check if it's exactly 6 days later (Monday to Sunday)
            if (v - start_date).days != 6:
                raise ValueError('Week must be exactly 7 days (Monday to Sunday)')
        return v


class WeekListCreate(WeekListBase):
    user_id: int


class WeekListUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_completed: Optional[bool] = None


class WeekListWordBase(BaseModel):
    practice_count: int = Field(default=0, ge=0)
    correct_count: int = Field(default=0, ge=0)
    is_mastered: bool = False
    priority_score: int = Field(default=0, ge=0)
    difficulty_multiplier: int = Field(default=1, ge=1, le=5)


class WeekListWordCreate(WeekListWordBase):
    week_list_id: int
    word_id: int


class WeekListWordUpdate(BaseModel):
    practice_count: Optional[int] = Field(None, ge=0)
    correct_count: Optional[int] = Field(None, ge=0)
    is_mastered: Optional[bool] = None
    priority_score: Optional[int] = Field(None, ge=0)


# Word information for weeklist
class WordInfo(BaseModel):
    id: int
    foreign: str
    local: str
    example_sentence: Optional[str]
    audio_url: Optional[str]
    difficulty_level: int
    word_type: Optional[str]
    lesson_title: str
    module_title: str
    course_name: str


class WeekListWordResponse(BaseModel):
    id: int
    word: WordInfo
    practice_count: int
    correct_count: int
    accuracy_percentage: float
    is_mastered: bool
    priority_score: int
    difficulty_multiplier: int

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id: int
    full_name: str


class WeekListResponse(BaseModel):
    id: int
    user: UserInfo
    week_start_date: date
    week_end_date: date
    is_active: bool
    is_completed: bool
    total_words: int
    completed_words: int
    completion_percentage: float
    words: List[WeekListWordResponse] = []

    class Config:
        from_attributes = True


class WeekListInDB(WeekListBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Practice session schemas
class PracticeAttempt(BaseModel):
    word_id: int
    is_correct: bool
    response_time_ms: Optional[int] = None  # Response time in milliseconds
    attempt_type: str = Field(default="quiz")  # quiz, typing, audio, etc.


class PracticeSessionRequest(BaseModel):
    week_list_id: int
    attempts: List[PracticeAttempt] = Field(..., min_items=1)


class PracticeSessionResponse(BaseModel):
    success: bool
    message: str
    session_stats: dict
    words_mastered: List[int] = []  # IDs of newly mastered words
    badges_earned: List[str] = []  # Badge types earned
    weeklist_completed: bool = False


# Weekly list generation request
class GenerateWeekListRequest(BaseModel):
    user_id: int
    week_start_date: date
    max_words: int = Field(default=50, ge=10, le=100)
    difficulty_preference: str = Field(default="balanced")  # easy, balanced, hard, adaptive
    include_review: bool = True  # Include words from previous weeks

    @validator('difficulty_preference')
    def validate_difficulty(cls, v):
        allowed = ["easy", "balanced", "hard", "adaptive"]
        if v not in allowed:
            raise ValueError(f'Difficulty must be one of: {", ".join(allowed)}')
        return v


# Algorithm context for weeklist generation
class WeekListAlgorithmContext(BaseModel):
    user_progress_analysis: dict
    difficulty_adjustment: float
    review_words_count: int
    new_words_count: int
    priority_factors: dict
    algorithm_version: str = "1.0"


# Weekly statistics
class WeeklyStats(BaseModel):
    week_start_date: date
    total_practice_sessions: int
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    words_mastered: int
    average_session_time: int  # in seconds
    streak_days: int


class WeekListProgress(BaseModel):
    week_list_id: int
    week_start_date: date
    week_end_date: date
    progress_by_day: List[dict]  # Daily progress breakdown
    total_progress: float
    is_on_track: bool
    estimated_completion_date: Optional[date]


# List responses
class WeekListListResponse(BaseModel):
    weeklists: List[WeekListResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class WeekListFilters(BaseModel):
    user_id: Optional[int] = None
    is_active: Optional[bool] = True
    is_completed: Optional[bool] = None
    week_start_from: Optional[date] = None
    week_start_to: Optional[date] = None


# Bulk operations
class BulkMasterWordsRequest(BaseModel):
    week_list_id: int
    word_ids: List[int] = Field(..., min_items=1)


class WeekListAnalytics(BaseModel):
    user_id: int
    total_weeklists: int
    completed_weeklists: int
    completion_rate: float
    average_accuracy: float
    total_words_mastered: int
    current_streak: int
    longest_streak: int
    favorite_word_types: List[str]