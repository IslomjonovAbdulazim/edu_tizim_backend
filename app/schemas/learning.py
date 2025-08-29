from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from .base import BaseSchema, TimestampMixin


# Progress Schemas
class ProgressBase(BaseSchema):
    user_id: int
    lesson_id: int
    completion_percentage: float = 0.0
    points: int = 0


class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseModel):
    completion_percentage: Optional[float] = None
    total_attempts: Optional[int] = None
    correct_answers: Optional[int] = None


class ProgressResponse(ProgressBase, TimestampMixin):
    is_completed: bool
    total_attempts: int
    correct_answers: int
    last_attempt_at: Optional[datetime]
    accuracy: float = 0.0


# Quiz Session Schemas
class QuizSessionBase(BaseSchema):
    user_id: int
    lesson_id: Optional[int] = None


class QuizSessionCreate(QuizSessionBase):
    pass


class QuizSessionUpdate(BaseModel):
    quiz_results: Optional[Dict] = None
    total_questions: Optional[int] = None
    correct_answers: Optional[int] = None
    completion_percentage: Optional[float] = None


class QuizSessionResponse(QuizSessionBase, TimestampMixin):
    quiz_results: Optional[Dict]
    total_questions: int
    correct_answers: int
    completion_percentage: float
    started_at: datetime
    completed_at: Optional[datetime]
    is_completed: bool
    accuracy: float = 0.0


# Quiz submission (for processing quiz results)
class QuizSubmission(BaseModel):
    user_id: int
    lesson_id: int
    word_results: Dict[int, bool]  # word_id -> correct/incorrect


class QuizResult(BaseModel):
    points_earned: int
    completion_percentage: float
    accuracy: float
    total_questions: int
    correct_answers: int


# WeakWord Schemas
class WeakWordBase(BaseSchema):
    user_id: int
    word_id: int


class WeakWordCreate(WeakWordBase):
    pass


class WeakWordUpdate(BaseModel):
    last_7_results: Optional[str] = None
    strength: Optional[str] = None


class WeakWordResponse(WeakWordBase, TimestampMixin):
    last_7_results: str
    total_attempts: int
    correct_attempts: int
    strength: str  # weak, medium, strong
    last_attempt_at: Optional[datetime]
    recent_accuracy: float = 0.0


class WeakWordWithDetails(WeakWordResponse):
    """WeakWord with word details"""
    foreign_form: str
    native_form: str
    example_sentence: Optional[str]
    audio_url: Optional[str]


# Learning Analytics Schemas
class UserLearningStats(BaseModel):
    user_id: int
    total_lessons: int
    completed_lessons: int
    completion_rate: float
    total_points: int
    average_accuracy: float
    weak_words_count: int
    strong_words_count: int


class LessonStats(BaseModel):
    lesson_id: int
    total_attempts: int
    completion_rate: float
    average_accuracy: float
    difficult_words: List[int]  # word_ids that are commonly missed