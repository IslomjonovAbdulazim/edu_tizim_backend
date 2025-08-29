from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# Badge types
class BadgeType:
    LESSON_MASTER = "lesson_master"
    STREAK_HOLDER = "streak_holder"
    TOP_PERFORMER = "top_performer"
    CONSISTENT_LEARNER = "consistent_learner"
    WORD_COLLECTOR = "word_collector"
    PERFECT_SCORE = "perfect_score"
    FAST_LEARNER = "fast_learner"
    WEEKLY_CHAMPION = "weekly_champion"


# Base badge schemas
class BadgeBase(BaseModel):
    user_id: int = Field(..., gt=0)
    badge_type: str
    level: int = Field(default=1, ge=1)
    count: int = Field(default=1, ge=1)
    context: Optional[str] = None

    @validator('badge_type')
    def validate_badge_type(cls, v):
        valid_types = [
            BadgeType.LESSON_MASTER, BadgeType.STREAK_HOLDER, BadgeType.TOP_PERFORMER,
            BadgeType.CONSISTENT_LEARNER, BadgeType.WORD_COLLECTOR, BadgeType.PERFECT_SCORE,
            BadgeType.FAST_LEARNER, BadgeType.WEEKLY_CHAMPION
        ]
        if v not in valid_types:
            raise ValueError(f'Badge type must be one of: {", ".join(valid_types)}')
        return v


class BadgeCreate(BadgeBase):
    pass


class BadgeResponse(BaseModel):
    id: int
    user_id: int
    badge_type: str
    badge_name: str
    badge_icon: str
    level: int
    count: int
    context: Optional[str]
    earned_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


# Badge with user info
class BadgeWithUser(BadgeResponse):
    user_name: str
    user_role: str


# Achievement notification
class AchievementNotification(BaseModel):
    badge: BadgeResponse
    is_new_level: bool = False
    is_first_time: bool = False
    message: str
    points_awarded: int = 0


# User badge summary
class UserBadgeSummary(BaseModel):
    user_id: int
    user_name: str
    total_badges: int
    recent_badges: List[BadgeResponse] = []
    badge_levels: dict = {}  # badge_type -> level
    achievements_this_week: int = 0
    badge_score: int = 0  # Calculated score based on badges


# Badge leaderboard
class BadgeLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    user_name: str
    total_badges: int
    highest_level: int
    badge_score: int
    recent_achievement: Optional[str] = None


class BadgeLeaderboard(BaseModel):
    entries: List[BadgeLeaderboardEntry]
    period: str = "all_time"  # all_time, monthly, weekly
    total_participants: int


# Badge statistics
class BadgeStatistics(BaseModel):
    badge_type: str
    badge_name: str
    total_holders: int
    highest_level: int
    average_level: float
    recent_awards_30d: int
    rarity_score: float  # 0-1, lower = rarer


# Badge progress tracking
class BadgeProgress(BaseModel):
    badge_type: str
    badge_name: str
    current_level: int
    current_count: int
    next_threshold: Optional[int] = None
    progress_percentage: float = 0.0
    estimated_next_level: Optional[str] = None


# Badge award request
class AwardBadgeRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    badge_type: str
    context: Optional[str] = None
    auto_level: bool = True  # Automatically determine level based on count


# Badge system settings
class BadgeSystemSettings(BaseModel):
    lesson_master_thresholds: List[int] = [5, 15, 30, 50, 100]
    streak_thresholds: List[int] = [3, 7, 14, 30, 60]
    top_performer_thresholds: List[int] = [1, 3, 7, 15, 30]
    word_collector_thresholds: List[int] = [50, 200, 500, 1000, 2000]


# Badge filters
class BadgeFilters(BaseModel):
    user_id: Optional[int] = None
    badge_type: Optional[str] = None
    level: Optional[int] = None
    is_active: Optional[bool] = None
    earned_from: Optional[datetime] = None
    earned_to: Optional[datetime] = None