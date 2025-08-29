from pydantic import BaseModel
from typing import Optional, List
from .base import BaseSchema, TimestampMixin


# Course Schemas
class CourseBase(BaseSchema):
    name: str
    description: Optional[str] = None
    level: str = "beginner"  # beginner, intermediate, advanced
    order_index: int = 0


class CourseCreate(CourseBase):
    learning_center_id: int


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class CourseResponse(CourseBase, TimestampMixin):
    learning_center_id: int
    is_active: bool
    total_modules: int = 0
    total_lessons: int = 0
    total_words: int = 0


# Module Schemas
class ModuleBase(BaseSchema):
    title: str
    description: Optional[str] = None
    order_index: int = 0


class ModuleCreate(ModuleBase):
    course_id: int


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class ModuleResponse(ModuleBase, TimestampMixin):
    course_id: int
    is_active: bool
    total_lessons: int = 0
    total_words: int = 0


# Lesson Schemas
class LessonBase(BaseSchema):
    title: str
    description: Optional[str] = None
    order_index: int = 0


class LessonCreate(LessonBase):
    module_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class LessonResponse(LessonBase, TimestampMixin):
    module_id: int
    is_active: bool
    total_words: int = 0


# Word Schemas
class WordBase(BaseSchema):
    foreign_form: str  # English
    native_form: str   # Uzbek
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    order_index: int = 0


class WordCreate(WordBase):
    lesson_id: int


class WordUpdate(BaseModel):
    foreign_form: Optional[str] = None
    native_form: Optional[str] = None
    example_sentence: Optional[str] = None
    audio_url: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class WordResponse(WordBase, TimestampMixin):
    lesson_id: int
    is_active: bool


# Nested response schemas for hierarchical views
class LessonWithWords(LessonResponse):
    words: List[WordResponse] = []


class ModuleWithLessons(ModuleResponse):
    lessons: List[LessonResponse] = []


class ModuleWithFullContent(ModuleResponse):
    lessons: List[LessonWithWords] = []


class CourseWithModules(CourseResponse):
    modules: List[ModuleResponse] = []


class CourseWithFullContent(CourseResponse):
    modules: List[ModuleWithFullContent] = []


# Bulk operations
class WordBulkCreate(BaseModel):
    lesson_id: int
    words: List[WordBase]


class WordBulkUpdate(BaseModel):
    word_updates: List[dict]  # List of {id: int, **WordUpdate}