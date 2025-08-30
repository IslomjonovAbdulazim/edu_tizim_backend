from pydantic import BaseModel, Field, validator
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
    user_id: int = Field(..., gt=0, description="User ID")
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard")
    rank: int = Field(..., gt=0, description="User's rank position")
    points: int = Field(..., ge=0, description="Points earned")
    user_full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")


class LeaderboardEntryCreate(LeaderboardEntryBase):
    group_id: Optional[int] = Field(None, gt=0, description="Group ID (for group leaderboards)")
    leaderboard_date: Optional[date] = Field(None, description="Date for daily leaderboards")
    previous_rank: Optional[int] = Field(None, gt=0, description="Previous rank for comparison")

    @validator('group_id')
    def validate_group_id(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GROUP_3_DAILY, LeaderboardType.GROUP_ALL_TIME]:
            if not v:
                raise ValueError('Group ID is required for group leaderboards')
        return v

    @validator('leaderboard_date')
    def validate_leaderboard_date(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GLOBAL_3_DAILY, LeaderboardType.GROUP_3_DAILY]:
            if not v:
                v = date.today()  # Default to today for daily leaderboards
        elif leaderboard_type in [LeaderboardType.GLOBAL_ALL_TIME, LeaderboardType.GROUP_ALL_TIME]:
            v = None  # All-time leaderboards don't have dates
        return v


class LeaderboardEntryUpdate(BaseModel):
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

    @validator('position_change', pre=True, always=True)
    def calculate_position_change(cls, v, values):
        current = values.get('rank')
        previous = values.get('previous_rank')
        if current and previous:
            return previous - current  # Positive = improvement (lower rank number)
        return 0

    @validator('is_top_3', pre=True, always=True)
    def set_is_top_3(cls, v, values):
        return values.get('rank', 0) <= 3

    @validator('is_improved', pre=True, always=True)
    def set_is_improved(cls, v, values):
        return values.get('position_change', 0) > 0

    @validator('rank_badge', pre=True, always=True)
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


# Badge Schemas
class UserBadgeBase(BaseSchema):
    user_id: int = Field(..., gt=0, description="User ID")
    category: BadgeCategory = Field(..., description="Badge category")
    title: str = Field(..., min_length=1, max_length=100, description="Badge title")
    description: str = Field(..., min_length=1, max_length=200, description="Badge description")
    level: int = Field(1, gt=0, le=1000, description="Badge level")


class UserBadgeCreate(UserBadgeBase):
    earned_at: date = Field(default_factory=date.today, description="Date badge was earned")


class UserBadgeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    level: Optional[int] = Field(None, gt=0, le=1000)
    is_seen: Optional[bool] = None
    is_active: Optional[bool] = None


class UserBadgeResponse(UserBadgeBase, TimestampMixin):
    earned_at: date = Field(..., description="Date badge was earned")
    is_seen: bool = Field(False, description="Whether user has seen this badge")

    # Computed fields
    is_new: bool = Field(False, description="Whether badge was earned recently")
    category_emoji: str = Field("🎖", description="Category emoji")
    level_display: str = Field("", description="Level display string")

    @validator('is_new', pre=True, always=True)
    def set_is_new(cls, v, values):
        earned_date = values.get('earned_at')
        if earned_date:
            days_since = (date.today() - earned_date).days
            return days_since <= 3  # New if earned within 3 days
        return False

    @validator('category_emoji', pre=True, always=True)
    def set_category_emoji(cls, v, values):
        category = values.get('category')
        emoji_map = {
            BadgeCategory.DAILY_FIRST: "🥇",
            BadgeCategory.PERFECT_LESSON: "💯",
            BadgeCategory.WEAKLIST_SOLVER: "📚",
            BadgeCategory.POSITION_CLIMBER: "📈"
        }
        return emoji_map.get(category, "🎖")

    @validator('level_display', pre=True, always=True)
    def set_level_display(cls, v, values):
        level = values.get('level', 1)
        if level >= 100:
            return f"Level {level} 🌟"
        elif level >= 50:
            return f"Level {level} ⭐"
        else:
            return f"Level {level}"


# Leaderboard Query and Response
class LeaderboardQuery(BaseModel):
    """Query parameters for leaderboard"""
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard to fetch")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID (required for group leaderboards)")
    leaderboard_date: Optional[date] = Field(None, description="Date for daily leaderboards")
    limit: int = Field(50, ge=1, le=100, description="Maximum entries to return")
    user_id: Optional[int] = Field(None, gt=0, description="Specific user to highlight")

    @validator('group_id')
    def validate_group_id(cls, v, values):
        leaderboard_type = values.get('leaderboard_type')
        if leaderboard_type in [LeaderboardType.GROUP_3_DAILY, LeaderboardType.GROUP_ALL_TIME]:
            if not v:
                raise ValueError('Group ID is required for group leaderboards')
        return v


class LeaderboardResponse(BaseModel):
    """Complete leaderboard response"""
    leaderboard_type: LeaderboardType = Field(..., description="Type of leaderboard")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID if applicable")
    leaderboard_date: Optional[date] = Field(None, description="Date if applicable")
    entries: List[LeaderboardEntryResponse] = Field(..., description="Leaderboard entries")
    user_rank: Optional[int] = Field(None, description="Current user's rank")
    total_participants: int = Field(0, ge=0, description="Total number of participants")
    last_updated: Optional[date] = Field(None, description="When leaderboard was last updated")

    @validator('total_participants', pre=True, always=True)
    def set_total_participants(cls, v, values):
        entries = values.get('entries', [])
        return len(entries)


# Badge Progress and Management
class BadgeProgress(BaseModel):
    """Progress toward next badge level"""
    category: BadgeCategory = Field(..., description="Badge category")
    current_level: int = Field(0, ge=0, description="Current badge level (0 if no badge)")
    current_count: int = Field(0, ge=0, description="Current achievement count")
    next_threshold: int = Field(0, gt=0, description="Next level threshold")
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Progress to next level")
    can_level_up: bool = Field(False, description="Whether can level up now")

    # Display fields
    category_name: str = Field("", description="Human-readable category name")
    description: str = Field("", description="What this badge tracks")

    @validator('progress_percentage', pre=True, always=True)
    def calculate_progress_percentage(cls, v, values):
        current = values.get('current_count', 0)
        threshold = values.get('next_threshold', 1)
        return min(100.0, round((current / threshold * 100), 1))

    @validator('can_level_up', pre=True, always=True)
    def set_can_level_up(cls, v, values):
        current = values.get('current_count', 0)
        threshold = values.get('next_threshold', 1)
        return current >= threshold

    @validator('category_name', pre=True, always=True)
    def set_category_name(cls, v, values):
        category = values.get('category')
        name_map = {
            BadgeCategory.DAILY_FIRST: "Daily Champion",
            BadgeCategory.PERFECT_LESSON: "Perfect Scholar",
            BadgeCategory.WEAKLIST_SOLVER: "Word Master",
            BadgeCategory.POSITION_CLIMBER: "Rising Star"
        }
        return name_map.get(category, category.value if category else "")


class UserBadgesSummary(BaseModel):
    """Complete badge summary for user"""
    user_id: int = Field(..., gt=0)
    total_badges: int = Field(0, ge=0, description="Total badges earned")
    unseen_badges: int = Field(0, ge=0, description="Unseen badges count")
    badges: List[UserBadgeResponse] = Field(default_factory=list, description="All badges")
    badge_progress: List[BadgeProgress] = Field(default_factory=list, description="Progress toward next levels")
    recent_badges: List[UserBadgeResponse] = Field(default_factory=list, description="Recently earned badges")

    @validator('recent_badges', pre=True, always=True)
    def set_recent_badges(cls, v, values):
        badges = values.get('badges', [])
        return [badge for badge in badges if badge.is_new]


# Badge Notification Schemas
class MarkBadgeAsSeenRequest(BaseModel):
    """Mark single badge as seen"""
    badge_id: int = Field(..., gt=0, description="Badge ID to mark as seen")


class MarkBadgesAsSeenRequest(BaseModel):
    """Mark multiple badges as seen"""
    badge_ids: List[int] = Field(..., min_items=1, description="Badge IDs to mark as seen")

    @validator('badge_ids')
    def validate_unique_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate badge IDs found')
        return v


class MarkAllBadgesAsSeenRequest(BaseModel):
    """Mark all unseen badges as seen for user"""
    user_id: int = Field(..., gt=0, description="User ID")


class BadgeNotificationResponse(BaseModel):
    """Badge notification response"""
    unseen_badges_count: int = Field(..., ge=0, description="Number of unseen badges")
    has_new_badges: bool = Field(..., description="Whether user has new badges")
    unseen_badges: List[UserBadgeResponse] = Field(..., description="Unseen badges")


class BadgeNotificationSummary(BaseModel):
    """Quick badge notification summary"""
    user_id: int = Field(..., gt=0)
    total_badges: int = Field(0, ge=0)
    unseen_badges: int = Field(0, ge=0)
    new_achievements: int = Field(0, ge=0, description="New achievements in last 24h")
    recent_level_ups: int = Field(0, ge=0, description="Recent level ups")


# Gamification Analytics
class GameStats(BaseModel):
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

    # Badge stats
    total_badges: int = Field(0, ge=0, description="Total badges earned")
    badge_levels_sum: int = Field(0, ge=0, description="Sum of all badge levels")
    highest_badge_level: int = Field(0, ge=0, description="Highest individual badge level")

    # Engagement
    days_active: int = Field(0, ge=0, description="Total days with activity")
    current_streak: int = Field(0, ge=0, description="Current daily streak")
    longest_streak: int = Field(0, ge=0, description="Longest daily streak achieved")


# Admin and Management
class LeaderboardUpdateRequest(BaseModel):
    """Request to update leaderboard (admin)"""
    leaderboard_type: LeaderboardType = Field(..., description="Leaderboard to update")
    group_id: Optional[int] = Field(None, gt=0, description="Group ID if applicable")
    force_update: bool = Field(False, description="Force update even if recent")


class BadgeAwardRequest(BaseModel):
    """Request to manually award badge (admin)"""
    user_id: int = Field(..., gt=0, description="User ID")
    category: BadgeCategory = Field(..., description="Badge category")
    level: int = Field(1, gt=0, description="Badge level")
    reason: Optional[str] = Field(None, max_length=200, description="Reason for manual award")