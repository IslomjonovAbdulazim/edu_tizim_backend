from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime


# Course schemas
class CourseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    language_from: str = Field(default="uz", max_length=10)
    language_to: str = Field(default="en", max_length=10)
    level: str = Field(default="beginner", max_length=20)
    is_active: bool = True
    order_index: int = 0

    @validator('level')
    def validate_level(cls, v):
        allowed_levels = ["beginner", "elementary", "intermediate", "upper-intermediate", "advanced", "proficient"]
        if v not in allowed_levels:
            raise ValueError(f'Level must be one of: {", ".join(allowed_levels)}')
        return v


class CourseCreate(CourseBase):
    learning_center_id: int


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None


class CourseInDB(CourseBase):
    id: int
    learning_center_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    language_from: str
    language_to: str
    level: str
    is_active: bool
    order_index: int
    total_modules: int = 0
    total_lessons: int = 0
    total_words: int = 0

    class Config:
        from_attributes = True


class CourseWithModules(CourseResponse):
    """Course response with modules included"""
    modules: List[dict] = []  # Will be populated with ModuleResponse objects


class CourseStatistics(BaseModel):
    """Course statistics"""
    course_id: int
    name: str
    total_modules: int
    total_lessons: int
    total_words: int
    enrolled_students: int
    average_progress: float
    completion_rate: float


class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int


# Course ordering
class CourseOrderUpdate(BaseModel):
    course_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)


class CourseReorderRequest(BaseModel):
    learning_center_id: int
    course_orders: List[CourseOrderUpdate] = Field(..., min_items=1)


# Course search and filtering
class CourseSearchFilters(BaseModel):
    learning_center_id: Optional[int] = None
    level: Optional[str] = None
    language_from: Optional[str] = None
    language_to: Optional[str] = None
    is_active: Optional[bool] = True