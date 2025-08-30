from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import (
    CourseService, ModuleService, LessonService, WordService,
    GroupService, LearningService, LearningCenterService,
    GamificationService, UserService, VerificationService,
)

from app.schemas.gamification import LeaderboardEntryOut, AddPointsIn
from app.models.gamification import LeaderboardType

router = APIRouter(prefix="/gamification", tags=["gamification"])

def svc(db: Session = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


@router.get("/leaderboard", response_model=List[LeaderboardEntryOut])
def leaderboard(
    type: LeaderboardType = Query(LeaderboardType.WEEKLY),
    limit: int = Query(50, ge=1, le=200),
    service: GamificationService = Depends(svc),
):
    return service.get_leaderboard(type, limit=limit)


@router.post("/points", response_model=LeaderboardEntryOut, status_code=status.HTTP_201_CREATED)
def add_points(payload: AddPointsIn, service: GamificationService = Depends(svc)):
    return service.add_points(payload.user_id, payload.points, type_=payload.type)
