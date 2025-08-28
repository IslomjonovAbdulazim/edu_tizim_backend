from typing import Optional, List
from pydantic import BaseModel, validator, Field
from datetime import datetime, date


# Basic leaderboard entry
class LeaderboardEntryBase(BaseModel):
    user_id: int
    full_name: str
    avatar_url: Optional[str] = None
    points: int = Field(ge=0)
    rank: int = Field(ge=1)
    position_change: int = 0  # +/- change from previous period


class CurrentLeaderboardEntry(LeaderboardEntryBase):
    """Real-time leaderboard entry"""
    is_current_user: bool = False
    total_lessons_completed: int = 0
    current_streak: int = 0
    last_activity: Optional[datetime] = None


# Leaderboard responses
class CurrentLeaderboardResponse(BaseModel):
    """Real-time leaderboard"""
    timestamp: datetime
    entries: List[CurrentLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None
    current_user_points: Optional[int] = None
    update_frequency: str = "real-time"


# Weekly and monthly aggregated leaderboards
class WeeklyLeaderboardEntry(LeaderboardEntryBase):
    week_start_date: date
    week_end_date: date
    points_this_week: int = Field(ge=0)
    lessons_completed_this_week: int = Field(ge=0)
    average_daily_points: float = Field(ge=0.0)


class MonthlyLeaderboardEntry(LeaderboardEntryBase):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2024)
    points_this_month: int = Field(ge=0)
    lessons_completed_this_month: int = Field(ge=0)
    days_active: int = Field(ge=0, le=31)
    consistency_score: float = Field(ge=0.0, le=100.0)  # Based on daily activity


class WeeklyLeaderboardResponse(BaseModel):
    week_start_date: date
    week_end_date: date
    entries: List[WeeklyLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None


class MonthlyLeaderboardResponse(BaseModel):
    month: int
    year: int
    entries: List[MonthlyLeaderboardEntry]
    total_participants: int
    current_user_rank: Optional[int] = None


# Leaderboard filters and options
class LeaderboardFilters(BaseModel):
    date: Optional[date] = None  # Specific date for daily leaderboard
    date_from: Optional[date] = None  # Date range start
    date_to: Optional[date] = None  # Date range end
    limit: int = Field(default=100, ge=1, le=500)  # Number of entries to return
    user_id: Optional[int] = None  # Get specific user's position


class LeaderboardType(str):
    CURRENT = "current"  # Real-time leaderboard
    DAILY = "daily"  # Daily snapshot
    WEEKLY = "weekly"  # Weekly aggregate
    MONTHLY = "monthly"  # Monthly aggregate


# Leaderboard analytics
class LeaderboardAnalytics(BaseModel):
    learning_center_id: int
    date_range: dict  # start_date and end_date
    total_unique_participants: int
    average_daily_participants: int
    most_active_day: date
    least_active_day: date
    participation_trend: str  # "increasing", "decreasing", "stable"
    top_performers: List[dict]
    engagement_metrics: dict


# Competition and challenges
class LeaderboardChallenge(BaseModel):
    challenge_id: str
    title: str
    description: str
    start_date: date
    end_date: date
    prize_description: Optional[str] = None
    participants: List[int]  # User IDs
    current_leader: Optional[int] = None  # User ID
    is_active: bool = True


class ChallengeLeaderboard(BaseModel):
    challenge: LeaderboardChallenge
    entries: List[CurrentLeaderboardEntry]
    time_remaining: Optional[str] = None  # Human readable time until end
    is_user_participating: bool = False