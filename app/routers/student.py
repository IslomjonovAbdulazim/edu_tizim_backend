from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import *
from ..utils import APIResponse, require_role, verify_token
from .. import schemas

security = HTTPBearer()

def get_student_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get student user without center validation"""
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(
        User.id == payload["user_id"], 
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    return {"user": user}

router = APIRouter()


@router.get("/info")
def get_student_info(current_user: dict = Depends(get_student_user), db: Session = Depends(get_db)):
    """Get student's complete information including all profiles, centers, and groups"""
    
    user = current_user["user"]
    
    # Get all learning center profiles for this student
    all_profiles = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.is_active == True
    ).all()
    
    learning_centers = []
    all_groups = []
    total_progress_stats = {
        "total_lessons": 0,
        "completed_lessons": 0,
        "total_coins": 0,
        "centers_count": len(all_profiles)
    }
    
    for profile in all_profiles:
        # Get learning center info
        center = db.query(LearningCenter).filter(
            LearningCenter.id == profile.center_id,
            LearningCenter.is_active == True
        ).first()
        
        if center:
            # Get groups for this profile/center
            center_groups = []
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
                    
                    group_info = {
                        "id": group.id,
                        "name": group.name,
                        "center_id": center.id,
                        "teacher": {
                            "id": teacher_profile.id,
                            "full_name": teacher_profile.full_name
                        } if teacher_profile else None,
                        "course": {
                            "id": course.id,
                            "title": course.title,
                            "description": course.description
                        } if course else None
                    }
                    center_groups.append(group_info)
                    all_groups.append(group_info)
            
            # Get progress stats for this center
            center_progress = db.query(Progress).filter(
                Progress.profile_id == profile.id
            ).all()
            
            center_lessons = len(center_progress)
            center_completed = len([p for p in center_progress if p.completed])
            center_coins = sum([coin.amount for coin in profile.coins]) if profile.coins else 0
            
            total_progress_stats["total_lessons"] += center_lessons
            total_progress_stats["completed_lessons"] += center_completed
            total_progress_stats["total_coins"] += center_coins
            
            learning_centers.append({
                "profile": {
                    "id": profile.id,
                    "full_name": profile.full_name,
                    "role_in_center": profile.role_in_center.value,
                    "is_active": profile.is_active,
                    "created_at": profile.created_at
                },
                "center": {
                    "id": center.id,
                    "title": center.title,
                    "logo": center.logo,
                    "days_remaining": center.days_remaining,
                    "student_limit": center.student_limit,
                    "is_active": center.is_active
                },
                "groups": center_groups,
                "progress": {
                    "total_lessons": center_lessons,
                    "completed_lessons": center_completed,
                    "completion_rate": round((center_completed / center_lessons * 100), 1) if center_lessons > 0 else 0,
                    "coins": center_coins
                }
            })
    
    return APIResponse.success({
        "student": {
            "id": user.id,
            "phone": user.phone,
            "telegram_id": user.telegram_id,
            "avatar": user.avatar,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "learning_centers": learning_centers,
        "summary": {
            "total_centers": len(learning_centers),
            "total_groups": len(all_groups),
            "overall_progress": {
                "total_lessons": total_progress_stats["total_lessons"],
                "completed_lessons": total_progress_stats["completed_lessons"],
                "completion_rate": round((total_progress_stats["completed_lessons"] / total_progress_stats["total_lessons"] * 100), 1) if total_progress_stats["total_lessons"] > 0 else 0,
                "total_coins": total_progress_stats["total_coins"]
            }
        }
    })