# Import all simplified models
from .base import BaseModel
from .user import User, UserRole, UserCenterRole, StudentGroup
from .learning_center import LearningCenter, Branch, Payment
from .content import Course, Module, Lesson, Word
from .group import Group
from .learning import Progress, QuizSession, WeakWord
from .gamification import LeaderboardEntry, LeaderboardType, UserBadge, BadgeCategory
from .verification import VerificationCode

__all__ = [
    # Base
    "BaseModel",

    # User system - simplified multi-tenant roles
    "User",
    "UserRole",
    "UserCenterRole",
    "StudentGroup",

    # Learning center & business
    "LearningCenter",
    "Branch",
    "Payment",

    # Content structure - clean hierarchy
    "Course",
    "Module",
    "Lesson",
    "Word",

    # Group management
    "Group",

    # Learning & progress - simplified tracking
    "Progress",
    "QuizSession",
    "WeakWord",

    # Gamification - streamlined engagement
    "LeaderboardEntry",
    "LeaderboardType",
    "UserBadge",
    "BadgeCategory",

    # Verification - secure and simple
    "VerificationCode"
]
