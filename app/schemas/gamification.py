from pydantic import BaseModel, Field, ConfigDict, field_validator
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


from typing import Optional, List, Generic, TypeVar
from datetime import date, datetime
from enum import Enum
from .base import BaseSchema, TimestampMixin


class LeaderboardType(str, Enum):
    GLOBAL_3_DAILY = "global_3_daily"
    GLOBAL_ALL_TIME = "global_all_time"
    GROUP_3_DAILY = "group_3_daily"
    GROUP_ALL_TIME = "group_all_time"


# Leaderboard Schemas
class LeaderboardEntryBase(BaseSchema):
    user_id: int = Field(..., gt=0, description="User ID")
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard")
    rank: int = Field(..., gt=0, description="User's rank position")
    points: int = Field(..., ge=0, description="Points earned")
    user_full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")



class LeaderboardEntryOut(LeaderboardEntryBase):
    id: int = Field(..., gt=0, description="ID")
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

class LeaderboardEntryCreate(LeaderboardEntryBase):
    group_id: Optional[int] = Field(None, gt=0, description="Group ID (for group leaderboards)")
    leaderboard_date: Optional[date] = Field(None, description="Date for daily leaderboards")
    previous_rank: Optional[int] = Field(None, gt=0, description="Previous rank for comparison")

    @field_validator('group_id')
    def validate_group_id(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GROUP_3_DAILY, LeaderboardType.GROUP_ALL_TIME]:
            if not v:
                raise ValueError('Group ID is required for group leaderboards')
        return v

    @field_validator('leaderboard_date')
    def validate_leaderboard_date(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]:
            if not v:
                v = date.today()  # Default to today for daily leaderboards
        elif leaderboard_type in [LeaderboardType.GLOBAL_ALL_TIME, LeaderboardType.GROUP_ALL_TIME]:
            v = None  # All-time leaderboards don't have dates
        return v


class LeaderboardEntryUpdate(BaseSchema):
    rank: Optional[int] = Field(None, gt=0)
    points: Optional[int] = Field(None, ge=0)
    user_full_name: Optional[str] = Field(None, min_length=1, max_length=100)


class LeaderboardEntryResponse(LeaderboardEntryBase, TimestampMixin):
    group_id: Optional[int] = Field(None, gt=0)
    leaderboard_date: Optional[date] = None
    previous_rank: Optional[int] = Field(None, gt=0)

    # Computed fields
    position_change: int = Field(0, description="Position change from previous rank")
    is_top_3: bool = Field(False, description="Whether user is in top 3")
    is_improved: bool = Field(False, description="Whether position improved")
    rank_badge: str = Field("", description="Rank display with emoji")

    @field_validator('position_change', mode='before', validate_default=True)
    def calculate_position_change(cls, v, values):
        current = values.get('rank')
        previous = values.get('previous_rank')
        if current and previous:
            return previous - current  # Positive = improvement (lower rank number)
        return 0

    @field_validator('is_top_3', mode='before', validate_default=True)
    def set_is_top_3(cls, v, values):
        return values.get('rank', 0) <= 3

    @field_validator('is_improved', mode='before', validate_default=True)
    def set_is_improved(cls, v, values):
        return values.get('position_change', 0) > 0

    @field_validator('rank_badge', mode='before', validate_default=True)
    def set_rank_badge(cls, v, values):
        rank = values.get('rank', 0)
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        elif rank <= 10:
            return "🏆"
        else:
            return "📊"


# Leaderboard Query and Response
class LeaderboardQuery(BaseSchema):
    """Query parameters for leaderboard"""
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard to fetch")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID (required for group leaderboards)")
    leaderboard_date: Optional[date] = Field(None, description="Date for daily leaderboards")
    limit: int = Field(50, ge=1, le=100, description="Maximum entries to return")
    user_id: Optional[int] = Field(None, gt=0, description="Specific user to highlight")

    @field_validator('group_id')
    def validate_group_id(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GROUP_3_DAILY, LeaderboardType.GROUP_ALL_TIME]:
            if not v:
                raise ValueError('Group ID is required for group leaderboards')
        return v


class LeaderboardResponse(BaseSchema):
    """Complete leaderboard response"""
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID if applicable")
    leaderboard_date: Optional[date] = Field(None, description="Date if applicable")
    entries: List[LeaderboardEntryResponse] = Field(..., description="Leaderboard entries")
    user_rank: Optional[int] = Field(None, description="Current user's rank")
    total_participants: int = Field(0, ge=0, description="Total number of participants")
    last_updated: Optional[date] = Field(None, description="When leaderboard was last updated")

    @field_validator('total_participants', mode='before', validate_default=True)
    def set_total_participants(cls, v, values):
        entries = values.get('entries', [])
        return len(entries)


# Game Statistics (simplified without badges)
class GameStats(BaseSchema):
    """Comprehensive gamification statistics"""
    user_id: int = Field(..., gt=0)

    # Leaderboard stats
    global_rank: Optional[int] = Field(None, gt=0, description="Global all-time rank")
    group_rank: Optional[int] = Field(None, gt=0, description="Group all-time rank")
    best_daily_rank: Optional[int] = Field(None, gt=0, description="Best daily rank achieved")

    # Performance stats
    total_points: int = Field(0, ge=0, description="Total points earned")
    position_improvements: int = Field(0, ge=0, description="Number of position improvements")
    perfect_lessons: int = Field(0, ge=0, description="Perfect lessons completed")
    daily_first_finishes: int = Field(0, ge=0, description="Daily first place finishes")
    weaklist_completions: int = Field(0, ge=0, description="Weak word lists completed")

    # Engagement
    days_active: int = Field(0, ge=0, description="Total days with activity")
    current_streak: int = Field(0, ge=0, description="Current daily streak")
    longest_streak: int = Field(0, ge=0, description="Longest daily streak achieved")


# Admin and Management
class LeaderboardUpdateRequest(BaseSchema):
    """Request to update leaderboard (admin)"""
    leaderboard_type: LeaderboardType = Field(..., description="Leaderboard to update")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID if applicable")
    force_update: bool = Field(False, description="Force update even if recent")


# Leaderboard Analytics
class LeaderboardAnalytics(BaseSchema):
    """Leaderboard engagement analytics"""
    leaderboard_type: LeaderboardType = Field(..., description="Leaderboard type")
    date_range: str = Field(..., description="Analytics date range")

    # Participation metrics
    total_participants: int = Field(0, ge=0, description="Total participants")
    active_participants: int = Field(0, ge=0, description="Active participants (last 7 days)")
    participation_rate: float = Field(0.0, ge=0.0, le=100.0, description="Participation rate %")

    # Competition metrics
    average_points: float = Field(0.0, ge=0.0, description="Average points across participants")
    top_10_points_threshold: int = Field(0, ge=0, description="Minimum points for top 10")
    position_changes: int = Field(0, ge=0, description="Total position changes")

    # Engagement patterns
    most_active_day: Optional[str] = Field(None, description="Day with most activity")
    peak_competition_hours: List[int] = Field(default_factory=list, description="Hours with most activity")


class UserLeaderboardSummary(BaseSchema):
    """User's leaderboard summary across all boards"""
    user_id: int = Field(..., gt=0)
    user_full_name: str = Field(..., min_length=1)

    # Current positions
    global_all_time_rank: Optional[int] = Field(None, gt=0)
    global_daily_rank: Optional[int] = Field(None, gt=0)
    group_all_time_rank: Optional[int] = Field(None, gt=0)
    group_daily_rank: Optional[int] = Field(None, gt=0)

    # Performance metrics
    total_points: int = Field(0, ge=0)
    best_rank_achieved: Optional[int] = Field(None, gt=0)
    days_in_top_10: int = Field(0, ge=0)
    days_in_top_3: int = Field(0, ge=0)
    times_ranked_first: int = Field(0, ge=0)

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
