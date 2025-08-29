from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator, Field
from datetime import datetime


class WeakListBase(BaseModel):
    is_active: bool = True


class WeakListCreate(WeakListBase):
    user_id: int


class WeakListUpdate(BaseModel):
    is_active: Optional[bool] = None


class WeakListWordBase(BaseModel):
    is_active: bool = True


class WeakListWordCreate(WeakListWordBase):
    weak_list_id: int
    word_id: int


class WeakListWordUpdate(BaseModel):
    is_active: Optional[bool] = None


# Quiz attempt schemas
class QuizAttempt(BaseModel):
    word_id: int = Field(..., gt=0)
    is_correct: bool
    quiz_type: str = Field(default="multiple_choice")
    response_time_ms: Optional[int] = Field(None, ge=0)
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None

    @validator('quiz_type')
    def validate_quiz_type(cls, v):
        allowed_types = ["multiple_choice", "typing", "audio", "translation", "matching"]
        if v not in allowed_types:
            raise ValueError(f'Quiz type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('response_time_ms')
    def validate_response_time(cls, v):
        if v is not None and v > 300000:  # 5 minutes max
            raise ValueError('Response time cannot exceed 5 minutes')
        return v


class BulkQuizSession(BaseModel):
    user_id: int = Field(..., gt=0)
    attempts: List[QuizAttempt] = Field(..., min_items=1, max_items=50)
    session_start: Optional[datetime] = None
    session_duration_ms: Optional[int] = Field(None, ge=0)

    @validator('attempts')
    def validate_unique_words(cls, v):
        # Allow multiple attempts for same word in one session
        return v


# Word information for weak list
class WordInfo(BaseModel):
    id: int
    foreign: str
    local: str
    example_sentence: Optional[str]
    difficulty_level: int
    word_type: Optional[str]
    lesson_title: str
    module_title: str
    course_name: str


class QuizHistoryEntry(BaseModel):
    is_correct: bool
    quiz_type: str
    timestamp: datetime
    response_time_ms: Optional[int]


class WeakListWordResponse(BaseModel):
    id: int
    word: WordInfo
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    recent_accuracy: float
    performance_level: str  # excellent, good, weak, critical
    needs_review: bool
    is_mastered: bool
    quiz_history: List[QuizHistoryEntry] = []
    first_attempt_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    last_correct_at: Optional[datetime]
    mistake_pattern: Dict[str, Any]

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id: int
    full_name: str


class WeakListResponse(BaseModel):
    id: int
    user: UserInfo
    is_active: bool
    total_words: int
    weak_words_count: int
    strong_words_count: int
    needs_review_count: int
    words: List[WeakListWordResponse] = []

    class Config:
        from_attributes = True


class WeakListInDB(WeakListBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Quiz session results
class QuizSessionResult(BaseModel):
    total_attempts: int
    correct_count: int
    accuracy: float
    words_updated: List[Dict[str, Any]]
    new_review_words: List[int]
    session_summary: str


# Performance analysis
class WordPerformance(BaseModel):
    word_id: int
    word_foreign: str
    word_local: str
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    recent_accuracy: float
    performance_level: str
    needs_review: bool
    is_mastered: bool
    quiz_history: List[Dict[str, Any]]
    mistake_pattern: Dict[str, Any]
    first_attempt: Optional[str]
    last_attempt: Optional[str]
    last_correct: Optional[str]


class PerformanceBreakdown(BaseModel):
    excellent: int = 0
    good: int = 0
    weak: int = 0
    critical: int = 0


class RecentActivity(BaseModel):
    words_practiced_week: int = 0
    attempts_this_week: int = 0


class WeakListStatistics(BaseModel):
    total_words: int
    total_attempts: int
    overall_accuracy: float
    words_needing_review: int
    mastered_words: int
    performance_breakdown: PerformanceBreakdown
    recent_activity: RecentActivity


# Learning suggestions
class LearningSuggestion(BaseModel):
    type: str
    priority: str  # urgent, high, medium, low
    message: str
    action: str

    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ["urgent", "high", "medium", "low"]
        if v not in allowed_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v


class FocusWord(BaseModel):
    word_id: int
    word: str  # "foreign - local"
    accuracy: float
    attempts: int


class LearningSuggestions(BaseModel):
    suggestions: List[LearningSuggestion]
    focus_words: List[FocusWord]


# Review and practice requests
class ReviewWordsRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    limit: int = Field(default=20, ge=1, le=50)
    performance_level: Optional[str] = None  # weak, critical

    @validator('performance_level')
    def validate_performance_level(cls, v):
        if v is not None:
            allowed_levels = ["excellent", "good", "weak", "critical"]
            if v not in allowed_levels:
                raise ValueError(f'Performance level must be one of: {", ".join(allowed_levels)}')
        return v


class WordsListResponse(BaseModel):
    words: List[WeakListWordResponse]
    total: int
    metadata: Dict[str, Any] = {}


# Word management
class AddWordToWeakListRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    word_id: int = Field(..., gt=0)


class RemoveWordFromWeakListRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    word_id: int = Field(..., gt=0)


class ResetWordProgressRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    word_id: int = Field(..., gt=0)
    confirm: bool = Field(default=False)

    @validator('confirm')
    def validate_confirm(cls, v):
        if not v:
            raise ValueError('Must confirm before resetting word progress')
        return v


# Analytics and reporting
class WeakListAnalytics(BaseModel):
    user_id: int
    total_words_practiced: int
    overall_accuracy: float
    improvement_trend: str  # improving, declining, stable
    most_difficult_words: List[Dict[str, Any]]
    recent_progress: List[Dict[str, Any]]  # Daily progress for last 7 days
    learning_velocity: float  # Words mastered per week
    consistency_score: float  # How regularly user practices


class ComparePerformance(BaseModel):
    word_id: int
    word: str
    user_accuracy: float
    average_accuracy: float  # Across all users in learning center
    difficulty_level: int
    relative_performance: str  # above_average, below_average, average


# Filters and search
class WeakListFilters(BaseModel):
    user_id: Optional[int] = None
    performance_level: Optional[str] = None
    needs_review: Optional[bool] = None
    is_mastered: Optional[bool] = None
    min_attempts: Optional[int] = Field(None, ge=0)
    max_accuracy: Optional[float] = Field(None, ge=0.0, le=100.0)
    last_attempt_days: Optional[int] = Field(None, ge=0)  # Last attempt within X days


# Export and backup
class ExportWeakListRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    format: str = Field(default="json")
    include_quiz_history: bool = True
    include_timestamps: bool = True

    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ["json", "csv", "excel"]
        if v not in allowed_formats:
            raise ValueError(f'Format must be one of: {", ".join(allowed_formats)}')
        return v