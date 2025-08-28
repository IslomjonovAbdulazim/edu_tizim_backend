from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime
from app.schemas.user import UserResponse


class ParentBase(BaseModel):
    occupation: Optional[str] = Field(None, max_length=100)
    workplace: Optional[str] = Field(None, max_length=100)
    relationship_to_student: Optional[str] = Field(None, max_length=50)
    alternative_contact: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)

    @validator('relationship_to_student')
    def validate_relationship(cls, v):
        if v is not None:
            allowed_relationships = ["father", "mother", "guardian", "uncle", "aunt", "grandfather", "grandmother",
                                     "other"]
            if v not in allowed_relationships:
                raise ValueError(f'Relationship must be one of: {", ".join(allowed_relationships)}')
        return v

    @validator('alternative_contact')
    def validate_alternative_contact(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Alternative contact must start with + or contain only digits')
        return v


class ParentCreate(ParentBase):
    # User creation data
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    telegram_id: int

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+') and not v.isdigit():
            raise ValueError('Phone number must start with + or contain only digits')
        return v


class ParentUpdate(ParentBase):
    # Allow updating parent-specific fields
    pass


class ParentInDB(ParentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentBasicInfo(BaseModel):
    id: int
    full_name: str
    proficiency_level: str
    total_points: int


class ParentResponse(BaseModel):
    id: int
    user: UserResponse
    occupation: Optional[str]
    workplace: Optional[str]
    relationship_to_student: Optional[str]
    alternative_contact: Optional[str]

    # Children information
    students: List[StudentBasicInfo] = []

    class Config:
        from_attributes = True


class ParentListResponse(BaseModel):
    parents: List[ParentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# For linking parents to students
class LinkParentStudentRequest(BaseModel):
    parent_id: int
    student_id: int
    relationship: Optional[str] = "parent"

    @validator('relationship')
    def validate_relationship(cls, v):
        allowed_relationships = ["father", "mother", "guardian", "uncle", "aunt", "grandfather", "grandmother", "other"]
        if v not in allowed_relationships:
            raise ValueError(f'Relationship must be one of: {", ".join(allowed_relationships)}')
        return v


class UnlinkParentStudentRequest(BaseModel):
    parent_id: int
    student_id: int


# Parent search/filter parameters
class ParentFilters(BaseModel):
    search: Optional[str] = None  # Search in name
    relationship_to_student: Optional[str] = None
    is_active: Optional[bool] = True