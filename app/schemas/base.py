from pydantic import BaseModel, ConfigDict, Field, field_validator

from datetime import datetime
from typing import Optional, List, TypeVar, Generic


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )


class TimestampMixin(BaseSchema):
    """Mixin for models with timestamps"""
    id: int = Field(..., gt=0, description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(True, description="Soft delete flag")


class PaginationParams(BaseSchema):
    """Common pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> 'PaginatedResponse[T]':
        """Create paginated response"""
        pages = (total + size - 1) // size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response format"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[T] = Field(None, description="Response data")


class ErrorResponse(BaseSchema):
    """Standard error response format"""
    success: bool = Field(False, description="Operation success status")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    details: Optional[dict] = Field(None, description="Additional error details")


# Common field validators
class PhoneNumberMixin(BaseSchema):
    """Mixin for phone number validation"""

    @classmethod
    def validate_phone(cls, phone: str) -> str:
        """Validate and normalize phone number"""
        import re
        if not phone:
            raise ValueError("Phone number is required")

        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())

        # Ensure international format
        if not cleaned.startswith('+'):
            raise ValueError('Phone number must start with + (international format)')

        # Validate format: +[country_code][number]
        if not re.match(r'^\+[1-9]\d{9,19}$', cleaned):
            raise ValueError('Invalid international phone number format')

        return cleaned


class NameMixin(BaseSchema):
    """Mixin for name validation"""

    @classmethod
    def validate_name(cls, name: str) -> str:
        """Validate and normalize name"""
        if not name:
            raise ValueError("Name is required")

        name = name.strip()
        if len(name) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(name) > 100:
            raise ValueError('Name must not exceed 100 characters')

        # Allow letters, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\u00C0-\u017F\u0400-\u04FF\s\-']+$", name):
            raise ValueError('Name contains invalid characters')

        return name


# Search and filter schemas
class SearchParams(BaseSchema):
    """Common search parameters"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")


class FilterParams(BaseSchema):
    """Common filter parameters"""
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")


class SortParams(BaseSchema):
    """Common sort parameters"""
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="Sort order")

    @property
    def is_ascending(self) -> bool:
        return self.sort_order == "asc"

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
