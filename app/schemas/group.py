from pydantic import BaseModel
from typing import Optional, List
from .base import BaseSchema, TimestampMixin
from .user import UserResponse


# Group Schemas
class GroupBase(BaseSchema):
    title: str
    schedule: Optional[str] = None  # "Mon,Wed,Fri 10:00-12:00"
    description: Optional[str] = None


class GroupCreate(GroupBase):
    branch_id: int
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None


class GroupUpdate(BaseModel):
    title: Optional[str] = None
    schedule: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None
    is_active: Optional[bool] = None


class GroupResponse(GroupBase, TimestampMixin):
    branch_id: int
    course_id: Optional[int]
    teacher_id: Optional[int]
    is_active: bool
    student_count: int = 0
    teacher_name: str = "No teacher assigned"


class GroupWithDetails(GroupResponse):
    """Group with additional details"""
    branch_title: Optional[str] = None
    course_name: Optional[str] = None
    students: List[UserResponse] = []


# Student-Group Management
class StudentGroupAssignment(BaseModel):
    user_id: int
    group_id: int


class StudentGroupBulkAssignment(BaseModel):
    group_id: int
    user_ids: List[int]


class GroupStudentsList(BaseModel):
    group_id: int
    students: List[UserResponse]
    total_students: int