# Import all services for easy access
from .base import BaseService

# Core services
from .user import UserService
from .learning_center import LearningCenterService, BranchService
from .content import ContentService
from .learning import LearningService
from .gamification import GamificationService
from .group import GroupService
from .verification import VerificationService

__all__ = [
    # Base
    "BaseService",

    # Services
    "UserService",
    "LearningCenterService",
    "BranchService",
    "ContentService",
    "LearningService",
    "GamificationService",
    "GroupService",
    "VerificationService",

    # Service Factory
    "ServiceFactory"
]


class ServiceFactory:
    """Service factory for dependency injection"""

    def __init__(self, db_session):
        self.db = db_session
        self._user_service = None
        self._learning_center_service = None
        self._branch_service = None
        self._content_service = None
        self._learning_service = None
        self._gamification_service = None
        self._group_service = None
        self._verification_service = None

    @property
    def user(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(self.db)
        return self._user_service

    @property
    def learning_center(self) -> LearningCenterService:
        if self._learning_center_service is None:
            self._learning_center_service = LearningCenterService(self.db)
        return self._learning_center_service

    @property
    def branch(self) -> BranchService:
        if self._branch_service is None:
            self._branch_service = BranchService(self.db)
        return self._branch_service

    @property
    def content(self) -> ContentService:
        if self._content_service is None:
            self._content_service = ContentService(self.db)
        return self._content_service

    @property
    def learning(self) -> LearningService:
        if self._learning_service is None:
            self._learning_service = LearningService(self.db)
        return self._learning_service

    @property
    def gamification(self) -> GamificationService:
        if self._gamification_service is None:
            self._gamification_service = GamificationService(self.db)
        return self._gamification_service

    @property
    def group(self) -> GroupService:
        if self._group_service is None:
            self._group_service = GroupService(self.db)
        return self._group_service

    @property
    def verification(self) -> VerificationService:
        if self._verification_service is None:
            self._verification_service = VerificationService(self.db)
        return self._verification_service


# Dependency injection helper
def get_services(db_session) -> ServiceFactory:
    """Get service factory with database session"""
    return ServiceFactory(db_session)


# Usage examples and patterns
"""
Usage in FastAPI endpoints:

from app.services import ServiceFactory
from app.database import get_db

@app.post("/users/")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    services = ServiceFactory(db)
    return services.user.create_user(user_data)

@app.get("/leaderboard/")
def get_leaderboard(query: LeaderboardQuery, db: Session = Depends(get_db)):
    services = ServiceFactory(db)
    return services.gamification.get_leaderboard(query, current_user.id)

@app.post("/quiz/submit")
def submit_quiz(quiz: QuizSubmission, db: Session = Depends(get_db)):
    services = ServiceFactory(db)

    # Submit quiz and update progress
    result = services.learning.submit_quiz(quiz)

    # Check for new badges
    if result["success"]:
        services.gamification.check_and_award_badges(quiz.user_id)

    return result

Usage in background tasks:

from app.services import ServiceFactory
from app.database import SessionLocal

def daily_leaderboard_update():
    db = SessionLocal()
    try:
        services = ServiceFactory(db)

        # Update leaderboards
        services.gamification.update_leaderboards()

        # Award leaderboard badges
        services.gamification.trigger_leaderboard_badges()

        # Deduct subscription days
        services.learning_center.daily_subscription_deduction()

    finally:
        db.close()

Integration patterns:

# In your main app file
from app.services import ServiceFactory

# FastAPI dependency
async def get_services(db: Session = Depends(get_db)) -> ServiceFactory:
    return ServiceFactory(db)

# Then in endpoints
@app.post("/learning/quiz")
async def submit_quiz(
    quiz_data: QuizSubmission,
    services: ServiceFactory = Depends(get_services)
):
    return services.learning.submit_quiz(quiz_data)
"""