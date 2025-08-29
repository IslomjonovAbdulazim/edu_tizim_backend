from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, time
from decimal import Decimal


class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    address: str = Field(..., min_length=5, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    phone_number: Optional[str] = Field(None, max_length=20)
    is_active: bool = True
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None

    @validator('phone_number')
    def validate_phone(cls, v):
        if v is not None:
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone number must start with + or contain only digits')
        return v


class BranchCreate(BranchBase):
    learning_center_id: int


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    phone_number: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None


class BranchInDB(BranchBase):
    id: int
    learning_center_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoordinatesResponse(BaseModel):
    latitude: float
    longitude: float


class BranchStats(BaseModel):
    total_groups: int = 0
    active_groups: int = 0
    total_students: int = 0


class BranchResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    address: str
    coordinates: Optional[CoordinatesResponse]
    phone_number: Optional[str]
    is_active: bool
    opening_time: Optional[time]
    closing_time: Optional[time]
    learning_center_id: int
    created_at: datetime
    stats: Optional[BranchStats] = None
    operating_hours: Optional[str] = None

    class Config:
        from_attributes = True


class BranchWithGroups(BranchResponse):
    """Branch response with groups included"""
    groups: List[dict] = []  # Will be populated with GroupResponse objects


class BranchListResponse(BaseModel):
    branches: List[BranchResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Branch management requests
class AssignStaffToBranchRequest(BaseModel):
    user_id: int
    branch_id: int


class BulkAssignStaffRequest(BaseModel):
    user_ids: List[int] = Field(..., min_items=1, max_items=50)
    branch_id: int


# Branch search and filtering
class BranchFilters(BaseModel):
    search: Optional[str] = None  # Search in name, address
    learning_center_id: Optional[int] = None
    is_active: Optional[bool] = True


# Location-based queries
class LocationSearchRequest(BaseModel):
    center_latitude: float = Field(..., ge=-90, le=90)
    center_longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(..., gt=0, le=100)  # Maximum 100km radius
    learning_center_id: Optional[int] = None


class BranchDistanceResponse(BaseModel):
    branch: BranchResponse
    distance_km: float
    is_nearby: bool  # Within specified radius


# Branch creation with limit validation
class CreateBranchRequest(BaseModel):
    branch_data: BranchCreate
    check_limits: bool = True  # Whether to check center limits before creating