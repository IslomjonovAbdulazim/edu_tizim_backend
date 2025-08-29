# Import all models for easy access and proper relationship setup
from .base import BaseModel
from .user import User
from .learning_center import LearningCenter
from .branch import Branch
from .course import Course
from .module import Module
from .lesson import Lesson
from .word import Word
from .group import Group
from .student import Student
from .parent import Parent
from .teacher import Teacher
from .progress import Progress
from .badge import UserBadge
from .daily_leaderboard import DailyLeaderboard
from .all_time_leaderboard import AllTimeLeaderboard
from .group_leaderboard import GroupLeaderboard
from .verification_code import VerificationCode
from .weaklist import WeakList, WeakListWord
from .payment import Payment

__all__ = [
    "BaseModel",
    "User",
    "LearningCenter",
    "Branch",
    "Course",
    "Module",
    "Lesson",
    "Word",
    "Group",
    "Student",
    "Parent",
    "Teacher",
    "Progress",
    "UserBadge",
    "DailyLeaderboard",
    "AllTimeLeaderboard",
    "GroupLeaderboard",
    "VerificationCode",
    "WeakList",
    "WeakListWord",
    "Payment"
]