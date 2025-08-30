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

from app.schemas.learning_center import (
    LearningCenterOut, LearningCenterCreate, LearningCenterUpdate,
    BranchOut, BranchCreate,
    PaymentOut, PaymentCreate,
    CenterRoleAssign, CenterRoleOut,
)

router = APIRouter(prefix="/learning-centers", tags=["learning-centers"])

def svc(db: Session = Depends(get_db)) -> LearningCenterService:
    return LearningCenterService(db)


@router.get("/", response_model=List[LearningCenterOut])
def list_centers(service: LearningCenterService = Depends(svc)):
    return service.list_centers()


@router.post("/", response_model=LearningCenterOut, status_code=status.HTTP_201_CREATED)
def create_center(payload: LearningCenterCreate, service: LearningCenterService = Depends(svc)):
    return service.create_center(payload.model_dump())


@router.put("/{center_id}", response_model=LearningCenterOut)
def update_center(center_id: int, payload: LearningCenterUpdate, service: LearningCenterService = Depends(svc)):
    updated = service.update_center(center_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Learning center not found")
    return updated


# branches
@router.post("/{center_id}/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(center_id: int, payload: BranchCreate, service: LearningCenterService = Depends(svc)):
    data = payload.model_dump()
    data["learning_center_id"] = center_id
    return service.create_branch(data)


@router.get("/{center_id}/branches", response_model=List[BranchOut])
def list_branches(center_id: int, service: LearningCenterService = Depends(svc)):
    return service.list_branches(center_id)


# payments
@router.post("/{center_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(center_id: int, payload: PaymentCreate, service: LearningCenterService = Depends(svc)):
    data = payload.model_dump()
    data["learning_center_id"] = center_id
    return service.create_payment(data)


# roles
@router.post("/{center_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
def assign_role(center_id: int, payload: CenterRoleAssign, service: LearningCenterService = Depends(svc)):
    service.assign_role(payload.user_id, center_id, payload.role)
    return None


@router.delete("/{center_id}/roles/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_role(center_id: int, user_id: int, service: LearningCenterService = Depends(svc)):
    service.revoke_role(user_id, center_id)
    return None


@router.get("/{center_id}/roles", response_model=List[CenterRoleOut])
def list_center_roles(center_id: int, service: LearningCenterService = Depends(svc)):
    return service.list_center_roles(center_id)
