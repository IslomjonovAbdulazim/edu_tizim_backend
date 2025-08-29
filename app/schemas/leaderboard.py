from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, date


# Base leaderboard entry
class LeaderboardEntryBase(BaseModel):
    user_id: int
    full_name: str
    avatar_url: Optional[str] = None
    rank: int = Field(ge=1)
    points: int = Field(ge=0)


# Daily leaderboard (with badges)
class DailyLeaderboardEntry(LeaderboardEntryBase):
    """Daily leaderboard entry - resets daily, gives badges"""
    leaderboard_date: date
    points_today: int = Field(ge=0)  # Points earned today only
    previous_rank: Optional[int] = None
    position_change: int = 0
    badge_awarded: bool = False
    badge_type: Optional[str] = None
    is_current_user: bool = False

    @property
    def position_change_text(self):
        if self.position_change > 0:
            return f"↑{self.position_change}"
        elif self.position_change < 0:
            return f"↓{abs(self.position_change)}"
        else:
            return "→"

    @property
    def is_top_3(self):
        return self.rank <= 3

    @property
    def is_first_place(self):
        return self.rank == 1


# All-time leaderboard (no badges)
class AllTimeLeaderboardEntry(LeaderboardEntryBase):
    """All-time leaderboard entry - cumulative points"""
    total_points: int = Field(ge=0)
    points_this_month: int = Field(ge=0)
    last_activity_date: Optional[date] = None
    lessons_completed: int = Field(ge=0)
    days_active: int = Field(ge=0)
    current_streak: int = Field(ge=0)
    average_daily_points: float = Field(ge=0.0)
    is_current_user: bool = False

    @property
    def is_active_this_month(self):
        return self.points_this_month > 0


# Group leaderboard (can be daily or all-time, no badges)
class GroupLeaderboardEntry(LeaderboardEntryBase):
    """Group leaderboard entry"""
    group_id: int
    group_name: str
    leaderboard_type: str  # "daily" or "all_time"
    leaderboard_date: Optional[date] = None  # Only for daily type
    lessons_completed: int = Field(ge=0)
    is_current_user: bool = False

    @validator('leaderboard_type')
    def validate_leaderboard_type(cls, v):
        allowed_types = ["daily", "all_time"]
        if v not in allowed_types:
            raise ValueError(f'Leaderboard type must be one of: {", ".join(allowed_types)}')
        return v

    @property
    def is_daily(self):
        return self.leaderboard_type == "daily"

    @property
    def is_all_time(self):
        return self.leaderboard_type == "all_time"


# Leaderboard responses
class DailyLeaderboardResponse(BaseModel):
    """Daily leaderboard response"""
    date: date
    learning_center_id: int
    learning_center_name: str
    entries: List[DailyLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    current_user_entry: Optional[DailyLeaderboardEntry] = None
    badges_awarded_count: int = 0
    next_reset_time: Optional[datetime] = None


class AllTimeLeaderboardResponse(BaseModel):
    """All-time leaderboard response"""
    learning_center_id: int
    learning_center_name: str
    entries: List[AllTimeLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    current_user_entry: Optional[AllTimeLeaderboardEntry] = None
    last_updated: datetime


class GroupLeaderboardResponse(BaseModel):
    """Group leaderboard response"""
    group_id: int
    group_name: str
    leaderboard_type: str
    date: Optional[date] = None  # For daily group leaderboards
    entries: List[GroupLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    current_user_entry: Optional[GroupLeaderboardEntry] = None
    last_updated: datetime


# Leaderboard filters and options
class LeaderboardFilters(BaseModel):
    learning_center_id: Optional[int] = None
    group_id: Optional[int] = None
    date: Optional[date] = None  # For daily leaderboards
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    limit: int = Field(default=100, ge=1, le=500)
    user_id: Optional[int] = None  # Get specific user's position


# Badge awards for daily leaderboard
class DailyBadgeAward(BaseModel):
    user_id: int
    rank: int
    badge_type: str
    points_today: int
    awarded_at: datetime

    @validator('badge_type')
    def validate_badge_type(cls, v):
        allowed_badges = ["daily_first", "daily_top3", "daily_top10"]
        if v not in allowed_badges:
            raise ValueError(f'Badge type must be one of: {", ".join(allowed_badges)}')
        return v


class DailyBadgeAwardSummary(BaseModel):
    date: date
    learning_center_id: int
    total_badges_awarded: int
    first_place_winner: Optional[str] = None
    top_3_winners: List[str] = []
    awards: List[DailyBadgeAward] = []


# Leaderboard analytics
class LeaderboardAnalytics(BaseModel):
    learning_center_id: int
    period: dict  # start_date, end_date, days
    daily_stats: dict
    all_time_stats: dict
    most_active_groups: List[dict]
    top_performers: List[dict]
    participation_trends: dict


# Cross-leaderboard comparison
class UserLeaderboardStatus(BaseModel):
    """User's status across all leaderboard types"""
    user_id: int
    user_name: str

    # Daily leaderboard
    daily_rank: Optional[int] = None
    points_today: int = 0
    daily_badge_today: bool = False

    # All-time leaderboard
    all_time_rank: Optional[int] = None
    total_points: int = 0

    # Group leaderboards (if user belongs to groups)
    group_daily_ranks: List[dict] = []  # [{group_name, rank, points}]
    group_all_time_ranks: List[dict] = []


# Leaderboard management requests
class UpdateDailyLeaderboardRequest(BaseModel):
    learning_center_id: int
    target_date: date = Field(default_factory=date.today)
    award_badges: bool = True


class UpdateAllTimeLeaderboardRequest(BaseModel):
    learning_center_id: int


class UpdateGroupLeaderboardRequest(BaseModel):
    group_id: int
    leaderboard_type: str = "daily"
    target_date: Optional[date] = Field(default_factory=date.today)

    @validator('leaderboard_type')
    def validate_type(cls, v):
        if v not in ["daily", "all_time"]:
            raise ValueError('Type must be "daily" or "all_time"')
        return v


# Leaderboard history
class LeaderboardHistoryEntry(BaseModel):
    date: date
    rank: int
    points: int
    participants: int
    leaderboard_type: str  # "daily", "all_time", "group_daily", "group_all_time"


class UserLeaderboardHistory(BaseModel):
    user_id: int
    user_name: str
    period_days: int
    history: List[LeaderboardHistoryEntry]
    best_daily_rank: int
    best_all_time_rank: int
    average_daily_rank: float
    rank_trend: str  # "improving", "declining", "stable"