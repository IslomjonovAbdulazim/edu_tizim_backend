from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime


# Module schemas
class ModuleBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    order_index: int = 0


class ModuleCreate(ModuleBase):
    course_id: int


class ModuleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None


class ModuleInDB(ModuleBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModuleResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_active: bool
    order_index: int
    course_id: int
    total_lessons: int = 0
    total_words: int = 0
    completion_points: int = 0

    class Config:
        from_attributes = True


class ModuleListResponse(BaseModel):
    modules: List[ModuleResponse]
    total: int


class ModuleWithLessons(ModuleResponse):
    """Module response with lessons included"""
    lessons: List[dict] = []  # Will be populated with LessonResponse objects


class ModuleStatistics(BaseModel):
    """Module statistics"""
    module_id: int
    title: str
    total_lessons: int
    active_lessons: int
    total_words: int
    completion_points: int
    student_progress: Optional[dict] = None


# Module ordering
class ModuleOrderUpdate(BaseModel):
    module_id: int = Field(..., gt=0)
    order_index: int = Field(..., ge=0)


class ModuleReorderRequest(BaseModel):
    course_id: int
    module_orders: List[ModuleOrderUpdate] = Field(..., min_items=1)