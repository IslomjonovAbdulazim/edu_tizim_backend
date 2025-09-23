from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel, field_serializer
from datetime import datetime

from ..database import get_db
from ..dependencies import get_admin_user, get_teacher_user, get_student_user, get_current_user
from ..models import User, Course, Lesson, Word, WordDifficulty


router = APIRouter()


# Response models (Read-only)
class CourseResponse(BaseModel):
    id: int
    title: str
    learning_center_id: int
    is_active: bool
    lesson_count: int
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return v.isoformat() + 'Z' if v else None
    
    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    title: str
    content: Optional[str]
    order: int
    course_id: int
    word_count: int
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return v.isoformat() + 'Z' if v else None
    
    class Config:
        from_attributes = True


class WordResponse(BaseModel):
    id: int
    word: str
    translation: str
    definition: Optional[str]
    sentence: Optional[str]
    difficulty: WordDifficulty
    audio: Optional[str]
    image: Optional[str]
    lesson_id: int
    order: int
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return v.isoformat() + 'Z' if v else None
    
    class Config:
        from_attributes = True


# Read-only content access for Admin, Teacher, Student


@router.get("/courses", response_model=List[CourseResponse])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all courses in learning center (accessible by Admin, Teacher, Student)"""
    from sqlalchemy import func
    
    # Get courses with lesson count
    courses = db.query(
        Course.id,
        Course.title,
        Course.learning_center_id,
        Course.is_active,
        Course.created_at,
        func.count(Lesson.id).label('lesson_count')
    ).outerjoin(Lesson, (Lesson.course_id == Course.id) & (Lesson.deleted_at.is_(None))).filter(
        Course.learning_center_id == current_user.learning_center_id,
        Course.is_active == True,
        Course.deleted_at.is_(None)
    ).group_by(Course.id).all()
    
    # Convert to dict format
    return [
        {
            "id": course.id,
            "title": course.title,
            "learning_center_id": course.learning_center_id,
            "is_active": course.is_active,
            "lesson_count": course.lesson_count,
            "created_at": course.created_at
        }
        for course in courses
    ]


@router.get("/courses/{course_id}/lessons", response_model=List[LessonResponse])
async def list_lessons(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List lessons in a course (accessible by Admin, Teacher, Student)"""
    from sqlalchemy import func
    
    # Verify course belongs to user's learning center
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get lessons with word count
    lessons = db.query(
        Lesson.id,
        Lesson.title,
        Lesson.content,
        Lesson.order,
        Lesson.course_id,
        Lesson.created_at,
        func.count(Word.id).label('word_count')
    ).outerjoin(Word, (Word.lesson_id == Lesson.id) & (Word.deleted_at.is_(None))).filter(
        Lesson.course_id == course_id,
        Lesson.deleted_at.is_(None)
    ).group_by(Lesson.id).order_by(Lesson.order).all()
    
    # Convert to dict format
    return [
        {
            "id": lesson.id,
            "title": lesson.title,
            "content": lesson.content,
            "order": lesson.order,
            "course_id": lesson.course_id,
            "word_count": lesson.word_count,
            "created_at": lesson.created_at
        }
        for lesson in lessons
    ]


@router.get("/lessons/{lesson_id}/words", response_model=List[WordResponse])
async def list_words(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List words in a lesson (accessible by Admin, Teacher, Student)"""
    # Verify lesson belongs to user's learning center
    lesson = db.query(Lesson).join(Course).filter(
        Lesson.id == lesson_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    words = db.query(Word).filter(
        Word.lesson_id == lesson_id,
        Word.deleted_at.is_(None)
    ).order_by(Word.order).all()
    
    return words
