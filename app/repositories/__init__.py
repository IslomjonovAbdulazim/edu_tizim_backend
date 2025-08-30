# Import all repository classes
from .base import BaseRepository
from .user import UserRepository, UserCenterRoleRepository, StudentGroupRepository
from .learning_center import LearningCenterRepository, BranchRepository, PaymentRepository
from .content import CourseRepository, ModuleRepository, LessonRepository, WordRepository
from .learning import ProgressRepository, QuizSessionRepository, WeakWordRepository
from .gamification import LeaderboardRepository
from .group import GroupRepository
from .verification import VerificationRepository

# Export all repositories
__all__ = [
    # Base
    "BaseRepository",

    # User system
    "UserRepository",
    "UserCenterRoleRepository",
    "StudentGroupRepository",

    # Learning center & business
    "LearningCenterRepository",
    "BranchRepository",
    "PaymentRepository",

    # Content management
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

    # Group management
    "GroupRepository",

    # Verification system
    "VerificationRepository",

    # Repository Factory
    "RepositoryFactory"
]


class RepositoryFactory:
    """Factory class for managing repository instances with dependency injection"""

    def __init__(self, db_session):
        self.db = db_session

        # Repository instances (lazy loading)
        self._user = None
        self._user_center_role = None
        self._student_group = None
        self._learning_center = None
        self._branch = None
        self._payment = None
        self._course = None
        self._module = None
        self._lesson = None
        self._word = None
        self._progress = None
        self._quiz_session = None
        self._weak_word = None
        self._leaderboard = None
        self._group = None
        self._verification = None

    # User system repositories
    @property
    def user(self) -> UserRepository:
        if self._user is None:
            self._user = UserRepository(self.db)
        return self._user

    @property
    def user_center_role(self) -> UserCenterRoleRepository:
        if self._user_center_role is None:
            self._user_center_role = UserCenterRoleRepository(self.db)
        return self._user_center_role

    @property
    def student_group(self) -> StudentGroupRepository:
        if self._student_group is None:
            self._student_group = StudentGroupRepository(self.db)
        return self._student_group

    # Learning center repositories
    @property
    def learning_center(self) -> LearningCenterRepository:
        if self._learning_center is None:
            self._learning_center = LearningCenterRepository(self.db)
        return self._learning_center

    @property
    def branch(self) -> BranchRepository:
        if self._branch is None:
            self._branch = BranchRepository(self.db)
        return self._branch

    @property
    def payment(self) -> PaymentRepository:
        if self._payment is None:
            self._payment = PaymentRepository(self.db)
        return self._payment

    # Content repositories
    @property
    def course(self) -> CourseRepository:
        if self._course is None:
            self._course = CourseRepository(self.db)
        return self._course

    @property
    def module(self) -> ModuleRepository:
        if self._module is None:
            self._module = ModuleRepository(self.db)
        return self._module

    @property
    def lesson(self) -> LessonRepository:
        if self._lesson is None:
            self._lesson = LessonRepository(self.db)
        return self._lesson

    @property
    def word(self) -> WordRepository:
        if self._word is None:
            self._word = WordRepository(self.db)
        return self._word

    # Learning repositories
    @property
    def progress(self) -> ProgressRepository:
        if self._progress is None:
            self._progress = ProgressRepository(self.db)
        return self._progress

    @property
    def quiz_session(self) -> QuizSessionRepository:
        if self._quiz_session is None:
            self._quiz_session = QuizSessionRepository(self.db)
        return self._quiz_session

    @property
    def weak_word(self) -> WeakWordRepository:
        if self._weak_word is None:
            self._weak_word = WeakWordRepository(self.db)
        return self._weak_word

    # Gamification repositories
    @property
    def leaderboard(self) -> LeaderboardRepository:
        if self._leaderboard is None:
            self._leaderboard = LeaderboardRepository(self.db)
        return self._leaderboard

    # Group repository
    @property
    def group(self) -> GroupRepository:
        if self._group is None:
            self._group = GroupRepository(self.db)
        return self._group

    # Verification repository
    @property
    def verification(self) -> VerificationRepository:
        if self._verification is None:
            self._verification = VerificationRepository(self.db)
        return self._verification

    # Utility methods
    def close_session(self):
        """Close the database session"""
        if self.db:
            self.db.close()

    def commit_transaction(self):
        """Commit current transaction"""
        self._commit()

    def rollback_transaction(self):
        """Rollback current transaction"""
        self.db.rollback()

    def refresh_all_repositories(self):
        """Clear all repository instances to force reload"""
        self._user = None
        self._user_center_role = None
        self._student_group = None
        self._learning_center = None
        self._branch = None
        self._payment = None
        self._course = None
        self._module = None
        self._lesson = None
        self._word = None
        self._progress = None
        self._quiz_session = None
        self._weak_word = None
        self._leaderboard = None
        self._group = None
        self._verification = None


# Convenience function for dependency injection
def get_repositories(db_session) -> RepositoryFactory:
    """Get repository factory instance for dependency injection"""
    return RepositoryFactory(db_session)


# Repository collections for easy access
USER_REPOSITORIES = [
    UserRepository,
    UserCenterRoleRepository,
    StudentGroupRepository
]

LEARNING_CENTER_REPOSITORIES = [
    LearningCenterRepository,
    BranchRepository,
    PaymentRepository
]

CONTENT_REPOSITORIES = [
    CourseRepository,
    ModuleRepository,
    LessonRepository,
    WordRepository
]

LEARNING_REPOSITORIES = [
    ProgressRepository,
    QuizSessionRepository,
    WeakWordRepository
]

GAMIFICATION_REPOSITORIES = [
    LeaderboardRepository
]

GROUP_REPOSITORIES = [
    GroupRepository
]

VERIFICATION_REPOSITORIES = [
    VerificationRepository
]

ALL_REPOSITORIES = (
        USER_REPOSITORIES +
        LEARNING_CENTER_REPOSITORIES +
        CONTENT_REPOSITORIES +
        LEARNING_REPOSITORIES +
        GAMIFICATION_REPOSITORIES +
        GROUP_REPOSITORIES +
        VERIFICATION_REPOSITORIES
)
