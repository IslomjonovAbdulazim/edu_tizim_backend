from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import date, datetime
from app.schemas.user import UserResponse


class StudentBase(BaseModel):
    date_of_birth: Optional[date] = None
    grade_level: Optional[str] = Field(None, max_length=20)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    native_language: str = Field(default="uz", max_length=10)
    learning_language: str = Field(default="en", max_length=10)
    proficiency_level: str = Field(default="beginner", max_length=20)

    @validator('proficiency_level')
    def validate_proficiency(cls, v):
        allowed_levels = ["beginner", "elementary", "intermediate", "upper-intermediate", "advanced", "proficient"]
        if v not in allowed_levels:
            raise ValueError(f'Proficiency level must be one of: {", ".join(allowed_levels)}')
        return v


class StudentCreate(StudentBase):
    # User creation data
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class StudentUpdate(StudentBase):
    # Allow updating student-specific fields
    pass


class StudentInDB(StudentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: int
    user: UserResponse
    date_of_birth: Optional[date]
    grade_level: Optional[str]
    emergency_contact: Optional[str]
    native_language: str
    learning_language: str
    proficiency_level: str
    total_points: int = 0

    # Group information
    groups: Optional[List[str]] = []  # List of group names

    class Config:
        from_attributes = True


class StudentWithProgress(StudentResponse):
    # Additional progress information
    completed_lessons: int = 0
    current_module: Optional[str] = None
    current_lesson: Optional[str] = None
    completion_percentage: float = 0.0
    badges_count: int = 0
    current_streak: int = 0


class StudentListResponse(BaseModel):
    students: List[StudentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# For adding students to groups
class AddStudentToGroupRequest(BaseModel):
    student_id: int
    group_id: int


class RemoveStudentFromGroupRequest(BaseModel):
    student_id: int
    group_id: int


# Student search/filter parameters
class StudentFilters(BaseModel):
    search: Optional[str] = None  # Search in name
    proficiency_level: Optional[str] = None
    learning_language: Optional[str] = None
    group_id: Optional[int] = None
    is_active: Optional[bool] = True