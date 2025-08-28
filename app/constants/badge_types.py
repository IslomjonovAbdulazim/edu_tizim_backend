from enum import Enum
from typing import Dict, List


class BadgeCategory(str, Enum):
    ACHIEVEMENT = "achievement"  # One-time achievements
    LEVEL = "level"  # Level badges (only one per subcategory)


class BadgeType(str, Enum):
    # Achievement badges (can have multiple)
    DAILY_FIRST = "daily_first"  # Finished #1 in daily leaderboard
    PERFECT_LESSON = "perfect_lesson"  # 100% lesson completion
    BATTLE_WINNER = "battle_winner"  # 3 straight battle winner

    # Level badges (only one per type)
    LESSON_MASTER = "lesson_master"  # Lesson completion levels
    WEEKLIST_SOLVER = "weeklist_solver"  # Weekly list completion levels
    TOP_PERFORMER = "top_performer"  # Daily top 3 finishes
    POSITION_CLIMBER = "position_climber"  # Daily position increase


# Level thresholds for level badges
LEVEL_THRESHOLDS: Dict[str, List[int]] = {
    BadgeType.LESSON_MASTER: [1, 10, 50, 100, 200, 300, 500, 700, 1000, 10000, 100000],
    BadgeType.WEEKLIST_SOLVER: [1, 10, 50, 100, 200, 300, 500, 700, 1000, 10000, 100000],
    BadgeType.TOP_PERFORMER: [1, 10, 50, 100, 200, 300, 500, 700, 1000, 10000, 100000],
    BadgeType.POSITION_CLIMBER: [1, 10, 50, 100, 200, 300, 500, 700, 1000, 10000, 100000]
}

# Badge descriptions and requirements
BADGE_INFO: Dict[str, Dict] = {
    # Achievement badges
    BadgeType.DAILY_FIRST: {
        "name": "Daily Champion",
        "description": "Finished #1 on the daily leaderboard",
        "category": BadgeCategory.ACHIEVEMENT,
        "icon": "🏆",
        "multiple": True
    },
    BadgeType.PERFECT_LESSON: {
        "name": "Perfect Score",
        "description": "Completed a lesson with 100% accuracy",
        "category": BadgeCategory.ACHIEVEMENT,
        "icon": "💯",
        "multiple": True
    },
    BadgeType.BATTLE_WINNER: {
        "name": "Battle Master",
        "description": "Won 3 battles in a row",
        "category": BadgeCategory.ACHIEVEMENT,
        "icon": "⚔️",
        "multiple": True
    },

    # Level badges
    BadgeType.LESSON_MASTER: {
        "name": "Lesson Master",
        "description": "Master of lesson completion",
        "category": BadgeCategory.LEVEL,
        "icon": "📚",
        "multiple": False
    },
    BadgeType.WEEKLIST_SOLVER: {
        "name": "Weekly Champion",
        "description": "Master of weekly word lists",
        "category": BadgeCategory.LEVEL,
        "icon": "📝",
        "multiple": False
    },
    BadgeType.TOP_PERFORMER: {
        "name": "Top Performer",
        "description": "Consistent top 3 finisher",
        "category": BadgeCategory.LEVEL,
        "icon": "🌟",
        "multiple": False
    },
    BadgeType.POSITION_CLIMBER: {
        "name": "Rising Star",
        "description": "Master of daily position improvements",
        "category": BadgeCategory.LEVEL,
        "icon": "📈",
        "multiple": False
    }
}


def get_level_for_count(badge_type: str, count: int) -> int:
    """Get the level for a given count in a badge type"""
    thresholds = LEVEL_THRESHOLDS.get(badge_type, [])
    level = 0
    for threshold in thresholds:
        if count >= threshold:
            level += 1
        else:
            break
    return level


def get_next_level_threshold(badge_type: str, current_count: int) -> int:
    """Get the next threshold for a badge type"""
    thresholds = LEVEL_THRESHOLDS.get(badge_type, [])
    for threshold in thresholds:
        if current_count < threshold:
            return threshold
    return thresholds[-1] if thresholds else 0


def is_level_badge(badge_type: str) -> bool:
    """Check if a badge type is a level badge"""
    return BADGE_INFO.get(badge_type, {}).get("category") == BadgeCategory.LEVEL


def can_have_multiple(badge_type: str) -> bool:
    """Check if a badge type can have multiple instances"""
    return BADGE_INFO.get(badge_type, {}).get("multiple", False)