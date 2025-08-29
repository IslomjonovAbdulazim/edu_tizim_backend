from sqlalchemy import Column, Integer, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BadgeType(BaseModel):
    """Badge type definition model - defines available badges in the system"""
    __tablename__ = "badge_types"

    # Basic info
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # Badge categorization
    category = Column(String(50), nullable=False)  # achievement, daily, streak, level, etc.
    icon = Column(String(200), nullable=False)  # Icon URL or icon name

    # Badge behavior
    is_progressive = Column(Boolean, default=False)  # Can have multiple levels?
    max_level = Column(Integer, default=1)  # Max level if progressive
    is_repeatable = Column(Boolean, default=False)  # Can be earned multiple times?

    # Requirements and thresholds
    requirements = Column(JSON, nullable=False)  # JSON with earning criteria
    # Example: {"points_required": 1000, "days_consecutive": 7, "lessons_completed": 50}

    # Visual properties
    color_primary = Column(String(7), default="#FFD700")  # Hex color
    color_secondary = Column(String(7), default="#FFA500")  # Hex color
    rarity = Column(String(20), default="common")  # common, uncommon, rare, epic, legendary

    # Status
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)  # For display ordering

    # Relationships
    user_badges = relationship("UserBadge", back_populates="badge_type")

    def __str__(self):
        return f"BadgeType({self.name}, {self.category})"

    @property
    def is_daily(self):
        """Check if this is a daily badge type"""
        return self.category.lower() == "daily"

    @property
    def is_streak(self):
        """Check if this is a streak badge type"""
        return self.category.lower() == "streak"

    @property
    def is_achievement(self):
        """Check if this is an achievement badge type"""
        return self.category.lower() == "achievement"

    def get_requirement(self, key: str):
        """Get specific requirement value"""
        if not self.requirements:
            return None
        return self.requirements.get(key)

    def check_requirements_met(self, user_stats: dict) -> dict:
        """Check if user meets requirements for this badge"""
        if not self.requirements:
            return {"met": False, "missing": []}

        met = True
        missing = []
        progress = {}

        for req_key, req_value in self.requirements.items():
            user_value = user_stats.get(req_key, 0)
            progress[req_key] = {
                "required": req_value,
                "current": user_value,
                "percentage": min(100, (user_value / req_value) * 100) if req_value > 0 else 0
            }

            if user_value < req_value:
                met = False
                missing.append(req_key)

        return {
            "met": met,
            "missing": missing,
            "progress": progress
        }

    def get_next_level_requirements(self, current_level: int) -> dict:
        """Get requirements for next level if progressive"""
        if not self.is_progressive or current_level >= self.max_level:
            return {}

        # Scale requirements by level (can be customized per badge type)
        next_level_reqs = {}
        multiplier = current_level + 1

        for key, base_value in self.requirements.items():
            if isinstance(base_value, (int, float)):
                next_level_reqs[key] = base_value * multiplier
            else:
                next_level_reqs[key] = base_value

        return next_level_reqs

    @classmethod
    def create_daily_badge_types(cls):
        """Factory method to create standard daily badge types"""
        return [
            {
                "name": "Daily First Place",
                "description": "Finish in 1st place on the daily leaderboard",
                "category": "daily",
                "icon": "trophy-gold",
                "requirements": {"daily_rank": 1},
                "color_primary": "#FFD700",
                "rarity": "rare"
            },
            {
                "name": "Daily Top 3",
                "description": "Finish in top 3 on the daily leaderboard",
                "category": "daily",
                "icon": "medal-bronze",
                "requirements": {"daily_rank": 3},
                "color_primary": "#CD7F32",
                "rarity": "uncommon"
            },
            {
                "name": "Daily Top 10",
                "description": "Finish in top 10 on the daily leaderboard",
                "category": "daily",
                "icon": "star",
                "requirements": {"daily_rank": 10},
                "color_primary": "#C0C0C0",
                "rarity": "common"
            }
        ]

    @classmethod
    def create_achievement_badge_types(cls):
        """Factory method to create standard achievement badge types"""
        return [
            {
                "name": "Point Collector",
                "description": "Earn points milestone",
                "category": "achievement",
                "icon": "coins",
                "is_progressive": True,
                "max_level": 10,
                "requirements": {"total_points": 1000},  # 1k, 2k, 3k, etc.
                "color_primary": "#4CAF50",
                "rarity": "common"
            },
            {
                "name": "Lesson Master",
                "description": "Complete lessons milestone",
                "category": "achievement",
                "icon": "book-open",
                "is_progressive": True,
                "max_level": 20,
                "requirements": {"lessons_completed": 10},  # 10, 20, 30, etc.
                "color_primary": "#2196F3",
                "rarity": "common"
            },
            {
                "name": "Streak Warrior",
                "description": "Maintain learning streak",
                "category": "streak",
                "icon": "flame",
                "is_progressive": True,
                "max_level": 12,
                "requirements": {"streak_days": 7},  # 7, 14, 21, etc.
                "color_primary": "#FF5722",
                "rarity": "uncommon"
            }
        ]

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'is_daily': self.is_daily,
            'is_streak': self.is_streak,
            'is_achievement': self.is_achievement
        })
        return data