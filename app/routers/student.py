from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import *
from ..utils import APIResponse, require_role
from .. import schemas

router = APIRouter()


@router.get("/info")
def get_student_info(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get student's complete information including profile, center, and groups"""
    
    # Ensure only students can access this endpoint
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    user = current_user["user"]
    profile = current_user["profile"]
    center = current_user["center"]
    
    # Get student's groups
    groups = []
    if profile:
        group_members = db.query(GroupMember).filter(
            GroupMember.profile_id == profile.id
        ).all()
        
        for member in group_members:
            group = db.query(Group).filter(
                Group.id == member.group_id,
                Group.is_active == True
            ).first()
            
            if group:
                # Get teacher info
                teacher_profile = None
                if group.teacher_id:
                    teacher_profile = db.query(LearningCenterProfile).filter(
                        LearningCenterProfile.id == group.teacher_id,
                        LearningCenterProfile.is_active == True
                    ).first()
                
                # Get course info
                course = None
                if group.course_id:
                    course = db.query(Course).filter(
                        Course.id == group.course_id,
                        Course.is_active == True
                    ).first()
                
                groups.append({
                    "id": group.id,
                    "name": group.name,
                    "teacher": {
                        "id": teacher_profile.id,
                        "full_name": teacher_profile.full_name
                    } if teacher_profile else None,
                    "course": {
                        "id": course.id,
                        "title": course.title,
                        "description": course.description
                    } if course else None
                })
    
    # Get current progress stats
    progress_stats = None
    if profile:
        total_progress = db.query(Progress).filter(
            Progress.profile_id == profile.id
        ).all()
        
        total_lessons = len(total_progress)
        completed_lessons = len([p for p in total_progress if p.completed])
        total_coins = profile.coins if hasattr(profile, 'coins') else 0
        
        progress_stats = {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "completion_rate": round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0,
            "total_coins": total_coins
        }
    
    return APIResponse.success({
        "student": {
            "id": user.id,
            "phone": user.phone,
            "telegram_id": user.telegram_id,
            "avatar": user.avatar,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "profile": {
            "id": profile.id,
            "full_name": profile.full_name,
            "role_in_center": profile.role_in_center.value,
            "is_active": profile.is_active,
            "created_at": profile.created_at
        } if profile else None,
        "learning_center": {
            "id": center.id,
            "title": center.title,
            "logo": center.logo,
            "days_remaining": center.days_remaining,
            "student_limit": center.student_limit,
            "is_active": center.is_active
        } if center else None,
        "groups": groups,
        "progress_stats": progress_stats
    })