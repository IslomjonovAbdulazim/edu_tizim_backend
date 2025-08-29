from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import date, datetime
from app.schemas.user import UserResponse


class TeacherBase(BaseModel):
    subject_specialization: Optional[str] = Field(None, max_length=100)
    teaching_experience_years: Optional[int] = Field(default=0, ge=0)
    qualification: Optional[str] = Field(None, max_length=200)
    employment_type: str = Field(default="full_time", max_length=20)
    hire_date: Optional[date] = None
    bio: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

    @validator('employment_type')
    def validate_employment_type(cls, v):
        allowed_types = ["full_time", "part_time", "contract", "volunteer"]
        if v not in allowed_types:
            raise ValueError(f'Employment type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('teaching_experience_years')
    def validate_experience(cls, v):
        if v is not None and v < 0:
            raise ValueError('Teaching experience cannot be negative')
        if v is not None and v > 50:
            raise ValueError('Teaching experience seems unrealistic (max 50 years)')
        return v


class TeacherCreate(TeacherBase):
    # User creation data
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class TeacherUpdate(TeacherBase):
    # Allow updating teacher-specific fields
    pass


class TeacherInDB(TeacherBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupBasicInfo(BaseModel):
    id: int
    name: str
    students_count: int
    max_capacity: int
    course_name: str


class TeacherResponse(BaseModel):
    id: int
    user: UserResponse
    subject_specialization: Optional[str]
    teaching_experience_years: Optional[int]
    qualification: Optional[str]
    employment_type: str
    hire_date: Optional[date]
    bio: Optional[str]
    experience_level: str  # Computed property
    active_groups_count: int = 0

    # Group information
    groups: Optional[List[GroupBasicInfo]] = []

    class Config:
        from_attributes = True


class TeacherWithStats(TeacherResponse):
    # Additional statistics
    total_students: int = 0
    average_group_size: float = 0.0
    groups_at_capacity: int = 0
    teaching_load_percentage: float = 0.0  # Based on max groups capacity


class TeacherListResponse(BaseModel):
    teachers: List[TeacherResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Teacher assignment requests
class AssignTeacherToGroupRequest(BaseModel):
    teacher_id: int
    group_id: int


class UnassignTeacherFromGroupRequest(BaseModel):
    group_id: int


class BulkTeacherAssignmentRequest(BaseModel):
    teacher_id: int
    group_ids: List[int] = Field(..., min_items=1, max_items=10)


# Teacher search and filters
class TeacherFilters(BaseModel):
    search: Optional[str] = None  # Search in name, subject, qualification
    subject_specialization: Optional[str] = None
    employment_type: Optional[str] = None
    experience_min: Optional[int] = Field(None, ge=0)
    experience_max: Optional[int] = Field(None, ge=0)
    has_groups: Optional[bool] = None
    is_active: Optional[bool] = True

    @validator('experience_max')
    def validate_experience_range(cls, v, values):
        if v is not None and 'experience_min' in values and values['experience_min'] is not None:
            if v < values['experience_min']:
                raise ValueError('Maximum experience must be greater than minimum experience')
        return v


# Teacher availability and workload
class TeacherAvailability(BaseModel):
    teacher_id: int
    teacher_name: str
    current_groups_count: int
    max_recommended_groups: int = 5
    available_capacity: int
    is_available: bool
    employment_type: str


class TeacherWorkloadSummary(BaseModel):
    teacher_id: int
    teacher_name: str
    groups: List[GroupBasicInfo]
    total_students: int
    workload_percentage: float
    recommended_action: str  # "balanced", "underutilized", "overloaded"


# Teacher performance and statistics
class TeacherStatistics(BaseModel):
    total_teachers: int
    active_teachers: int
    inactive_teachers: int
    average_experience_years: float
    employment_distribution: dict
    subject_distribution: dict
    teachers_with_groups: int
    teachers_without_groups: int
    group_assignment_rate: float
    experience_distribution: dict


class SubjectSpecialization(BaseModel):
    subject: str
    teachers_count: int
    avg_experience: float


class TeacherAnalytics(BaseModel):
    learning_center_id: int
    total_teachers: int
    subject_specializations: List[SubjectSpecialization]
    employment_breakdown: dict
    experience_levels: dict
    group_coverage: dict  # How well groups are covered by teachers