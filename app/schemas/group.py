from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


from typing import Optional, List, Generic, TypeVar
from .base import BaseSchema, TimestampMixin
from .user import UserResponse


# Group Schemas
class GroupBase(BaseSchema):
    title: str = Field(..., min_length=2, max_length=100, description="Group name")
    schedule: Optional[str] = Field(None, max_length=200,
                                    description="Group schedule (e.g., 'Mon,Wed,Fri 10:00-12:00')")
    description: Optional[str] = Field(None, max_length=1000, description="Group description")

    @field_validator('title')
    def validate_title(cls, v):
        return v.strip()

    @field_validator('schedule')
    def validate_schedule(cls, v):
        if v:
            v = v.strip()
            # Basic validation for schedule format
            if len(v) < 3:
                raise ValueError('Schedule must be at least 3 characters')
        return v



class GroupOut(GroupBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class GroupCreate(GroupBase):
    branch_id: int = Field(..., gt=0, description="Branch ID where group is located")
    course_id: Optional[int] = Field(None, gt=0, description="Course ID (optional)")
    teacher_id: Optional[int] = Field(None, gt=0, description="Teacher ID (optional)")


class GroupUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    schedule: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    course_id: Optional[int] = Field(None, gt=0)
    teacher_id: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

    @field_validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v

    @field_validator('schedule')
    def validate_schedule(cls, v):
        if v:
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Schedule must be at least 3 characters')
        return v


class GroupResponse(GroupBase, TimestampMixin):
    branch_id: int = Field(..., gt=0)
    course_id: Optional[int] = Field(None, gt=0)
    teacher_id: Optional[int] = Field(None, gt=0)

    # Statistics
    student_count: int = Field(0, ge=0, description="Number of active students")
    max_capacity: int = Field(25, gt=0, description="Maximum student capacity")

    # Display fields
    teacher_name: str = Field("No teacher assigned", description="Teacher's full name")
    branch_name: Optional[str] = Field(None, description="Branch name")
    course_name: Optional[str] = Field(None, description="Course name")

    # Computed fields
    is_full: bool = Field(False, description="Whether group is at capacity")
    available_spots: int = Field(0, ge=0, description="Available student spots")
    capacity_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Capacity utilization percentage")

    @field_validator('is_full', mode='before', validate_default=True)
    def set_is_full(cls, v, values):
        student_count = values.get('student_count', 0)
        max_capacity = values.get('max_capacity', 25)
        return student_count >= max_capacity

    @field_validator('available_spots', mode='before', validate_default=True)
    def calculate_available_spots(cls, v, values):
        student_count = values.get('student_count', 0)
        max_capacity = values.get('max_capacity', 25)
        return max(0, max_capacity - student_count)

    @field_validator('capacity_percentage', mode='before', validate_default=True)
    def calculate_capacity_percentage(cls, v, values):
        student_count = values.get('student_count', 0)
        max_capacity = values.get('max_capacity', 25)
        return round((student_count / max_capacity * 100), 1) if max_capacity > 0 else 0.0


class GroupWithDetails(GroupResponse):
    """Group with detailed information and relationships"""
    students: List[UserResponse] = Field(default_factory=list, description="Students in the group")
    learning_center_id: Optional[int] = Field(None, gt=0, description="Learning center ID")
    learning_center_name: Optional[str] = Field(None, description="Learning center name")

    # Additional statistics
    active_students: int = Field(0, ge=0, description="Number of active students")
    average_progress: float = Field(0.0, ge=0.0, le=100.0, description="Average student progress")
    group_performance_score: float = Field(0.0, ge=0.0, le=100.0, description="Overall group performance")

    @field_validator('active_students', mode='before', validate_default=True)
    def count_active_students(cls, v, values):
        students = values.get('students', [])
        return len([s for s in students if s.is_active]) if students else 0


# Student Group Assignment Schemas
class StudentGroupAssignment(BaseSchema):
    """Single student-group assignment"""
    user_id: int = Field(..., gt=0, description="Student user ID")
    group_id: int = Field(..., gt=0, description="Group ID")


class StudentGroupBulkAssignment(BaseSchema):
    """Bulk student-group assignment"""
    group_id: int = Field(..., gt=0, description="Target group ID")
    user_ids: List[int] = Field(..., min_items=1, max_items=50, description="Student user IDs")

    @field_validator('user_ids')
    def validate_unique_user_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate user IDs found')
        if len(v) > 50:
            raise ValueError('Cannot assign more than 50 students at once')
        return v


class StudentGroupRemoval(BaseSchema):
    """Remove student from group"""
    user_id: int = Field(..., gt=0, description="Student user ID")
    group_id: int = Field(..., gt=0, description="Group ID")
    reason: Optional[str] = Field(None, max_length=200, description="Reason for removal")


class StudentGroupTransfer(BaseSchema):
    """Transfer student between groups"""
    user_id: int = Field(..., gt=0, description="Student user ID")
    from_group_id: int = Field(..., gt=0, description="Source group ID")
    to_group_id: int = Field(..., gt=0, description="Target group ID")
    reason: Optional[str] = Field(None, max_length=200, description="Reason for transfer")

    @field_validator('to_group_id')
    def validate_different_groups(cls, v, values):
        from_group = values.get('from_group_id')
        if v == from_group:
            raise ValueError('Source and target groups cannot be the same')
        return v


# Group Lists and Collections
class GroupStudentsList(BaseSchema):
    """List of students in a group"""
    group_id: int = Field(..., gt=0)
    group_title: str = Field(..., description="Group title")
    students: List[UserResponse] = Field(..., description="Students in group")
    total_students: int = Field(..., ge=0, description="Total number of students")
    active_students: int = Field(..., ge=0, description="Number of active students")

    @field_validator('total_students', mode='before', validate_default=True)
    def set_total_students(cls, v, values):
        students = values.get('students', [])
        return len(students)

    @field_validator('active_students', mode='before', validate_default=True)
    def count_active_students(cls, v, values):
        students = values.get('students', [])
        return len([s for s in students if s.is_active])


class GroupsList(BaseSchema):
    """List of groups with summary info"""
    groups: List[GroupResponse] = Field(..., description="Groups")
    total_groups: int = Field(..., ge=0, description="Total number of groups")
    active_groups: int = Field(..., ge=0, description="Number of active groups")
    total_students: int = Field(..., ge=0, description="Total students across all groups")

    @field_validator('total_groups', mode='before', validate_default=True)
    def set_total_groups(cls, v, values):
        groups = values.get('groups', [])
        return len(groups)

    @field_validator('active_groups', mode='before', validate_default=True)
    def count_active_groups(cls, v, values):
        groups = values.get('groups', [])
        return len([g for g in groups if g.is_active])

    @field_validator('total_students', mode='before', validate_default=True)
    def sum_total_students(cls, v, values):
        groups = values.get('groups', [])
        return sum(g.student_count for g in groups)


# Teacher Assignment
class TeacherAssignment(BaseSchema):
    """Assign teacher to group"""
    group_id: int = Field(..., gt=0, description="Group ID")
    teacher_id: int = Field(..., gt=0, description="Teacher user ID")


class TeacherRemoval(BaseSchema):
    """Remove teacher from group"""
    group_id: int = Field(..., gt=0, description="Group ID")
    reason: Optional[str] = Field(None, max_length=200, description="Reason for removal")


# Group Search and Filtering
class GroupSearchRequest(BaseSchema):
    """Search and filter groups"""
    query: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    branch_id: Optional[int] = Field(None, gt=0, description="Filter by branch")
    course_id: Optional[int] = Field(None, gt=0, description="Filter by course")
    teacher_id: Optional[int] = Field(None, gt=0, description="Filter by teacher")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_teacher: Optional[bool] = Field(None, description="Filter by teacher assignment")
    is_full: Optional[bool] = Field(None, description="Filter by capacity")
    min_students: Optional[int] = Field(None, ge=0, description="Minimum student count")
    max_students: Optional[int] = Field(None, ge=0, description="Maximum student count")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Results offset")


# Group Analytics
class GroupAnalytics(BaseSchema):
    """Group performance analytics"""
    group_id: int = Field(..., gt=0)
    group_title: str = Field(..., description="Group title")

    # Student metrics
    total_students: int = Field(..., ge=0)
    active_students: int = Field(..., ge=0)
    retention_rate: float = Field(..., ge=0.0, le=100.0, description="Student retention rate")

    # Performance metrics
    average_progress: float = Field(..., ge=0.0, le=100.0, description="Average student progress")
    average_quiz_score: float = Field(..., ge=0.0, le=100.0, description="Average quiz scores")
    completion_rate: float = Field(..., ge=0.0, le=100.0, description="Lesson completion rate")

    # Engagement metrics
    active_learners: int = Field(..., ge=0, description="Students active in last 7 days")
    quiz_participation: float = Field(..., ge=0.0, le=100.0, description="Quiz participation rate")

    # Ranking
    group_rank: Optional[int] = Field(None, gt=0, description="Group's rank compared to other groups")


class GroupCapacityInfo(BaseSchema):
    """Group capacity information"""
    group_id: int = Field(..., gt=0)
    current_students: int = Field(..., ge=0, description="Current number of students")
    max_capacity: int = Field(..., gt=0, description="Maximum capacity")
    available_spots: int = Field(..., ge=0, description="Available spots")
    is_full: bool = Field(..., description="Whether group is at capacity")
    capacity_percentage: float = Field(..., ge=0.0, le=100.0, description="Current capacity usage")
    recommended_capacity: int = Field(..., gt=0, description="Recommended optimal capacity")

    @field_validator('available_spots', mode='before', validate_default=True)
    def calculate_available_spots(cls, v, values):
        current = values.get('current_students', 0)
        max_cap = values.get('max_capacity', 25)
        return max(0, max_cap - current)

    @field_validator('is_full', mode='before', validate_default=True)
    def set_is_full(cls, v, values):
        current = values.get('current_students', 0)
        max_cap = values.get('max_capacity', 25)
        return current >= max_cap

    @field_validator('capacity_percentage', mode='before', validate_default=True)
    def calculate_percentage(cls, v, values):
        current = values.get('current_students', 0)
        max_cap = values.get('max_capacity', 25)
        return round((current / max_cap * 100), 1) if max_cap > 0 else 0.0


# Batch Operations
class BulkGroupUpdate(BaseSchema):
    """Bulk update multiple groups"""
    group_ids: List[int] = Field(..., min_items=1, max_items=20, description="Group IDs to update")
    updates: GroupUpdate = Field(..., description="Updates to apply")

    @field_validator('group_ids')
    def validate_unique_group_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate group IDs found')
        return v


class GroupCreationBatch(BaseSchema):
    """Create multiple groups at once"""
    branch_id: int = Field(..., gt=0, description="Target branch ID")
    groups: List[GroupBase] = Field(..., min_items=1, max_items=10, description="Groups to create")

    @field_validator('groups')
    def validate_unique_titles(cls, groups):
        titles = [g.title.lower() for g in groups]
        if len(titles) != len(set(titles)):
            raise ValueError('Duplicate group titles found in batch')
        return groups

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
