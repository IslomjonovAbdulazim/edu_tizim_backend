from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, time


class GroupBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    max_capacity: int = Field(default=20, ge=1, le=50)
    is_active: bool = True
    schedule_days: Optional[str] = Field(None, max_length=20)  # e.g., "Mon,Wed,Fri"
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @validator('schedule_days')
    def validate_schedule_days(cls, v):
        if v is not None:
            allowed_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            days = [day.strip() for day in v.split(',')]
            for day in days:
                if day not in allowed_days:
                    raise ValueError(f'Invalid day: {day}. Allowed days: {", ".join(allowed_days)}')
        return v


class GroupCreate(GroupBase):
    branch_id: int  # Groups must belong to a specific branch
    course_id: int
    learning_center_id: int  # Keep for compatibility
    teacher_id: Optional[int] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    max_capacity: Optional[int] = Field(None, ge=1, le=50)
    is_active: Optional[bool] = None
    schedule_days: Optional[str] = Field(None, max_length=20)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    branch_id: Optional[int] = None  # Allow moving group to different branch
    teacher_id: Optional[int] = None


class GroupInDB(GroupBase):
    id: int
    branch_id: int
    course_id: int
    learning_center_id: int
    teacher_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentBasicInfo(BaseModel):
    id: int
    full_name: str
    phone_number: str


class TeacherInfo(BaseModel):
    id: int
    full_name: str
    phone_number: str
    subject_specialization: Optional[str]


class CourseInfo(BaseModel):
    id: int
    name: str
    level: str


class BranchInfo(BaseModel):
    id: int
    name: str
    address: str


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    max_capacity: int
    current_capacity: int
    available_spots: int
    capacity_percentage: float
    is_active: bool
    is_full: bool
    schedule_days: Optional[str]
    start_time: Optional[time]
    end_time: Optional[time]

    # Related data
    branch: BranchInfo  # Branch information
    course: CourseInfo
    teacher: Optional[TeacherInfo] = None
    students: List[StudentBasicInfo] = []

    # Location info
    full_location: str  # Branch name
    branch_address: str

    class Config:
        from_attributes = True


class GroupListResponse(BaseModel):
    groups: List[GroupResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Group student management
class AddStudentToGroupRequest(BaseModel):
    student_id: int

    @validator('student_id')
    def validate_student_id(cls, v):
        if v <= 0:
            raise ValueError('Student ID must be positive')
        return v


class BulkStudentOperationRequest(BaseModel):
    student_ids: List[int] = Field(..., min_items=1)

    @validator('student_ids')
    def validate_student_ids(cls, v):
        if not all(student_id > 0 for student_id in v):
            raise ValueError('All student IDs must be positive')
        if len(set(v)) != len(v):
            raise ValueError('Student IDs must be unique')
        return v


# Group transfer between branches
class TransferGroupToBranchRequest(BaseModel):
    group_id: int
    target_branch_id: int
    reason: Optional[str] = None


# Group filtering and search
class GroupFilters(BaseModel):
    search: Optional[str] = None  # Search in name
    branch_id: Optional[int] = None  # Filter by branch
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None
    learning_center_id: Optional[int] = None  # Keep for compatibility
    is_active: Optional[bool] = True
    has_capacity: Optional[bool] = None  # Groups with available spots
    schedule_day: Optional[str] = None  # Filter by specific day


# Branch-specific group management
class BranchGroupSummary(BaseModel):
    branch_id: int
    branch_name: str
    total_groups: int
    active_groups: int
    total_students: int
    total_capacity: int
    utilization_rate: float
    groups_at_capacity: int
    available_spots: int


class BranchGroupsResponse(BaseModel):
    branch: BranchInfo
    groups: List[GroupResponse]
    summary: BranchGroupSummary


# Group statistics
class GroupStatistics(BaseModel):
    group_id: int
    group_name: str
    branch_name: str
    total_students: int
    active_students: int
    average_progress: float
    completion_rate: float