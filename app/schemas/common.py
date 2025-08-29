from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int


# Sorting
class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC


# Base responses
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None


# ID references (avoid circular imports)
class IdReference(BaseModel):
    id: int
    name: str


class UserReference(BaseModel):
    id: int
    full_name: str
    role: str


# Common filters
class DateFilter(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ActiveFilter(BaseModel):
    is_active: Optional[bool] = None


# Statistics base
class BaseStatistics(BaseModel):
    total: int
    active: int
    created_today: int = 0
    created_this_week: int = 0


# Search request
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    filters: Optional[dict] = None
    pagination: Optional[PaginationParams] = PaginationParams()
    sort: Optional[SortParams] = SortParams()