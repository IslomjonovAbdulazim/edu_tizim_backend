from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime


# Lesson schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: bool = True
    order_index: int = 0
    base_points: int = Field(default=50, ge=0)


class LessonCreate(LessonBase):
    module_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None
    base_points: Optional[int] = Field(None, ge=0)


class LessonInDB(LessonBase):
    id: int
    module_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class LessonListResponse(BaseModel):
    lessons: List[LessonResponse]
    total: int


class LessonWithWords(LessonResponse):
    """Lesson response with words included"""
    words: List[dict] = []  # Will be populated with WordResponse objects


class LessonWithModuleInfo(LessonResponse):
    """Lesson with module and course information"""
    module_title: str
    course_name: str
    course_id: int


class LessonStatistics(BaseModel):
    """Lesson statistics"""
    lesson_id: int
    title: str
    base_points: int
    total_words: int
    active_words: int
    completion_points: int
    average_word_difficulty: float = 0.0


class LessonProgressSummary(BaseModel):
    """Progress summary for a lesson"""
    lesson_id: int
    lesson_title: str
    module_title: str
    course_name: str
    total_students: int
    completed_students: int
    average_completion: float
    average_attempts: float


# Lesson navigation
class LessonNavigation(BaseModel):
    current_lesson: LessonResponse
    previous_lesson: Optional[LessonResponse] = None
    next_lesson: Optional[LessonResponse] = None


# Lesson ordering
class LessonOrderUpdate(BaseModel):
    lesson_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)


class LessonReorderRequest(BaseModel):
    module_id: int
    lesson_orders: List[LessonOrderUpdate] = Field(..., min_items=1)


# Lesson difficulty analysis
class LessonDifficultyAnalysis(BaseModel):
    lesson_id: int
    title: str
    average_difficulty: float
    difficulty_distribution: dict  # {level: count}
    recommended_for_levels: List[str]  # ["beginner", "intermediate", etc.]


class LessonSearchFilters(BaseModel):
    """Filters for lesson search"""
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    difficulty_min: Optional[int] = Field(None, ge=1, le=5)
    difficulty_max: Optional[int] = Field(None, ge=1, le=5)
    has_content: Optional[bool] = None
    is_active: Optional[bool] = True