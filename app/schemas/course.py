from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Course levels
class CourseLevel:
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# Base course schemas
class CourseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    level: str = Field(default=CourseLevel.BEGINNER)
    is_active: bool = True
    order_index: int = 0

    @validator('level')
    def validate_level(cls, v):
        valid_levels = [CourseLevel.BEGINNER, CourseLevel.INTERMEDIATE, CourseLevel.ADVANCED]
        if v not in valid_levels:
            raise ValueError(f'Level must be one of: {", ".join(valid_levels)}')
        return v

class CourseCreate(CourseBase):
    learning_center_id: int = Field(..., gt=0)

class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    level: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None

class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    level: str
    is_active: bool
    order_index: int
    learning_center_id: int
    total_modules: int = 0
    total_lessons: int = 0
    total_words: int = 0
    completion_points: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int

# Course with nested content
class CourseWithModules(CourseResponse):
    modules: List[dict] = []  # Will contain ModuleResponse objects

# Course statistics
class CourseStatistics(BaseModel):
    course_id: int
    name: str
    level: str
    total_modules: int
    active_modules: int
    total_lessons: int
    active_lessons: int
    total_words: int
    total_students_enrolled: int = 0
    completion_rate: float = 0.0
    average_progress: float = 0.0

# Course progress for users
class UserCourseProgress(BaseModel):
    course_id: int
    course_name: str
    level: str
    modules_completed: int = 0
    total_modules: int = 0
    lessons_completed: int = 0
    total_lessons: int = 0
    points_earned: int = 0
    total_possible_points: int = 0
    progress_percentage: float = 0.0
    last_activity: Optional[datetime] = None

# Course ordering
class CourseOrderUpdate(BaseModel):
    course_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)

class CourseReorderRequest(BaseModel):
    learning_center_id: int
    course_orders: List[CourseOrderUpdate] = Field(..., min_items=1)

# Course filters
class CourseFilters(BaseModel):
    level: Optional[str] = None
    is_active: Optional[bool] = None
    learning_center_id: Optional[int] = None
    search: Optional[str] = None  # Search in name or description