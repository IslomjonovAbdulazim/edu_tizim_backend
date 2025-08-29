from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Base lesson schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: bool = True
    order_index: int = 0
    base_points: int = Field(default=50, ge=0)

class LessonCreate(LessonBase):
    module_id: int = Field(..., gt=0)

class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None
    base_points: Optional[int] = Field(None, ge=0)

class LessonResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    content: Optional[str]
    is_active: bool
    order_index: int
    base_points: int
    module_id: int
    total_words: int = 0
    completion_points: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class LessonListResponse(BaseModel):
    lessons: List[LessonResponse]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int

# Lesson with words
class LessonWithWords(LessonResponse):
    words: List[dict] = []  # Will contain WordResponse objects

# Lesson with progress info
class LessonWithProgress(LessonResponse):
    user_progress: Optional[dict] = None  # ProgressResponse
    is_completed: bool = False
    user_points: int = 0
    accuracy_percentage: float = 0.0

# Lesson statistics
class LessonStatistics(BaseModel):
    lesson_id: int
    title: str
    module_title: str
    course_name: str
    total_words: int
    active_words: int
    base_points: int
    completion_points: int
    students_attempted: int = 0
    students_completed: int = 0
    average_accuracy: float = 0.0
    average_completion_time: Optional[int] = None  # seconds

# Lesson practice session
class LessonPracticeStart(BaseModel):
    lesson_id: int = Field(..., gt=0)
    practice_type: str = Field(default="quiz")  # quiz, review, test

class LessonPracticeResult(BaseModel):
    lesson_id: int
    correct_answers: int = Field(..., ge=0)
    total_questions: int = Field(..., gt=0)
    points_earned: int = Field(..., ge=0)
    completion_time_seconds: Optional[int] = Field(None, ge=0)
    is_completed: bool = False

    @validator('correct_answers')
    def validate_answers(cls, v, values):
        if 'total_questions' in values and v > values['total_questions']:
            raise ValueError('Correct answers cannot exceed total questions')
        return v

# Lesson ordering
class LessonOrderUpdate(BaseModel):
    lesson_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)

class LessonReorderRequest(BaseModel):
    module_id: int
    lesson_orders: List[LessonOrderUpdate] = Field(..., min_items=1)

# Lesson filters
class LessonFilters(BaseModel):
    module_id: Optional[int] = None
    course_id: Optional[int] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None