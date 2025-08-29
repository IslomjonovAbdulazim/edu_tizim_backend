from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Word types
class WordType:
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    PRONOUN = "pronoun"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"
    PHRASE = "phrase"

# Base word schemas
class WordBase(BaseModel):
    foreign: str = Field(..., min_length=1, max_length=100)
    local: str = Field(..., min_length=1, max_length=100)
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    difficulty_level: int = Field(default=1, ge=1, le=5)
    word_type: Optional[str] = None
    is_active: bool = True
    order_index: int = 0

    @validator('word_type')
    def validate_word_type(cls, v):
        if v is not None:
            valid_types = [WordType.NOUN, WordType.VERB, WordType.ADJECTIVE, WordType.ADVERB,
                          WordType.PREPOSITION, WordType.PRONOUN, WordType.CONJUNCTION,
                          WordType.INTERJECTION, WordType.PHRASE]
            if v not in valid_types:
                raise ValueError(f'Word type must be one of: {", ".join(valid_types)}')
        return v

class WordCreate(WordBase):
    lesson_id: int = Field(..., gt=0)

class WordUpdate(BaseModel):
    foreign: Optional[str] = Field(None, min_length=1, max_length=100)
    local: Optional[str] = Field(None, min_length=1, max_length=100)
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    word_type: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None

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
    created_at: datetime

    class Config:
        from_attributes = True

class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int

# Word with lesson context
class WordWithContext(WordResponse):
    lesson_title: str
    module_title: str
    course_name: str
    course_level: str

# Word practice
class WordPracticeAttempt(BaseModel):
    word_id: int = Field(..., gt=0)
    user_answer: str = Field(..., min_length=1, max_length=200)
    is_correct: bool
    attempt_type: str = Field(default="translation")  # translation, multiple_choice, audio
    response_time_ms: Optional[int] = Field(None, ge=0)

    @validator('attempt_type')
    def validate_attempt_type(cls, v):
        valid_types = ["translation", "multiple_choice", "audio", "typing", "listening"]
        if v not in valid_types:
            raise ValueError(f'Attempt type must be one of: {", ".join(valid_types)}')
        return v

class WordPracticeSession(BaseModel):
    lesson_id: int = Field(..., gt=0)
    attempts: List[WordPracticeAttempt] = Field(..., min_items=1)
    session_duration_seconds: Optional[int] = Field(None, ge=0)

class WordPracticeResult(BaseModel):
    word_id: int
    is_correct: bool
    correct_answer: str
    user_answer: str
    points_earned: int = 0

# Bulk word operations
class BulkWordCreate(BaseModel):
    lesson_id: int = Field(..., gt=0)
    words: List[WordBase] = Field(..., min_items=1, max_items=50)

class WordImport(BaseModel):
    lesson_id: int = Field(..., gt=0)
    csv_data: str  # CSV string with word data
    has_headers: bool = True

# Word statistics
class WordStatistics(BaseModel):
    word_id: int
    foreign: str
    local: str
    difficulty_level: int
    attempts_count: int = 0
    correct_attempts: int = 0
    accuracy_rate: float = 0.0
    average_response_time: Optional[float] = None

# Word filters
class WordFilters(BaseModel):
    lesson_id: Optional[int] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    word_type: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None  # Search in foreign or local text