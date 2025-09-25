from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import get_student_user
from ..models import User, LessonProgress, Leaderboard


router = APIRouter()


@router.get("/courses")
async def get_available_courses(
    current_user: User = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get courses available to student"""
    # Get courses from student's learning center
    from ..models import Course
    
    courses = db.query(Course).filter(
        Course.learning_center_id == current_user.learning_center_id,
        Course.is_active == True,
        Course.deleted_at.is_(None)
    ).all()
    
    # Convert to dict and cache for 30 minutes
    courses_dict = [
        {
            "id": c.id,
            "title": c.title,
            "learning_center_id": c.learning_center_id,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat()
        }
        for c in courses
    ]
    
    return courses_dict


@router.get("/progress")
async def get_my_progress(
    current_user: User = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get student's learning progress"""
    progress = db.query(LessonProgress).filter(
        LessonProgress.student_id == current_user.id
    ).all()
    
    return {
        "total_coins": current_user.coins,
        "lesson_progress": progress
    }


@router.get("/leaderboard")
async def get_leaderboard(
    current_user: User = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get learning center leaderboard"""
    # Get leaderboard from database
    leaderboard = db.query(Leaderboard).filter(
        Leaderboard.learning_center_id == current_user.learning_center_id
    ).order_by(Leaderboard.rank).limit(10).all()
    
    # Convert to dict
    leaderboard_dict = [
        {
            "id": l.id,
            "student_id": l.student_id,
            "total_coins": l.total_coins,
            "rank": l.rank,
            "updated_at": l.updated_at.isoformat()
        }
        for l in leaderboard
    ]
    
    return leaderboard_dict


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: int,
    score: int,
    current_user: User = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Complete a lesson and award coins"""
    # Update lesson progress
    progress = db.query(LessonProgress).filter(
        LessonProgress.student_id == current_user.id,
        LessonProgress.lesson_id == lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            student_id=current_user.id,
            lesson_id=lesson_id,
            best_score=score,
            lesson_attempts=1
        )
        db.add(progress)
    else:
        progress.lesson_attempts += 1
        if score > progress.best_score:
            # Award coins for improvement
            improvement = score - progress.best_score
            progress.best_score = score
            
            from ..services import user_service
            user_service.award_coins(
                db=db,
                student_id=current_user.id,
                lesson_id=lesson_id,
                score=improvement
            )
    
    db.commit()
    
    return {"message": "Dars yakunlandi", "score": score}
