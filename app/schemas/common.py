from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum

# Generic type for paginated responses
T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    total_pages: int
    has_next: bool
    has_prev: bool

    @validator('total_pages', always=True)
    def calculate_total_pages(cls, v, values):
        if 'total' in values and 'per_page' in values:
            import math
            return math.ceil(values['total'] / values['per_page'])
        return v

    @validator('has_next', always=True)
    def calculate_has_next(cls, v, values):
        if 'page' in values and 'total_pages' in values:
            return values['page'] < values['total_pages']
        return False

    @validator('has_prev', always=True)
    def calculate_has_prev(cls, v, values):
        if 'page' in values:
            return values['page'] > 1
        return False


class PaginationParams(BaseModel):
    """Common pagination parameters"""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Common sorting parameters"""
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC


# Standard API response wrapper
class APIResponse(BaseModel, Generic[T]):
    """Standard API response format"""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    error_code: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Date range filtering
class DateRangeFilter(BaseModel):
    """Common date range filter"""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v and 'date_from' in values and values['date_from']:
            if v < values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v


class SearchFilter(BaseModel):
    """Common search filter"""
    search: Optional[str] = Field(None, min_length=1, max_length=100)
    search_fields: List[str] = Field(default=["name", "title"])


# File upload response
class FileUploadResponse(BaseModel):
    """File upload response"""
    success: bool = True
    message: str = "File uploaded successfully"
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    file_url: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)


# Bulk operation responses
class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    success: bool = True
    message: str = "Bulk operation completed"
    total_processed: int
    successful_operations: int
    failed_operations: int
    errors: List[dict] = []


class BulkDeleteRequest(BaseModel):
    """Request for bulk delete operations"""
    ids: List[int] = Field(..., min_items=1, max_items=100)

    @validator('ids')
    def validate_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('IDs must be unique')
        if any(id_val <= 0 for id_val in v):
            raise ValueError('All IDs must be positive integers')
        return v


# Statistics and analytics common schemas
class StatsPeriod(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class StatsRequest(BaseModel):
    """Common statistics request"""
    period: StatsPeriod = StatsPeriod.MONTH
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    group_by: Optional[str] = "day"  # day, week, month

    @validator('group_by')
    def validate_group_by(cls, v):
        allowed = ["day", "week", "month", "year"]
        if v not in allowed:
            raise ValueError(f'group_by must be one of: {", ".join(allowed)}')
        return v


class MetricPoint(BaseModel):
    """Single metric data point"""
    timestamp: datetime
    value: float
    label: Optional[str] = None


class MetricSeries(BaseModel):
    """Series of metric data points"""
    name: str
    description: Optional[str] = None
    data_points: List[MetricPoint]
    total: Optional[float] = None
    average: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"


# Notification schemas
class NotificationLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationResponse(BaseModel):
    """Notification message"""
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_url: Optional[str] = None
    is_read: bool = False


# Activity logging
class ActivityType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACHIEVEMENT = "achievement"
    PROGRESS = "progress"


class ActivityLog(BaseModel):
    """Activity log entry"""
    user_id: int
    activity_type: ActivityType
    resource_type: str  # "lesson", "word", "badge", etc.
    resource_id: Optional[int] = None
    description: str
    metadata: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# System health and status
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class ServiceHealth(BaseModel):
    """Individual service health"""
    service_name: str
    status: HealthStatus
    response_time_ms: Optional[int] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict] = None


class SystemHealth(BaseModel):
    """Overall system health"""
    status: HealthStatus
    services: List[ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: int
    version: str


# ID-based references (for avoiding circular imports)
class IdReference(BaseModel):
    """Simple ID reference"""
    id: int
    name: Optional[str] = None


class UserReference(IdReference):
    """User reference"""
    full_name: str
    role: str


class CourseReference(IdReference):
    """Course reference"""
    name: str
    level: str


class LessonReference(IdReference):
    """Lesson reference"""
    title: str
    module_title: str


# Validation helpers
def validate_positive_int(v: int) -> int:
    if v <= 0:
        raise ValueError('Value must be positive')
    return v


def validate_percentage(v: float) -> float:
    if not 0.0 <= v <= 100.0:
        raise ValueError('Percentage must be between 0.0 and 100.0')
    return v


def validate_phone_number(v: str) -> str:
    if not v.startswith('+') and not v.isdigit():
        raise ValueError('Phone number must start with + or contain only digits')
    return v