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

from app.schemas.user import (
    UserOut, UserCreate, UserUpdate,
    UserRoleOut,
)

router = APIRouter(prefix="/users", tags=["users"])

def svc(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/", response_model=List[UserOut])
def search_users(
    q: str = Query(..., description="Search by full name or phone"),
    center_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: UserService = Depends(svc),
):
    return service.search(center_id, q, limit=limit)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, service: UserService = Depends(svc)):
    return service.create(payload.model_dump())


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, service: UserService = Depends(svc)):
    u = service.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, service: UserService = Depends(svc)):
    u = service.update(user_id, payload.model_dump(exclude_unset=True))
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, service: UserService = Depends(svc)):
    ok = service.delete(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.get("/{user_id}/roles", response_model=List[UserRoleOut])
def user_roles(user_id: int, service: UserService = Depends(svc)):
    return service.list_roles(user_id)
