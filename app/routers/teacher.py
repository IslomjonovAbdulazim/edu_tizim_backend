from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import get_teacher_user
from ..models import User, Group


router = APIRouter()


@router.get("/my-groups")
async def get_my_groups(
    current_user: User = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Get groups assigned to teacher"""
    groups = db.query(Group).filter(
        Group.teacher_id == current_user.id,
        Group.deleted_at.is_(None)
    ).all()
    
    return groups


@router.get("/groups/{group_id}/students")
async def get_group_students(
    group_id: int,
    current_user: User = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Get students in a group with their progress"""
    # Verify teacher owns this group
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.teacher_id == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get students with progress
    # Implementation would include joins with progress tables
    
    return {"message": "Students with progress data"}


