from pydantic import BaseModel, Field, ConfigDict, field_validator
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


from typing import Optional, Dict, List, Generic, TypeVar
from datetime import datetime
from enum import Enum
from .base import BaseSchema, TimestampMixin


class WordStrength(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


# Progress Schemas
class ProgressBase(BaseSchema):
    user_id: int = Field(..., gt=0, description="User ID")
    lesson_id: int = Field(..., gt=0, description="Lesson ID")
    completion_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Lesson completion percentage")
    points: int = Field(0, ge=0, description="Points earned from this lesson")



class ProgressOut(ProgressBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseSchema):
    completion_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    points: Optional[int] = Field(None, ge=0)
    total_attempts: Optional[int] = Field(None, ge=0)
    correct_answers: Optional[int] = Field(None, ge=0)

    @field_validator('correct_answers')
    def validate_correct_answers(cls, v, values):
        total = values.get('total_attempts')
        if v is not None and total is not None and v > total:
            raise ValueError('Correct answers cannot exceed total attempts')
        return v


class ProgressResponse(ProgressBase, TimestampMixin):
    is_completed: bool = Field(False, description="Whether lesson is completed")
    total_attempts: int = Field(0, ge=0, description="Total quiz attempts")
    correct_answers: int = Field(0, ge=0, description="Total correct answers")
    last_attempt_at: Optional[datetime] = Field(None, description="Last attempt timestamp")

    # Computed fields
    accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Overall accuracy percentage")

    @field_validator('accuracy', mode='before', validate_default=True)
    def calculate_accuracy(cls, v, values):
        total = values.get('total_attempts', 0)
        correct = values.get('correct_answers', 0)
        return round((correct / total * 100), 1) if total > 0 else 0.0


# Quiz Session Schemas

class QuizSessionOut(QuizSessionBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class QuizSessionBase(BaseSchema):
    user_id: int = Field(..., gt=0, description="User ID")
    lesson_id: Optional[int] = Field(None, gt=0, description="Lesson ID (optional for practice quizzes)")


class QuizSessionCreate(QuizSessionBase):
    pass


class QuizSessionUpdate(BaseSchema):
    quiz_results: Optional[Dict[int, bool]] = Field(None, description="Word ID to correct/incorrect mapping")
    total_questions: Optional[int] = Field(None, ge=0)
    correct_answers: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None

    @field_validator('correct_answers')
    def validate_correct_answers(cls, v, values):
        total = values.get('total_questions')
        if v is not None and total is not None and v > total:
            raise ValueError('Correct answers cannot exceed total questions')
        return v


class QuizSessionResponse(QuizSessionBase, TimestampMixin):
    quiz_results: Optional[Dict[int, bool]] = Field(None, description="Quiz results by word ID")
    total_questions: int = Field(0, ge=0, description="Total questions in quiz")
    correct_answers: int = Field(0, ge=0, description="Number of correct answers")
    completion_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Quiz completion percentage")
    started_at: datetime = Field(..., description="Quiz start time")
    completed_at: Optional[datetime] = Field(None, description="Quiz completion time")
    is_completed: bool = Field(False, description="Whether quiz is completed")

    # Computed fields
    accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Quiz accuracy percentage")
    duration_minutes: Optional[float] = Field(None, ge=0.0, description="Quiz duration in minutes")

    @field_validator('accuracy', mode='before', validate_default=True)
    def calculate_accuracy(cls, v, values):
        total = values.get('total_questions', 0)
        correct = values.get('correct_answers', 0)
        return round((correct / total * 100), 1) if total > 0 else 0.0

    @field_validator('duration_minutes', mode='before', validate_default=True)
    def calculate_duration(cls, v, values):
        start = values.get('started_at')
        end = values.get('completed_at')
        if start and end:
            delta = end - start
            return round(delta.total_seconds() / 60, 2)
        return None


# Quiz Submission and Results
class QuizSubmission(BaseSchema):
    """Submit quiz results"""
    user_id: int = Field(..., gt=0)
    lesson_id: int = Field(..., gt=0)
    word_results: Dict[int, bool] = Field(..., min_items=1, description="Word ID to correct/incorrect mapping")

    @field_validator('word_results')
    def validate_word_results(cls, v):
        if not v:
            raise ValueError('Quiz must have at least one word result')
        return v


class QuizResult(BaseSchema):
    """Quiz completion result"""
    points_earned: int = Field(..., ge=0, description="Points earned from quiz")
    completion_percentage: float = Field(..., ge=0.0, le=100.0, description="Completion percentage")
    accuracy: float = Field(..., ge=0.0, le=100.0, description="Accuracy percentage")
    total_questions: int = Field(..., gt=0, description="Total questions")
    correct_answers: int = Field(..., ge=0, description="Correct answers")
    time_taken: Optional[float] = Field(None, ge=0.0, description="Time taken in minutes")
    is_perfect: bool = Field(False, description="Whether quiz was completed with 100% accuracy")
    is_improvement: bool = Field(False, description="Whether this improved previous score")

    @field_validator('is_perfect', mode='before', validate_default=True)
    def set_is_perfect(cls, v, values):
        return values.get('accuracy', 0) == 100.0

    @field_validator('correct_answers')
    def validate_correct_answers(cls, v, values):
        total = values.get('total_questions', 0)
        if v > total:
            raise ValueError('Correct answers cannot exceed total questions')
        return v


# Weak Word Schemas

class WeakWordOut(WeakWordBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class WeakWordBase(BaseSchema):
    user_id: int = Field(..., gt=0, description="User ID")
    word_id: int = Field(..., gt=0, description="Word ID")


class WeakWordCreate(WeakWordBase):
    is_correct: bool = Field(..., description="Whether the first attempt was correct")


class WeakWordUpdate(BaseSchema):
    last_7_results: Optional[str] = Field(None, max_length=7, regex="^[01]*$",
                                          description="Last 7 attempts as binary string")
    strength: Optional[WordStrength] = None
    is_correct: Optional[bool] = Field(None, description="Add new attempt result")


class WeakWordResponse(WeakWordBase, TimestampMixin):
    last_7_results: str = Field("", max_length=7, description="Last 7 attempts (1=correct, 0=incorrect)")
    total_attempts: int = Field(0, ge=0, description="Total attempts")
    correct_attempts: int = Field(0, ge=0, description="Total correct attempts")
    strength: WordStrength = Field(WordStrength.WEAK, description="Word strength level")
    last_attempt_at: Optional[datetime] = Field(None, description="Last attempt timestamp")

    # Computed fields
    recent_accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Accuracy from last 7 attempts")
    overall_accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Overall accuracy")

    @field_validator('recent_accuracy', mode='before', validate_default=True)
    def calculate_recent_accuracy(cls, v, values):
        results = values.get('last_7_results', '')
        if not results:
            return 0.0
        correct = results.count('1')
        return round((correct / len(results) * 100), 1)

    @field_validator('overall_accuracy', mode='before', validate_default=True)
    def calculate_overall_accuracy(cls, v, values):
        total = values.get('total_attempts', 0)
        correct = values.get('correct_attempts', 0)
        return round((correct / total * 100), 1) if total > 0 else 0.0


class WeakWordWithDetails(WeakWordResponse):
    """Weak word with vocabulary details"""
    foreign_form: str = Field(..., description="Word in foreign language")
    native_form: str = Field(..., description="Word in native language")
    example_sentence: Optional[str] = Field(None, description="Example sentence")
    audio_url: Optional[str] = Field(None, description="Audio pronunciation URL")
    lesson_title: Optional[str] = Field(None, description="Lesson title")
    module_title: Optional[str] = Field(None, description="Module title")


# Learning Analytics
class UserLearningStats(BaseSchema):
    """Comprehensive user learning statistics"""
    user_id: int = Field(..., gt=0)

    # Lesson stats
    total_lessons: int = Field(0, ge=0, description="Total lessons accessed")
    completed_lessons: int = Field(0, ge=0, description="Lessons completed")
    completion_rate: float = Field(0.0, ge=0.0, le=100.0, description="Lesson completion rate")

    # Performance stats
    total_points: int = Field(0, ge=0, description="Total points earned")
    average_accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Average quiz accuracy")
    perfect_lessons: int = Field(0, ge=0, description="Lessons completed with 100% accuracy")

    # Vocabulary stats
    total_words_encountered: int = Field(0, ge=0, description="Total unique words encountered")
    weak_words_count: int = Field(0, ge=0, description="Current weak words count")
    strong_words_count: int = Field(0, ge=0, description="Strong/mastered words count")
    vocabulary_strength: float = Field(0.0, ge=0.0, le=100.0, description="Overall vocabulary strength")

    # Activity stats
    learning_streak: int = Field(0, ge=0, description="Current learning streak in days")
    total_quiz_attempts: int = Field(0, ge=0, description="Total quiz attempts")
    study_time_minutes: Optional[int] = Field(None, ge=0, description="Total study time in minutes")
    last_activity: Optional[datetime] = Field(None, description="Last learning activity")

    @field_validator('completion_rate', mode='before', validate_default=True)
    def calculate_completion_rate(cls, v, values):
        total = values.get('total_lessons', 0)
        completed = values.get('completed_lessons', 0)
        return round((completed / total * 100), 1) if total > 0 else 0.0

    @field_validator('vocabulary_strength', mode='before', validate_default=True)
    def calculate_vocabulary_strength(cls, v, values):
        total = values.get('total_words_encountered', 0)
        strong = values.get('strong_words_count', 0)
        return round((strong / total * 100), 1) if total > 0 else 0.0


class LessonStats(BaseSchema):
    """Lesson statistics across all users"""
    lesson_id: int = Field(..., gt=0)
    lesson_title: str = Field(..., description="Lesson title")

    # Attempt stats
    total_attempts: int = Field(0, ge=0, description="Total attempts by all users")
    unique_users: int = Field(0, ge=0, description="Number of unique users who attempted")
    completion_rate: float = Field(0.0, ge=0.0, le=100.0, description="Percentage of users who completed")

    # Performance stats
    average_accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Average accuracy across all attempts")
    average_attempts_to_complete: float = Field(0.0, ge=0.0, description="Average attempts needed to complete")

    # Word difficulty
    difficult_words: List[int] = Field(default_factory=list, description="Word IDs that users struggle with")
    easy_words: List[int] = Field(default_factory=list, description="Word IDs that users find easy")

    # Time analysis
    average_completion_time: Optional[float] = Field(None, ge=0.0, description="Average time to complete in minutes")


# Practice and Review
class PracticeRequest(BaseSchema):
    """Request for practice words"""
    user_id: int = Field(..., gt=0)
    max_words: int = Field(20, ge=1, le=50, description="Maximum words for practice")
    include_strengths: List[WordStrength] = Field([WordStrength.WEAK, WordStrength.MEDIUM],
                                                  description="Word strengths to include")
    lesson_id: Optional[int] = Field(None, gt=0, description="Limit to specific lesson")
    module_id: Optional[int] = Field(None, gt=0, description="Limit to specific module")


class PracticeSession(BaseSchema):
    """Practice session response"""
    user_id: int = Field(..., gt=0)
    words: List[WeakWordWithDetails] = Field(..., description="Words for practice")
    session_type: str = Field("practice", description="Type of practice session")
    estimated_duration: int = Field(..., ge=0, description="Estimated duration in minutes")
    difficulty_level: str = Field("mixed", description="Overall difficulty level")

# === Standard response wrappers ===
T = TypeVar('T')
class ResponseEnvelope(Generic[T], BaseSchema):
    data: T
    meta: Optional[dict] = None

class Paginated(Generic[T], BaseSchema):
    items: List[T]
    total: int
    page: int
    size: int
    has_next: bool
