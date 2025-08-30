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

from app.schemas.group import GroupOut, GroupCreate, GroupUpdate, StudentGroupOut

router = APIRouter(prefix="/groups", tags=["groups"])

def svc(db: Session = Depends(get_db)) -> GroupService:
    return GroupService(db)


@router.get("/", response_model=List[GroupOut])
def list_groups(learning_center_id: int = Query(...), service: GroupService = Depends(svc)):
    return service.list_by_center(learning_center_id)


@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, service: GroupService = Depends(svc)):
    return service.create(payload.model_dump())


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, service: GroupService = Depends(svc)):
    g = service.get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return g


@router.put("/{group_id}", response_model=GroupOut)
def update_group(group_id: int, payload: GroupUpdate, service: GroupService = Depends(svc)):
    g = service.update(group_id, payload.model_dump(exclude_unset=True))
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return g


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, service: GroupService = Depends(svc)):
    ok = service.delete(group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Group not found")
    return None


@router.post("/{group_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_groups(group_id: int, learning_center_id: int = Body(...), order: List[int] = Body(...), service: GroupService = Depends(svc)):
    service.reorder(learning_center_id, order)
    return None


@router.post("/{group_id}/students", status_code=status.HTTP_204_NO_CONTENT)
def add_student(group_id: int, user_id: int = Body(..., embed=True), service: GroupService = Depends(svc)):
    service.add_student(user_id, group_id)
    return None


@router.delete("/{group_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(group_id: int, user_id: int, service: GroupService = Depends(svc)):
    service.remove_student(user_id, group_id)
    return None


@router.get("/{group_id}/students", response_model=List[StudentGroupOut])
def list_students(group_id: int, service: GroupService = Depends(svc)):
    return service.list_members(group_id)
