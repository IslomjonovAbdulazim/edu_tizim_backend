from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List
from enum import Enum
from .base import BaseSchema, TimestampMixin


class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Course Schemas
class CourseBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=100, description="Course name")
    description: Optional[str] = Field(None, max_length=1000, description="Course description")
    level: CourseLevel = Field(CourseLevel.BEGINNER, description="Course difficulty level")
    order_index: int = Field(0, ge=0, description="Display order")

    @validator('name')
    def validate_name(cls, v):
        return v.strip()


class CourseCreate(CourseBase):
    learning_center_id: int = Field(..., gt=0, description="Learning center ID")


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    level: Optional[CourseLevel] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CourseResponse(CourseBase, TimestampMixin):
    learning_center_id: int = Field(..., gt=0)

    # Statistics
    total_modules: int = Field(0, ge=0, description="Number of modules")
    total_lessons: int = Field(0, ge=0, description="Number of lessons")
    total_words: int = Field(0, ge=0, description="Number of words")
    enrolled_students: int = Field(0, ge=0, description="Number of enrolled students")


# Module Schemas
class ModuleBase(BaseSchema):
    title: str = Field(..., min_length=2, max_length=100, description="Module title")
    description: Optional[str] = Field(None, max_length=1000, description="Module description")
    order_index: int = Field(0, ge=0, description="Display order within course")

    @validator('title')
    def validate_title(cls, v):
        return v.strip()


class ModuleCreate(ModuleBase):
    course_id: int = Field(..., gt=0, description="Course ID")


class ModuleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ModuleResponse(ModuleBase, TimestampMixin):
    course_id: int = Field(..., gt=0)

    # Statistics
    total_lessons: int = Field(0, ge=0, description="Number of lessons")
    total_words: int = Field(0, ge=0, description="Number of words")
    completion_rate: float = Field(0.0, ge=0.0, le=100.0, description="Average completion rate")


# Lesson Schemas
class LessonBase(BaseSchema):
    title: str = Field(..., min_length=2, max_length=100, description="Lesson title")
    description: Optional[str] = Field(None, max_length=1000, description="Lesson description")
    content: Optional[str] = Field(None, max_length=10000, description="Lesson content (Markdown)")
    order_index: int = Field(0, ge=0, description="Display order within module")

    @validator('title')
    def validate_title(cls, v):
        return v.strip()


class LessonCreate(LessonBase):
    module_id: int = Field(..., gt=0, description="Module ID")


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = Field(None, max_length=10000)
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class LessonResponse(LessonBase, TimestampMixin):
    module_id: int = Field(..., gt=0)

    # Statistics
    total_words: int = Field(0, ge=0, description="Number of words in lesson")
    average_completion: float = Field(0.0, ge=0.0, le=100.0, description="Average completion rate")
    quiz_attempts: int = Field(0, ge=0, description="Total quiz attempts")


# Word Schemas
class WordBase(BaseSchema):
    foreign_form: str = Field(..., min_length=1, max_length=100, description="Word in foreign language")
    native_form: str = Field(..., min_length=1, max_length=100, description="Word in native language")
    example_sentence: Optional[str] = Field(None, max_length=500, description="Example sentence")
    audio_url: Optional[HttpUrl] = Field(None, description="Audio pronunciation URL")
    image_url: Optional[HttpUrl] = Field(None, description="Visual reference image URL")
    order_index: int = Field(0, ge=0, description="Display order within lesson")

    @validator('foreign_form', 'native_form')
    def validate_word_forms(cls, v):
        return v.strip()


class WordCreate(WordBase):
    lesson_id: int = Field(..., gt=0, description="Lesson ID")


class WordUpdate(BaseModel):
    foreign_form: Optional[str] = Field(None, min_length=1, max_length=100)
    native_form: Optional[str] = Field(None, min_length=1, max_length=100)
    example_sentence: Optional[str] = Field(None, max_length=500)
    audio_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class WordResponse(WordBase, TimestampMixin):
    lesson_id: int = Field(..., gt=0)

    # Learning statistics
    difficulty_rating: float = Field(0.0, ge=0.0, le=5.0, description="Difficulty rating (0-5)")
    success_rate: float = Field(0.0, ge=0.0, le=100.0, description="Success rate in quizzes")


# Nested Schemas for Hierarchical Data
class WordInLesson(WordResponse):
    """Word with minimal data for lesson view"""
    pass


class LessonWithWords(LessonResponse):
    """Lesson with all its words"""
    words: List[WordInLesson] = Field(default_factory=list)


class LessonInModule(LessonResponse):
    """Lesson with minimal data for module view"""
    pass


class ModuleWithLessons(ModuleResponse):
    """Module with all its lessons"""
    lessons: List[LessonInModule] = Field(default_factory=list)


class ModuleWithFullContent(ModuleResponse):
    """Module with lessons and words"""
    lessons: List[LessonWithWords] = Field(default_factory=list)


class ModuleInCourse(ModuleResponse):
    """Module with minimal data for course view"""
    pass


class CourseWithModules(CourseResponse):
    """Course with all its modules"""
    modules: List[ModuleInCourse] = Field(default_factory=list)


class CourseWithFullContent(CourseResponse):
    """Course with complete hierarchy"""
    modules: List[ModuleWithFullContent] = Field(default_factory=list)


# Bulk Operations
class WordBulkCreate(BaseModel):
    """Bulk create words for a lesson"""
    lesson_id: int = Field(..., gt=0, description="Target lesson ID")
    words: List[WordBase] = Field(..., min_items=1, max_items=100, description="Words to create")

    @validator('words')
    def validate_unique_words(cls, words):
        foreign_forms = [w.foreign_form.lower() for w in words]
        if len(foreign_forms) != len(set(foreign_forms)):
            raise ValueError('Duplicate foreign forms found in batch')
        return words


class WordBulkUpdate(BaseModel):
    """Bulk update words"""
    updates: List[dict] = Field(..., min_items=1, max_items=100, description="Word updates with IDs")

    @validator('updates')
    def validate_updates(cls, updates):
        for update in updates:
            if 'id' not in update:
                raise ValueError('Each update must include word ID')
        return updates


class WordImportRequest(BaseModel):
    """Import words from file or external source"""
    lesson_id: int = Field(..., gt=0)
    source_type: str = Field(..., regex="^(csv|json|xlsx)$")
    source_data: str = Field(..., description="Base64 encoded file data or JSON string")
    overwrite_existing: bool = Field(False, description="Whether to overwrite existing words")


# Search and Query Schemas
class ContentSearchRequest(BaseModel):
    """Search across content"""
    query: str = Field(..., min_length=1, max_length=100)
    learning_center_id: int = Field(..., gt=0)
    content_type: Optional[str] = Field(None, regex="^(course|module|lesson|word)$")
    level: Optional[CourseLevel] = None
    limit: int = Field(20, ge=1, le=100)


class WordSearchRequest(BaseModel):
    """Search words specifically"""
    query: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[int] = Field(None, gt=0)
    module_id: Optional[int] = Field(None, gt=0)
    course_id: Optional[int] = Field(None, gt=0)
    learning_center_id: int = Field(..., gt=0)
    search_in: str = Field("both", regex="^(foreign|native|both|example)$")
    limit: int = Field(20, ge=1, le=100)


# Content Analytics
class ContentStatistics(BaseModel):
    """Content usage statistics"""
    learning_center_id: int = Field(..., gt=0)
    total_courses: int = Field(0, ge=0)
    total_modules: int = Field(0, ge=0)
    total_lessons: int = Field(0, ge=0)
    total_words: int = Field(0, ge=0)
    most_popular_course: Optional[str] = None
    average_completion_rate: float = Field(0.0, ge=0.0, le=100.0)
    content_engagement_score: float = Field(0.0, ge=0.0, le=100.0)