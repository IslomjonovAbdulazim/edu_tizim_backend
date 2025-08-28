from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime


# Word schemas
class WordBase(BaseModel):
    foreign: str = Field(..., min_length=1, max_length=100)
    local: str = Field(..., min_length=1, max_length=100)
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    difficulty_level: int = Field(default=1, ge=1, le=5)
    word_type: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    order_index: int = 0


class WordCreate(WordBase):
    lesson_id: int


class WordUpdate(BaseModel):
    foreign: Optional[str] = Field(None, min_length=1, max_length=100)
    local: Optional[str] = Field(None, min_length=1, max_length=100)
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    word_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    order_index: Optional[int] = None


class WordInDB(WordBase):
    id: int
    lesson_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordResponse(BaseModel):
    id: int
    foreign: str
    local: str
    example_sentence: Optional[str]
    audio_url: Optional[str]
    difficulty_level: int
    word_type: Optional[str]
    is_active: bool
    order_index: int
    lesson_id: int
    points_value: int = 10

    class Config:
        from_attributes = True


class WordWithLessonInfo(WordResponse):
    """Word with lesson, module, and course information"""
    lesson_title: str
    module_title: str
    course_name: str
    course_id: int


class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int


# Word practice and learning
class WordPracticeAttempt(BaseModel):
    word_id: int
    user_answer: str
    is_correct: bool
    response_time_ms: Optional[int] = None
    attempt_type: str = Field(default="quiz")  # quiz, typing, audio, multiple_choice


class WordPracticeSession(BaseModel):
    lesson_id: int
    attempts: List[WordPracticeAttempt] = Field(..., min_items=1)
    session_duration_seconds: Optional[int] = None


class WordPracticeResult(BaseModel):
    word_id: int
    foreign: str
    local: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    points_earned: int


class WordStatistics(BaseModel):
    """Word statistics"""
    total_words: int
    average_difficulty: float
    words_with_audio: int
    words_without_audio: int
    audio_coverage_percentage: float
    difficulty_distribution: dict
    word_type_distribution: dict


# Word ordering and management
class WordOrderUpdate(BaseModel):
    word_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)


class WordReorderRequest(BaseModel):
    lesson_id: int
    word_orders: List[WordOrderUpdate] = Field(..., min_items=1)


# Bulk operations
class BulkWordUpdate(BaseModel):
    word_ids: List[int] = Field(..., min_items=1)
    update_data: WordUpdate


class BulkAudioUpdate(BaseModel):
    word_audio_map: dict = Field(..., description="Mapping of word_id to audio_url")


class BulkDifficultyUpdate(BaseModel):
    word_difficulty_map: dict = Field(..., description="Mapping of word_id to difficulty_level")


# Word search and filtering
class WordSearchFilters(BaseModel):
    lesson_id: Optional[int] = None
    module_id: Optional[int] = None
    course_id: Optional[int] = None
    learning_center_id: Optional[int] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    word_type: Optional[str] = None
    has_audio: Optional[bool] = None
    is_active: Optional[bool] = True


class RandomWordRequest(BaseModel):
    count: int = Field(..., ge=1, le=100)
    course_id: Optional[int] = None
    difficulty_range: Optional[tuple] = Field(None, description="(min_difficulty, max_difficulty)")
    exclude_word_ids: Optional[List[int]] = None
    word_types: Optional[List[str]] = None


# Word similarity and recommendations
class SimilarWordsRequest(BaseModel):
    word_id: int
    similarity_type: str = Field(default="foreign", regex="^(foreign|local)$")
    limit: int = Field(default=10, ge=1, le=50)


class WordRecommendation(BaseModel):
    word_id: int
    foreign: str
    local: str
    similarity_score: float = 0.0
    reason: str = "similar_pattern"  # similar_pattern, same_type, same_difficulty


class WordForReview(BaseModel):
    word_id: int
    foreign: str
    local: str
    difficulty_level: int
    last_practiced: Optional[datetime] = None
    success_rate: float = 0.0
    needs_review: bool = True
    priority_score: int = 0