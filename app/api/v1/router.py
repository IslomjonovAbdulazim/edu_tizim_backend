from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    students,
    parents,
    groups,
    modules,
    lessons,
    words,
    progress,
    leaderboard,
    badges,
    weeklists
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User Management
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(parents.router, prefix="/parents", tags=["Parents"])

# Group Management
api_router.include_router(groups.router, prefix="/groups", tags=["Groups"])

# Content Management
api_router.include_router(modules.router, prefix="/modules", tags=["Modules"])
api_router.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
api_router.include_router(words.router, prefix="/words", tags=["Words"])

# Progress & Gamification
api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
api_router.include_router(badges.router, prefix="/badges", tags=["Badges"])
api_router.include_router(weeklists.router, prefix="/weeklists", tags=["Weekly Lists"])