# Import all repositories for easy access
from .base import BaseRepository

# User management
from .user import UserRepository

# Learning center & business
from .learning_center import (
    LearningCenterRepository,
    BranchRepository,
    PaymentRepository
)

# Content management
from .content import (
    CourseRepository,
    ModuleRepository,
    LessonRepository,
    WordRepository
)

# Learning & progress
from .learning import (
    ProgressRepository,
    QuizSessionRepository,
    WeakWordRepository
)

# Gamification
from .gamification import (
    LeaderboardRepository,
    BadgeRepository
)

# Group management
from .group import GroupRepository

# Verification
from .verification import VerificationRepository

__all__ = [
    # Base
    "BaseRepository",

    # User
    "UserRepository",

    # Learning center & business
    "LearningCenterRepository",
    "BranchRepository",
    "PaymentRepository",

    # Content
    "CourseRepository",
    "ModuleRepository",
    "LessonRepository",
    "WordRepository",

    # Learning & progress
    "ProgressRepository",
    "QuizSessionRepository",
    "WeakWordRepository",

    # Gamification
    "LeaderboardRepository",
    "BadgeRepository",

    # Group
    "GroupRepository",

    # Verification
    "VerificationRepository"
]


# Repository factory class for dependency injection
class RepositoryFactory:
    """Factory class to create repository instances with database session"""

    def __init__(self, db_session):
        self.db = db_session

    @property
    def user(self) -> UserRepository:
        return UserRepository(self.db)

    @property
    def learning_center(self) -> LearningCenterRepository:
        return LearningCenterRepository(self.db)

    @property
    def branch(self) -> BranchRepository:
        return BranchRepository(self.db)

    @property
    def payment(self) -> PaymentRepository:
        return PaymentRepository(self.db)

    @property
    def course(self) -> CourseRepository:
        return CourseRepository(self.db)

    @property
    def module(self) -> ModuleRepository:
        return ModuleRepository(self.db)

    @property
    def lesson(self) -> LessonRepository:
        return LessonRepository(self.db)

    @property
    def word(self) -> WordRepository:
        return WordRepository(self.db)

    @property
    def progress(self) -> ProgressRepository:
        return ProgressRepository(self.db)

    @property
    def quiz_session(self) -> QuizSessionRepository:
        return QuizSessionRepository(self.db)

    @property
    def weak_word(self) -> WeakWordRepository:
        return WeakWordRepository(self.db)

    @property
    def leaderboard(self) -> LeaderboardRepository:
        return LeaderboardRepository(self.db)

    @property
    def badge(self) -> BadgeRepository:
        return BadgeRepository(self.db)

    @property
    def group(self) -> GroupRepository:
        return GroupRepository(self.db)

    @property
    def verification(self) -> VerificationRepository:
        return VerificationRepository(self.db)

# Usage example:
# from app.repositories import RepositoryFactory
#
# def some_service(db: Session):
#     repos = RepositoryFactory(db)
#     user = repos.user.get(1)
#     progress = repos.progress.get_user_progress(user.id)