from enum import Enum
from typing import Dict, List


class BadgeCategory(str, Enum):
    DAILY_FIRST = "daily_first"  # Top 1 in 3-daily leaderboard
    PERFECT_LESSON = "perfect_lesson"  # 100% lesson completion
    WEAKLIST_SOLVER = "weaklist_solver"  # WeakList completion
    POSITION_CLIMBER = "position_climber"  # Position improvement in leaderboard


# Level thresholds for each badge category
LEVEL_THRESHOLDS: Dict[str, List[int]] = {
    BadgeCategory.DAILY_FIRST: [1, 3, 5, 10, 20, 30, 40, 50, 70, 100, 125],

    BadgeCategory.PERFECT_LESSON: [1, 3, 5, 10, 20, 30, 40, 50, 70, 100, 125,
                                   150, 175, 200, 250, 300, 350, 400, 450, 500],

    BadgeCategory.WEAKLIST_SOLVER: [1, 3, 5, 10, 20, 30, 40, 50, 70, 100, 125,
                                    150, 175, 200, 250, 300, 350, 400, 450, 500,
                                    600, 700, 800, 900],

    BadgeCategory.POSITION_CLIMBER: [1, 3, 5, 10, 20, 30, 40, 50, 70, 100, 125,
                                     150, 175, 200, 250, 300, 350, 400, 450, 500,
                                     600, 700, 800, 900]
}

# Badge information for each category
BADGE_INFO: Dict[str, Dict] = {
    BadgeCategory.DAILY_FIRST: {
        "name": "Daily Champion",
        "description": "Finished #1 on the 3-daily leaderboard",
        "base_image_url": "/static/badges/daily_champion.png"
    },

    BadgeCategory.PERFECT_LESSON: {
        "name": "Perfect Scholar",
        "description": "Completed lessons with 100% accuracy",
        "base_image_url": "/static/badges/perfect_scholar.png"
    },

    BadgeCategory.WEAKLIST_SOLVER: {
        "name": "Word Master",
        "description": "Conquered weaklist challenges",
        "base_image_url": "/static/badges/word_master.png"
    },

    BadgeCategory.POSITION_CLIMBER: {
        "name": "Rising Star",
        "description": "Climbed higher in leaderboard rankings",
        "base_image_url": "/static/badges/rising_star.png"
    }
}


def get_level_for_count(badge_category: str, count: int) -> int:
    """Get the level for a given count in a badge category"""
    thresholds = LEVEL_THRESHOLDS.get(badge_category, [])
    level = 0
    for threshold in thresholds:
        if count >= threshold:
            level += 1
        else:
            break
    return level


def get_next_level_threshold(badge_category: str, current_count: int) -> int:
    """Get the next threshold for a badge category"""
    thresholds = LEVEL_THRESHOLDS.get(badge_category, [])
    for threshold in thresholds:
        if current_count < threshold:
            return threshold
    return thresholds[-1] if thresholds else 0


def get_badge_info(badge_category: str, level: int) -> Dict:
    """Get complete badge information for a specific level"""
    base_info = BADGE_INFO.get(badge_category, {})
    if not base_info:
        return {}

    return {
        "title": f"{base_info['name']} Level {level}",
        "description": f"{base_info['description']} - Level {level}",
        "image_url": f"{base_info['base_image_url']}?level={level}",  # Can modify URL based on level
        "category": badge_category,
        "level": level
    }


def can_level_up(badge_category: str, current_level: int, current_count: int) -> bool:
    """Check if a badge can be leveled up"""
    thresholds = LEVEL_THRESHOLDS.get(badge_category, [])
    if current_level >= len(thresholds):
        return False
    return current_count >= thresholds[current_level]