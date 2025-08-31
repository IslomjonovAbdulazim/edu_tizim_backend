from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..services import ContentService
from ..utils import APIResponse


router = APIRouter()


@router.get("/courses")
def get_public_courses(
        center_id: int = None,
        db: Session = Depends(get_db)
):
    """Get available courses (public endpoint)"""
    if not center_id:
        raise HTTPException(status_code=400, detail="center_id required")

    courses = db.query(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True
    ).all()

    return APIResponse.success(courses)


@router.get("/courses/{course_id}")
def get_course_structure(course_id: int, db: Session = Depends(get_db)):
    """Get course structure with modules and lessons"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_active == True
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get full content structure using cached service
    content = ContentService.get_course_content(db, course.center_id)

    # Filter for requested course
    course_content = next((c for c in content if c["id"] == course_id), None)

    if not course_content:
        raise HTTPException(status_code=404, detail="Course content not found")

    return APIResponse.success(course_content)


@router.get("/courses/{course_id}/modules")
def get_course_modules(course_id: int, db: Session = Depends(get_db)):
    """Get modules in a course"""
    modules = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index).all()

    return APIResponse.success(modules)


@router.get("/modules/{module_id}/lessons")
def get_module_lessons(module_id: int, db: Session = Depends(get_db)):
    """Get lessons in a module"""
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.order_index).all()

    return APIResponse.success(lessons)


@router.get("/lessons/{lesson_id}/words")
def get_lesson_words(lesson_id: int, db: Session = Depends(get_db)):
    """Get words in a lesson"""
    words = db.query(Word).filter(
        Word.lesson_id == lesson_id,
        Word.is_active == True
    ).order_by(Word.order_index).all()

    return APIResponse.success(words)


@router.get("/words/{word_id}")
def get_word_details(word_id: int, db: Session = Depends(get_db)):
    """Get detailed word information"""
    word = db.query(Word).filter(
        Word.id == word_id,
        Word.is_active == True
    ).first()

    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    return APIResponse.success(word)


@router.get("/search")
def search_content(
        q: str,
        center_id: int,
        content_type: str = "all",  # "courses", "lessons", "words", "all"
        db: Session = Depends(get_db)
):
    """Search through content"""
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query too short")

    results = {}

    if content_type in ["courses", "all"]:
        courses = db.query(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Course.title.ilike(f"%{q}%")
        ).limit(10).all()
        results["courses"] = courses

    if content_type in ["lessons", "all"]:
        lessons = db.query(Lesson).join(Module).join(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Module.is_active == True,
            Lesson.is_active == True,
            Lesson.title.ilike(f"%{q}%")
        ).limit(10).all()
        results["lessons"] = lessons

    if content_type in ["words", "all"]:
        words = db.query(Word).join(Lesson).join(Module).join(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True,
            Module.is_active == True,
            Lesson.is_active == True,
            Word.is_active == True,
            Word.word.ilike(f"%{q}%")
        ).limit(20).all()
        results["words"] = words

    return APIResponse.success(results)


@router.get("/stats/{course_id}")
def get_course_stats(course_id: int, db: Session = Depends(get_db)):
    """Get course statistics"""
    # Count modules, lessons, words
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

    # Get enrolled students count
    enrolled_students = db.query(GroupMember).join(Group).filter(
        Group.course_id == course_id,
        Group.is_active == True
    ).count()

    return APIResponse.success({
        "modules": modules_count,
        "lessons": lessons_count,
        "words": words_count,
        "enrolled_students": enrolled_students
    })


@router.get("/random-words")
def get_random_words(
        center_id: int,
        count: int = 10,
        db: Session = Depends(get_db)
):
    """Get random words for practice"""
    if count > 50:
        count = 50

    words = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True,
        Module.is_active == True,
        Lesson.is_active == True,
        Word.is_active == True
    ).order_by(func.random()).limit(count).all()

    return APIResponse.success(words)