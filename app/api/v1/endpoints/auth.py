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

from app.schemas.auth import RequestCodeIn, VerifyCodeIn, VerifyCodeOut

router = APIRouter(prefix="/auth", tags=["auth"])

def svc(db: Session = Depends(get_db)) -> VerificationService:
    return VerificationService(db)


@router.post("/request-code", status_code=status.HTTP_204_NO_CONTENT)
def request_code(payload: RequestCodeIn, service: VerificationService = Depends(svc)):
    # NOTE: send via your SMS/Telegram integration outside the service; service only stores code
    service.create_code(user_id=payload.user_id, code=payload.code, ttl_minutes=payload.ttl_minutes, channel=payload.channel)
    return None


@router.post("/verify", response_model=VerifyCodeOut)
def verify_code(payload: VerifyCodeIn, service: VerificationService = Depends(svc)):
    ok = service.verify(payload.user_id, payload.code)
    return VerifyCodeOut(ok=ok)
