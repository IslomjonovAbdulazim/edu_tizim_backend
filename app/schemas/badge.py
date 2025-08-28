from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime
from app.constants.badge_types import BadgeType, BadgeCategory


class BadgeBase(BaseModel):
    badge_type: BadgeType
    level: int = Field(default=1, ge=1)
    count: int = Field(default=1, ge=1)
    description: Optional[str] = Field(None, max_length=255)
    context_data: Optional[str] = None  # JSON string
    is_active: bool = True


class BadgeCreate(BaseModel):
    user_id: int
    badge_type: BadgeType
    level: int = Field(default=1, ge=1)
    count: int = Field(default=1, ge=1)
    description: Optional[str] = Field(None, max_length=255)
    context_data: Optional[str] = None

    @validator('badge_type')
    def validate_badge_type(cls, v):
        # Ensure badge_type is valid
        if v not in BadgeType.__members__.values():
            raise ValueError(f'Invalid badge type: {v}')
        return v


class BadgeUpdate(BaseModel):
    level: Optional[int] = Field(None, ge=1)
    count: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class BadgeInDB(BadgeBase):
    id: int
    user_id: int
    earned_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id: int
    full_name: str
    role: str


class BadgeResponse(BaseModel):
    id: int
    user: UserInfo
    badge_type: str
    badge_name: str
    badge_icon: str
    badge_category: str
    level: int
    count: int
    description: Optional[str]
    earned_at: datetime
    is_active: bool
    is_level_badge: bool

    class Config:
        from_attributes = True


class BadgeEarnedResponse(BaseModel):
    """Response for when a badge is newly earned"""
    success: bool
    message: str
    badge: BadgeResponse
    is_new_badge: bool = True
    next_level_threshold: Optional[int] = None


# Badge granting request (for admin/system)
class GrantBadgeRequest(BaseModel):
    user_id: int
    badge_type: BadgeType
    context: Optional[str] = None

    @validator('badge_type')
    def validate_badge_type(cls, v):
        if v not in BadgeType.__members__.values():
            raise ValueError(f'Invalid badge type: {v}')
        return v


# Badge progress tracking
class BadgeProgressRequest(BaseModel):
    user_id: int
    badge_type: BadgeType
    increment: int = Field(default=1, ge=1)
    context: Optional[str] = None


class BadgeProgressResponse(BaseModel):
    badge_type: str
    current_count: int
    current_level: int
    next_threshold: Optional[int]
    progress_percentage: float
    badge_earned: bool = False
    level_up: bool = False


# User badge collection
class UserBadgeCollection(BaseModel):
    user_id: int
    user_full_name: str
    total_badges: int
    achievement_badges: List[BadgeResponse]
    level_badges: List[BadgeResponse]
    recent_badges: List[BadgeResponse]  # Last 5 earned


class BadgeListResponse(BaseModel):
    badges: List[BadgeResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Badge statistics
class BadgeStatistics(BaseModel):
    badge_type: str
    badge_name: str
    total_earned: int
    unique_earners: int
    highest_level: int
    highest_count: int
    average_level: float
    recent_earners: List[UserInfo]


class SystemBadgeStats(BaseModel):
    total_badges_awarded: int
    unique_badge_holders: int
    most_popular_badge: str
    rarest_badge: str
    total_level_badges: int
    total_achievement_badges: int
    badge_stats: List[BadgeStatistics]


# Badge filtering
class BadgeFilters(BaseModel):
    user_id: Optional[int] = None
    badge_type: Optional[BadgeType] = None
    badge_category: Optional[BadgeCategory] = None
    level: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_active: Optional[bool] = True


# Leaderboard integration
class BadgeLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    full_name: str
    badge_count: int
    highest_level_badges: List[str]
    recent_achievement: Optional[str]


class BadgeLeaderboard(BaseModel):
    badge_type: Optional[str] = None  # Specific badge type or overall
    entries: List[BadgeLeaderboardEntry]
    total_participants: int