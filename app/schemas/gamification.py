from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from enum import Enum
from .base import BaseSchema, TimestampMixin


class LeaderboardType(str, Enum):
    GLOBAL_3_DAILY = "global_3_daily"
    GLOBAL_ALL_TIME = "global_all_time"
    GROUP_3_DAILY = "group_3_daily"
    GROUP_ALL_TIME = "group_all_time"


class BadgeCategory(str, Enum):
    DAILY_FIRST = "daily_first"
    PERFECT_LESSON = "perfect_lesson"
    WEAKLIST_SOLVER = "weaklist_solver"
    POSITION_CLIMBER = "position_climber"


# Leaderboard Schemas
class LeaderboardEntryBase(BaseSchema):
    user_id: int
    leaderboard_type: LeaderboardType
    rank: int
    points: int


class LeaderboardEntryCreate(LeaderboardEntryBase):
    group_id: Optional[int] = None
    leaderboard_date: Optional[date] = None
    user_full_name: str
    previous_rank: Optional[int] = None
    position_change: int = 0


class LeaderboardEntryResponse(LeaderboardEntryBase, TimestampMixin):
    group_id: Optional[int]
    leaderboard_date: Optional[date]
    user_full_name: str
    previous_rank: Optional[int]
    position_change: int
    is_3_daily: bool = False
    is_top_3: bool = False
    position_improved: bool = False


# Badge Schemas
class UserBadgeBase(BaseSchema):
    user_id: int
    category: BadgeCategory
    level: int = 1


class UserBadgeCreate(UserBadgeBase):
    title: str
    description: str
    image_url: str


class UserBadgeUpdate(BaseModel):
    level: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class UserBadgeResponse(UserBadgeBase, TimestampMixin):
    title: str
    description: str
    image_url: str
    is_active: bool
    earned_at: date


# Leaderboard Views
class LeaderboardQuery(BaseModel):
    leaderboard_type: LeaderboardType
    group_id: Optional[int] = None
    leaderboard_date: Optional[date] = None
    limit: int = 50


class LeaderboardResponse(BaseModel):
    leaderboard_type: LeaderboardType
    group_id: Optional[int]
    leaderboard_date: Optional[date]
    entries: List[LeaderboardEntryResponse]
    user_rank: Optional[int] = None  # Current user's rank in this leaderboard


# Badge Progress
class BadgeProgress(BaseModel):
    category: BadgeCategory
    current_level: int
    current_count: int
    next_threshold: int
    progress_percentage: float
    can_level_up: bool


class UserBadgesSummary(BaseModel):
    user_id: int
    badges: List[UserBadgeResponse]
    badge_progress: List[BadgeProgress]
    total_badges: int


# Gamification Analytics
class GameStats(BaseModel):
    user_id: int
    total_points: int
    current_rank_global: Optional[int]
    current_rank_group: Optional[int]
    badges_earned: int
    position_improvements: int
    perfect_lessons: int
    daily_first_finishes: int
    weaklist_completions: int