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

from app.schemas.learning import (
    ProgressCreate, ProgressOut,
    QuizSessionCreate, QuizSessionUpdate, QuizSessionOut,
    WeakWordCreate, WeakWordOut,
)

router = APIRouter(prefix="/learning", tags=["learning"])

def svc(db: Session = Depends(get_db)) -> LearningService:
    return LearningService(db)


# progress
@router.post("/progress", response_model=ProgressOut, status_code=status.HTTP_201_CREATED)
def record_progress(payload: ProgressCreate, service: LearningService = Depends(svc)):
    return service.record_progress(payload.model_dump())


@router.get("/users/{user_id}/progress", response_model=List[ProgressOut])
def user_progress(user_id: int, limit: int = Query(100, ge=1, le=1000), service: LearningService = Depends(svc)):
    return service.get_user_progress(user_id, limit=limit)


# quizzes
@router.post("/quizzes", response_model=QuizSessionOut, status_code=status.HTTP_201_CREATED)
def start_quiz(payload: QuizSessionCreate, service: LearningService = Depends(svc)):
    return service.start_quiz(payload.model_dump())


@router.put("/quizzes/{quiz_id}", response_model=QuizSessionOut)
def complete_quiz(quiz_id: int, payload: QuizSessionUpdate, service: LearningService = Depends(svc)):
    updated = service.complete_quiz(quiz_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return updated


@router.get("/users/{user_id}/quizzes", response_model=List[QuizSessionOut])
def user_quizzes(user_id: int, limit: int = Query(50, ge=1, le=1000), service: LearningService = Depends(svc)):
    return service.get_user_quizzes(user_id, limit=limit)


# weak words
@router.post("/weak-words", response_model=WeakWordOut, status_code=status.HTTP_201_CREATED)
def mark_weak_word(payload: WeakWordCreate, service: LearningService = Depends(svc)):
    return service.mark_weak_word(payload.model_dump())


@router.get("/users/{user_id}/weak-words", response_model=List[WeakWordOut])
def user_weak_words(user_id: int, limit: int = Query(100, ge=1, le=1000), service: LearningService = Depends(svc)):
    return service.get_user_weak_words(user_id, limit=limit)
