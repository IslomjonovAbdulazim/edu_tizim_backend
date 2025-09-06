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


@router.get("/course/{course_id}/progress")
def get_course_progress(
    course_id: int,
    current_user: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get course progress with modules and lessons for student"""
    
    user = current_user["user"]
    
    # Find student's profile for the course's center
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_active == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Find student's profile in this course's learning center
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.center_id == course.center_id,
        LearningCenterProfile.is_active == True
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student not enrolled in this course's learning center"
        )
    
    # Get course modules with lessons
    modules = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index).all()
    
    modules_data = []
    total_lessons = 0
    completed_lessons = 0
    
    for module in modules:
        # Get lessons for this module
        lessons = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_active == True
        ).order_by(Lesson.order_index).all()
        
        lessons_data = []
        module_completed = 0
        
        for lesson in lessons:
            # Get progress for this lesson
            progress = db.query(Progress).filter(
                Progress.profile_id == profile.id,
                Progress.lesson_id == lesson.id
            ).first()
            
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "percentage": progress.percentage if progress else 0,
                "completed": progress.completed if progress else False,
                "last_practiced": progress.last_practiced if progress else None
            }
            
            lessons_data.append(lesson_data)
            
            if progress and progress.completed:
                module_completed += 1
                completed_lessons += 1
            
            total_lessons += 1
        
        module_data = {
            "id": module.id,
            "title": module.title,
            "lessons": lessons_data,
            "completed_lessons": module_completed,
            "total_lessons": len(lessons)
        }
        
        modules_data.append(module_data)
    
    return APIResponse.success({
        "course_id": course.id,
        "course_title": course.title,
        "modules": modules_data,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons
    })


@router.get("/center/{center_id}/leaderboard")
def get_center_leaderboard(
    center_id: int,
    current_user: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get leaderboard for students in a learning center"""
    
    user = current_user["user"]
    
    # Verify student is enrolled in this learning center
    student_profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.is_active == True
    ).first()
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student not enrolled in this learning center"
        )
    
    # Get all student profiles in this learning center
    all_profiles = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    ).all()
    
    leaderboard_data = []
    
    for profile in all_profiles:
        # Calculate total coins for this student
        total_coins = db.query(func.sum(Coin.amount)).filter(
            Coin.profile_id == profile.id
        ).scalar() or 0
        
        # Calculate completed lessons count
        completed_lessons = db.query(Progress).filter(
            Progress.profile_id == profile.id,
            Progress.completed == True
        ).count()
        
        # Calculate total lessons count
        total_lessons = db.query(Progress).filter(
            Progress.profile_id == profile.id
        ).count()
        
        leaderboard_data.append({
            "profile_id": profile.id,
            "student_name": profile.full_name,
            "total_coins": int(total_coins),
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "completion_rate": round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0,
            "is_current_user": profile.id == student_profile.id
        })
    
    # Sort by coins (primary) and completion rate (secondary)
    leaderboard_data.sort(key=lambda x: (x["total_coins"], x["completion_rate"]), reverse=True)
    
    # Add ranking
    for idx, student in enumerate(leaderboard_data):
        student["rank"] = idx + 1
    
    # Find current user's rank
    current_user_rank = next((s["rank"] for s in leaderboard_data if s["is_current_user"]), None)
    current_user_data = next((s for s in leaderboard_data if s["is_current_user"]), None)
    
    return APIResponse.success({
        "center_id": center_id,
        "leaderboard": leaderboard_data,
        "current_user": {
            "rank": current_user_rank,
            "total_coins": current_user_data["total_coins"] if current_user_data else 0,
            "completed_lessons": current_user_data["completed_lessons"] if current_user_data else 0,
            "completion_rate": current_user_data["completion_rate"] if current_user_data else 0
        },
        "total_students": len(leaderboard_data)
    })