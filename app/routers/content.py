from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import get_admin_user, get_super_admin_user, get_student_user
from ..models import User, Course, Lesson, Word, WordDifficulty
from ..services import storage_service, cache_service


router = APIRouter()


class CreateCourseRequest(BaseModel):
    title: str


class CreateLessonRequest(BaseModel):
    title: str
    content: Optional[str] = None
    order: int


class CreateWordRequest(BaseModel):
    word: str
    translation: str
    definition: Optional[str] = None
    sentence: Optional[str] = None
    difficulty: WordDifficulty
    order: int


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None


class UpdateLessonRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None


class UpdateWordRequest(BaseModel):
    word: Optional[str] = None
    translation: Optional[str] = None
    definition: Optional[str] = None
    sentence: Optional[str] = None
    difficulty: Optional[WordDifficulty] = None
    order: Optional[int] = None


# Response models
class CourseResponse(BaseModel):
    id: int
    title: str
    learning_center_id: int
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    title: str
    content: Optional[str]
    order: int
    course_id: int
    created_at: str
    
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
    created_at: str
    
    class Config:
        from_attributes = True


# Admin/Super Admin routes

@router.post("/courses", response_model=CourseResponse)
async def create_course(
    request: CreateCourseRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new course"""
    learning_center_id = current_user.learning_center_id
    
    course = Course(
        title=request.title,
        learning_center_id=learning_center_id
    )
    
    db.add(course)
    db.commit()
    db.refresh(course)
    
    # Invalidate course cache
    await cache_service.delete_pattern(f"student_courses:{learning_center_id}")
    
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    request: UpdateCourseRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if request.title:
        course.title = request.title
    
    db.commit()
    db.refresh(course)
    
    return course


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete course (soft delete)"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.is_active = False
    db.commit()
    
    return {"message": "Course deleted successfully"}


@router.post("/courses/{course_id}/lessons")
async def create_lesson(
    course_id: int,
    request: CreateLessonRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new lesson"""
    # Verify course belongs to user's learning center
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    lesson = Lesson(
        title=request.title,
        content=request.content,
        order=request.order,
        course_id=course_id
    )
    
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.post("/lessons/{lesson_id}/words")
async def create_word(
    lesson_id: int,
    request: CreateWordRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new word"""
    # Verify lesson belongs to user's learning center
    lesson = db.query(Lesson).join(Course).filter(
        Lesson.id == lesson_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    word = Word(
        word=request.word,
        translation=request.translation,
        definition=request.definition,
        sentence=request.sentence,
        difficulty=request.difficulty,
        order=request.order,
        lesson_id=lesson_id
    )
    
    db.add(word)
    db.commit()
    db.refresh(word)
    
    return word


@router.post("/words/{word_id}/audio")
async def upload_word_audio(
    word_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Upload audio for a word"""
    # Verify word belongs to user's learning center
    word = db.query(Word).join(Lesson).join(Course).filter(
        Word.id == word_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Save audio file
    audio_path = await storage_service.save_audio(file, word_id)
    
    # Update word with audio path
    word.audio = audio_path
    db.commit()
    
    return {"message": "Audio uploaded successfully", "path": audio_path}


@router.post("/words/{word_id}/image")
async def upload_word_image(
    word_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Upload image for a word"""
    # Verify word belongs to user's learning center
    word = db.query(Word).join(Lesson).join(Course).filter(
        Word.id == word_id,
        Course.learning_center_id == current_user.learning_center_id
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Save image file
    image_path = await storage_service.save_image(file, word_id)
    
    # Update word with image path
    word.image = image_path
    db.commit()
    
    return {"message": "Image uploaded successfully", "path": image_path}


@router.get("/courses")
async def list_courses(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all courses in learning center"""
    courses = db.query(Course).filter(
        Course.learning_center_id == current_user.learning_center_id,
        Course.is_active == True,
        Course.deleted_at.is_(None)
    ).all()
    
    return courses


@router.get("/courses/{course_id}/lessons")
async def list_lessons(
    course_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List lessons in a course"""
    lessons = db.query(Lesson).join(Course).filter(
        Lesson.course_id == course_id,
        Course.learning_center_id == current_user.learning_center_id,
        Lesson.deleted_at.is_(None)
    ).order_by(Lesson.order).all()
    
    return lessons


@router.get("/lessons/{lesson_id}/words")
async def list_words(
    lesson_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List words in a lesson"""
    words = db.query(Word).join(Lesson).join(Course).filter(
        Word.lesson_id == lesson_id,
        Course.learning_center_id == current_user.learning_center_id,
        Word.deleted_at.is_(None)
    ).order_by(Word.order).all()
    
    return words
