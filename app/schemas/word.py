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

    @validator('word_type')
    def validate_word_type(cls, v):
        if v is not None:
            allowed_types = ["noun", "verb", "adjective", "adverb", "preposition", "conjunction", "pronoun", "interjection", "article"]
            if v not in allowed_types:
                raise ValueError(f'Word type must be one of: {", ".join(allowed_types)}')
        return v


class WordCreate(WordBase):
    lesson_id: int

    @validator('lesson_id')
    def validate_lesson_id(cls, v):
        if v <= 0:
            raise ValueError('Lesson ID must be positive')
        return v


class WordUpdate(BaseModel):
    foreign: Optional[str] = Field(None, min_length=1, max_length=100)
    local: Optional[str] = Field(None, min_length=1, max_length=100)
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    word_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    order_index: Optional[int] = None

    @validator('word_type')
    def validate_word_type(cls, v):
        if v is not None:
            allowed_types = ["noun", "verb", "adjective", "adverb", "preposition", "conjunction", "pronoun", "interjection", "article"]
            if v not in allowed_types:
                raise ValueError(f'Word type must be one of: {", ".join(allowed_types)}')
        return v


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
    learning_center_id: int


class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Word practice and learning
class WordPracticeAttempt(BaseModel):
    word_id: int
    user_answer: str
    correct_answer: str
    is_correct: bool
    response_time_ms: Optional[int] = None
    attempt_type: str = Field(default="quiz")  # quiz, typing, audio, multiple_choice

    @validator('attempt_type')
    def validate_attempt_type(cls, v):
        allowed_types = ["quiz", "typing", "audio", "multiple_choice", "translation"]
        if v not in allowed_types:
            raise ValueError(f'Attempt type must be one of: {", ".join(allowed_types)}')
        return v


class WordPracticeSession(BaseModel):
    lesson_id: int
    attempts: List[WordPracticeAttempt] = Field(..., min_items=1)
    session_duration_seconds: Optional[int] = None

    @validator('session_duration_seconds')
    def validate_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError('Session duration cannot be negative')
        return v


class WordPracticeResult(BaseModel):
    word_id: int
    foreign: str
    local: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    points_earned: int
    difficulty_level: int


class WordStatistics(BaseModel):
    """Word statistics for a learning center or course"""
    total_words: int
    average_difficulty: float
    words_with_audio: int
    words_without_audio: int
    audio_coverage_percentage: float
    difficulty_distribution: dict  # {level: count}
    word_type_distribution: dict  # {type: count}


# Word ordering and management
class WordOrderUpdate(BaseModel):
    word_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)


class WordReorderRequest(BaseModel):
    lesson_id: int
    word_orders: List[WordOrderUpdate] = Field(..., min_items=1)

    @validator('word_orders')
    def validate_unique_words(cls, v):
        word_ids = [order.word_id for order in v]
        if len(set(word_ids)) != len(word_ids):
            raise ValueError('Word IDs must be unique in reorder request')
        return v


# Bulk operations
class BulkWordUpdate(BaseModel):
    word_ids: List[int] = Field(..., min_items=1, max_items=100)
    update_data: WordUpdate

    @validator('word_ids')
    def validate_word_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('Word IDs must be unique')
        if any(word_id <= 0 for word_id in v):
            raise ValueError('All word IDs must be positive')
        return v


class BulkAudioUpdate(BaseModel):
    word_audio_map: dict = Field(..., description="Mapping of word_id to audio_url")

    @validator('word_audio_map')
    def validate_audio_map(cls, v):
        if not v:
            raise ValueError('Audio map cannot be empty')
        for word_id, audio_url in v.items():
            try:
                int(word_id)
            except ValueError:
                raise ValueError('All keys must be valid word IDs')
            if not isinstance(audio_url, str):
                raise ValueError('All audio URLs must be strings')
        return v


class BulkDifficultyUpdate(BaseModel):
    word_difficulty_map: dict = Field(..., description="Mapping of word_id to difficulty_level")

    @validator('word_difficulty_map')
    def validate_difficulty_map(cls, v):
        if not v:
            raise ValueError('Difficulty map cannot be empty')
        for word_id, difficulty in v.items():
            try:
                int(word_id)
            except ValueError:
                raise ValueError('All keys must be valid word IDs')
            if not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
                raise ValueError('All difficulty levels must be integers between 1 and 5')
        return v


# Word search and filtering
class WordSearchFilters(BaseModel):
    search: Optional[str] = Field(None, min_length=1)
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
    lesson_id: Optional[int] = None
    difficulty_range: Optional[tuple] = Field(None, description="(min_difficulty, max_difficulty)")
    exclude_word_ids: Optional[List[int]] = None
    word_types: Optional[List[str]] = None

    @validator('difficulty_range')
    def validate_difficulty_range(cls, v):
        if v is not None:
            if len(v) != 2:
                raise ValueError('Difficulty range must be a tuple of (min, max)')
            min_diff, max_diff = v
            if not (1 <= min_diff <= 5) or not (1 <= max_diff <= 5):
                raise ValueError('Difficulty levels must be between 1 and 5')
            if min_diff > max_diff:
                raise ValueError('Minimum difficulty cannot be greater than maximum')
        return v


# Word similarity and recommendations
class SimilarWordsRequest(BaseModel):
    word_id: int = Field(..., gt=0)
    similarity_type: str = Field(default="foreign")
    limit: int = Field(default=10, ge=1, le=50)

    @validator('similarity_type')
    def validate_similarity_type(cls, v):
        allowed_types = ["foreign", "local", "both"]
        if v not in allowed_types:
            raise ValueError(f'Similarity type must be one of: {", ".join(allowed_types)}')
        return v


class WordRecommendation(BaseModel):
    word_id: int
    foreign: str
    local: str
    difficulty_level: int
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(default="similar_pattern")

    @validator('reason')
    def validate_reason(cls, v):
        allowed_reasons = ["similar_pattern", "same_type", "same_difficulty", "same_lesson", "related_meaning"]
        if v not in allowed_reasons:
            raise ValueError(f'Reason must be one of: {", ".join(allowed_reasons)}')
        return v


# Import/Export
class WordImportRequest(BaseModel):
    lesson_id: int = Field(..., gt=0)
    words: List[WordCreate] = Field(..., min_items=1, max_items=100)


class WordExportRequest(BaseModel):
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None
    format: str = Field(default="json")
    include_audio_urls: bool = False

    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ["json", "csv", "xlsx"]
        if v not in allowed_formats:
            raise ValueError(f'Export format must be one of: {", ".join(allowed_formats)}')
        return v