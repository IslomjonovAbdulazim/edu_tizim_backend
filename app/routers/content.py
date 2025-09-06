from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import *
from ..services import ContentService, ProgressService
from ..utils import APIResponse, get_current_user_data
from ..dependencies import get_current_user

router = APIRouter()


@router.get("/courses")
def get_courses(
        center_id: int = Query(..., description="Learning center ID"),
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get available courses for a center"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    courses = db.query(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True
    ).all()

    if not courses:
        return APIResponse.success([], "No courses found for this center")

    return APIResponse.success([{
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "created_at": course.created_at
    } for course in courses])


@router.get("/courses/{course_id}")
def get_course_structure(
        course_id: int, 
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get complete course structure with modules and lessons"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_active == True
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get cached content
    content = ContentService.get_course_content(db, course.center_id)

    # Find the specific course
    course_content = next((c for c in content if c["id"] == course_id), None)
    if not course_content:
        raise HTTPException(status_code=404, detail="Course content not found")

    return APIResponse.success(course_content)


@router.get("/lessons/{lesson_id}/words")
def get_lesson_words(
        lesson_id: int, 
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get all words in a lesson"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_active == True
    ).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    words = ContentService.get_lesson_words(db, lesson_id)
    return APIResponse.success(words)


@router.get("/words/{word_id}")
def get_word_details(
        word_id: int, 
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get detailed word information"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    word = db.query(Word).filter(
        Word.id == word_id,
        Word.is_active == True
    ).first()

    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    return APIResponse.success({
        "id": word.id,
        "word": word.word,
        "meaning": word.meaning,
        "definition": word.definition,
        "example_sentence": word.example_sentence,
        "image_url": word.image_url,
        "audio_url": word.audio_url
    })


@router.get("/search")
def search_content(
        q: str = Query(..., min_length=2, description="Search query"),
        center_id: int = Query(..., description="Learning center ID"),
        content_type: str = Query("all", regex="^(courses|lessons|words|all)$"),
        limit: int = Query(20, le=50),
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Search through content"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    results = {}

    if content_type in ["courses", "all"]:
        courses = db.query(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Course.title.ilike(f"%{q}%")
        ).limit(10).all()
        results["courses"] = [{"id": c.id, "title": c.title, "description": c.description} for c in courses]

    if content_type in ["lessons", "all"]:
        lessons = db.query(Lesson).join(Module).join(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Module.is_active == True,
            Lesson.is_active == True,
            Lesson.title.ilike(f"%{q}%")
        ).limit(10).all()
        results["lessons"] = [{"id": l.id, "title": l.title, "module_id": l.module_id} for l in lessons]

    if content_type in ["words", "all"]:
        words = db.query(Word).join(Lesson).join(Module).join(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Module.is_active == True,
            Lesson.is_active == True,
            Word.is_active == True,
            Word.word.ilike(f"%{q}%")
        ).limit(limit).all()
        results["words"] = [{"id": w.id, "word": w.word, "meaning": w.meaning, "lesson_id": w.lesson_id} for w in words]

    return APIResponse.success(results)


@router.get("/random-words")
def get_random_words(
        center_id: int = Query(..., description="Learning center ID"),
        count: int = Query(10, le=50, description="Number of random words"),
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get random words for practice"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    words = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True,
        Module.is_active == True,
        Lesson.is_active == True,
        Word.is_active == True
    ).order_by(func.random()).limit(count).all()

    return APIResponse.success([{
        "id": w.id,
        "word": w.word,
        "meaning": w.meaning,
        "definition": w.definition,
        "example_sentence": w.example_sentence,
        "image_url": w.image_url,
        "audio_url": w.audio_url,
        "lesson_id": w.lesson_id
    } for w in words])


@router.get("/stats/{course_id}")
def get_course_stats(
        course_id: int, 
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get course statistics"""
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    modules_count = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).count()

    lessons_count = db.query(Lesson).join(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True,
        Lesson.is_active == True
    ).count()

    words_count = db.query(Word).join(Lesson).join(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True,
        Lesson.is_active == True,
        Word.is_active == True
    ).count()

    enrolled_students = db.query(GroupMember).join(Group).filter(
        Group.course_id == course_id,
        Group.is_active == True
    ).count()

    return APIResponse.success({
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description
        },
        "stats": {
            "modules": modules_count,
            "lessons": lessons_count,
            "words": words_count,
            "enrolled_students": enrolled_students
        }
    })


# Student Progress Endpoints (Protected)
@router.post("/progress/lesson", dependencies=[Depends(get_current_user)])
def update_lesson_progress(
        progress_data: schemas.ProgressUpdate,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Update student's lesson progress"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can update progress")

    if not current_user["profile"]:
        raise HTTPException(status_code=403, detail="No active profile found")

    coins_earned = ProgressService.update_lesson_progress(
        db,
        current_user["profile"].id,
        progress_data.lesson_id,
        progress_data.percentage
    )

    return APIResponse.success({
        "message": "Progress updated successfully",
        "coins_earned": coins_earned,
        "lesson_completed": progress_data.percentage >= 100
    })


@router.post("/progress/word", dependencies=[Depends(get_current_user)])
def update_word_progress(
        word_attempt: schemas.WordAttempt,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Update student's word-level progress"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can update word progress")

    if not current_user["profile"]:
        raise HTTPException(status_code=403, detail="No active profile found")

    ProgressService.update_word_progress(
        db,
        current_user["profile"].id,
        word_attempt.word_id,
        word_attempt.correct
    )

    return APIResponse.success({"message": "Word progress updated"})


@router.get("/my-progress", dependencies=[Depends(get_current_user)])
def get_my_progress(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get student's learning progress"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can view progress")

    if not current_user["profile"]:
        raise HTTPException(status_code=403, detail="No active profile found")

    progress_records = db.query(Progress).filter(
        Progress.profile_id == current_user["profile"].id
    ).all()

    total_coins = db.query(func.sum(Coin.amount)).filter(
        Coin.profile_id == current_user["profile"].id
    ).scalar() or 0

    # Get weak words
    weak_word_ids = ProgressService.get_weak_words(db, current_user["profile"].id, 10)
    weak_words = []
    if weak_word_ids:
        weak_words = db.query(Word).filter(Word.id.in_(weak_word_ids)).all()

    return APIResponse.success({
        "progress": [{
            "lesson_id": p.lesson_id,
            "percentage": p.percentage,
            "completed": p.completed,
            "last_practiced": p.last_practiced
        } for p in progress_records],
        "summary": {
            "total_lessons": len(progress_records),
            "completed_lessons": len([p for p in progress_records if p.completed]),
            "total_coins": total_coins,
            "weak_words_count": len(weak_words)
        },
        "weak_words": [{
            "id": w.id,
            "word": w.word,
            "meaning": w.meaning
        } for w in weak_words]
    })