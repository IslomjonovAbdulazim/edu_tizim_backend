from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, date


# Basic daily leaderboard entry
class DailyLeaderboardEntryBase(BaseModel):
    user_id: int
    rank: int = Field(ge=1)
    points: int = Field(ge=0)
    position_change: int = 0  # +/- change from previous day
    user_full_name: str
    user_avatar_url: Optional[str] = None


class DailyLeaderboardEntry(DailyLeaderboardEntryBase):
    """Daily leaderboard entry with additional info"""
    leaderboard_date: date
    previous_rank: Optional[int] = None
    points_gained_today: int = Field(default=0, ge=0)

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


class DailyLeaderboardCreate(BaseModel):
    """Data for creating daily leaderboard snapshot"""
    learning_center_id: int
    leaderboard_date: date
    entries: List[dict] = Field(..., min_items=1)


class DailyLeaderboardInDB(BaseModel):
    id: int
    learning_center_id: int
    leaderboard_date: date
    user_id: int
    rank: int
    points: int
    previous_rank: Optional[int]
    position_change: int
    user_full_name: str
    user_avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyLeaderboardResponse(BaseModel):
    """Daily leaderboard response"""
    date: date
    entries: List[DailyLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    current_user_entry: Optional[DailyLeaderboardEntry] = None
    snapshot_time: datetime
    next_reset_time: Optional[datetime] = None


class UserDailyEntry(BaseModel):
    """User's specific daily entry"""
    user_id: int
    date: date
    rank: int
    points: int
    points_gained_today: int
    position_change: int
    position_change_text: str
    is_top_3: bool
    total_participants: int


# Leaderboard history and statistics
class UserLeaderboardHistory(BaseModel):
    user_id: int
    user_full_name: str
    entries: List[DailyLeaderboardEntry]
    best_rank: int
    worst_rank: int
    average_rank: float
    total_days_participated: int
    days_in_top_10: int
    days_in_top_3: int
    days_in_first_place: int
    current_streak_top_10: int
    longest_streak_top_10: int


class LeaderboardStats(BaseModel):
    """Daily leaderboard statistics"""
    date: date
    learning_center_id: int
    total_participants: int
    average_points: float
    median_points: float
    top_scorer_points: int
    points_distribution: dict  # Point ranges and counts
    new_participants: int
    returning_participants: int


# Top performers and climbers
class TopPerformer(BaseModel):
    user_id: int
    user_full_name: str
    top_appearances: int  # How many times in top N
    avg_rank: float
    best_rank: int
    total_points: int
    consistency_score: float  # Percentage of days in top N


class BiggestClimber(BaseModel):
    user_id: int
    user_full_name: str
    date: date
    previous_rank: int
    current_rank: int
    position_change: int
    points_gained: int


# Participation tracking
class ParticipationStats(BaseModel):
    """Participation statistics for learning center"""
    learning_center_id: int
    period: dict  # start_date, end_date, days
    total_unique_participants: int
    average_daily_participants: float
    most_active_day: date
    least_active_day: date
    participation_trend: str  # "increasing", "decreasing", "stable"
    daily_breakdown: List[dict]


# Streak tracking
class StreakLeader(BaseModel):
    user_id: int
    user_full_name: str
    current_streak: int
    max_streak: int
    streak_type: str  # "top_3", "top_10", "participation"


class StreakLeaderboard(BaseModel):
    streak_type: str
    min_streak: int
    leaders: List[StreakLeader]


# Leaderboard creation and management
class CreateDailySnapshotRequest(BaseModel):
    learning_center_id: int
    target_date: date = Field(default_factory=lambda: datetime.now().date())


class LeaderboardDataEntry(BaseModel):
    """Entry for creating leaderboard snapshot"""
    user_id: int
    full_name: str
    points: int
    rank: int
    avatar_url: Optional[str] = None


# Filters and queries
class LeaderboardFilters(BaseModel):
    learning_center_id: int
    date: Optional[date] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    user_id: Optional[int] = None
    top_n: Optional[int] = Field(None, ge=1, le=100)


class LeaderboardQuery(BaseModel):
    learning_center_id: int
    target_date: date
    limit: int = Field(default=100, ge=1, le=500)
    include_user_rank: Optional[int] = None  # Include specific user even if not in top N


# Comparison and analytics
class LeaderboardComparison(BaseModel):
    """Compare performance across different periods"""
    user_id: int
    user_full_name: str
    date1: date
    date2: date
    rank1: Optional[int]
    rank2: Optional[int]
    points1: Optional[int]
    points2: Optional[int]
    rank_change: Optional[int]
    points_change: Optional[int]


class LeaderboardTrend(BaseModel):
    """User's leaderboard trend over time"""
    user_id: int
    dates: List[date]
    ranks: List[int]
    points: List[int]
    trend_direction: str  # "improving", "declining", "stable"
    trend_score: float  # -1 to 1, negative = declining, positive = improving


class CenterLeaderboardComparison(BaseModel):
    """Compare leaderboards across learning centers"""
    date: date
    centers: dict  # center_id -> List[TopPerformer]
    comparison_metrics: dict