from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime
import os
import requests
import logging

from ..database import get_db
from ..dependencies import get_super_admin_user
from ..models import LearningCenter, Course, Lesson, Word, WordDifficulty, User, UserRole
from ..services import storage_service, user_service


router = APIRouter()


class CreateLearningCenterRequest(BaseModel):
    name: str
    phone: str
    student_limit: int
    teacher_limit: int
    group_limit: int
    is_paid: bool = True


class UpdateLearningCenterRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    student_limit: Optional[int] = None
    teacher_limit: Optional[int] = None
    group_limit: Optional[int] = None
    is_paid: Optional[bool] = None


class LearningCenterResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str]
    phone: str
    student_limit: int
    teacher_limit: int
    group_limit: int
    is_active: bool
    is_paid: bool
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return v.isoformat() + 'Z' if v else None
    
    class Config:
        from_attributes = True


@router.post("/learning-centers", response_model=LearningCenterResponse)
async def create_learning_center(
    request: CreateLearningCenterRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new learning center"""
    center = LearningCenter(
        name=request.name,
        phone=request.phone,
        student_limit=request.student_limit,
        teacher_limit=request.teacher_limit,
        group_limit=request.group_limit,
        is_paid=request.is_paid
    )
    
    db.add(center)
    db.commit()
    db.refresh(center)
    
    
    return center


@router.get("/learning-centers", response_model=List[LearningCenterResponse])
async def list_learning_centers(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all learning centers"""
    # CACHING DISABLED - Always fetch from database
    centers = db.query(LearningCenter).filter(
        LearningCenter.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()
    
    return centers


@router.post("/learning-centers/{center_id}/logo")
async def upload_center_logo(
    center_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Upload logo for learning center"""
    center = db.query(LearningCenter).filter(
        LearningCenter.id == center_id,
        LearningCenter.deleted_at.is_(None)
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    # Save logo file
    logo_path = await storage_service.save_logo(file, center_id)
    
    # Update center with logo path
    center.logo = logo_path
    db.commit()
    
    
    return {"message": "Logo muvaffaqiyatli yuklandi", "path": logo_path}


@router.put("/learning-centers/{center_id}", response_model=LearningCenterResponse)
async def update_learning_center(
    center_id: int,
    request: UpdateLearningCenterRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update learning center details"""
    center = db.query(LearningCenter).filter(
        LearningCenter.id == center_id,
        LearningCenter.deleted_at.is_(None)
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    # Update fields if provided
    for field, value in request.dict(exclude_unset=True).items():
        setattr(center, field, value)
    
    db.commit()
    db.refresh(center)
    
    
    return center


@router.post("/learning-centers/{center_id}/toggle-payment")
async def toggle_payment_status(
    center_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle payment status for learning center"""
    center = db.query(LearningCenter).filter(
        LearningCenter.id == center_id,
        LearningCenter.deleted_at.is_(None)
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    center.is_paid = not center.is_paid
    db.commit()
    
    
    return {
        "message": f"To'lov holati {'yoqildi' if center.is_paid else 'o'chirildi'}",
        "is_paid": center.is_paid
    }


@router.delete("/learning-centers/{center_id}")
async def deactivate_learning_center(
    center_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate learning center (soft delete)"""
    center = db.query(LearningCenter).filter(
        LearningCenter.id == center_id,
        LearningCenter.deleted_at.is_(None)
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    # Soft delete: mark as inactive and set deleted_at timestamp
    from sqlalchemy.sql import func
    center.is_active = False
    center.deleted_at = func.now()
    db.commit()
    
    return {"message": "O'quv markazi muvaffaqiyatli o'chirildi"}


# User Management Schemas
class CreateUserRequest(BaseModel):
    phone: str
    name: str
    role: UserRole
    learning_center_id: int


class UpdateUserRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None
    learning_center_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    phone: str
    name: str
    role: UserRole
    learning_center_id: int
    coins: int
    is_active: bool
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, v):
        return v.isoformat() + 'Z' if v else None
    
    class Config:
        from_attributes = True


# User Management Endpoints (Super Admin Only)

@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin/teacher/student) for any learning center (Super Admin only)"""
    # Verify learning center exists
    center = db.query(LearningCenter).filter(
        LearningCenter.id == request.learning_center_id
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    # Check if phone number is unique within learning center (exclude deleted users)
    existing_user = db.query(User).filter(
        User.phone == request.phone,
        User.learning_center_id == request.learning_center_id,
        User.deleted_at.is_(None)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon raqami ushbu o'quv markazida allaqachon mavjud"
        )
    
    user = user_service.create_user(
        db=db,
        phone=request.phone,
        name=request.name,
        role=request.role,
        learning_center_id=request.learning_center_id
    )
    
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    learning_center_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all users across all learning centers (Super Admin only)"""
    query = db.query(User).filter(User.deleted_at.is_(None))
    
    if learning_center_id:
        query = query.filter(User.learning_center_id == learning_center_id)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get specific user details (Super Admin only)"""
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update user details (Super Admin only)"""
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    # Validate learning center if updating
    if request.learning_center_id:
        center = db.query(LearningCenter).filter(
            LearningCenter.id == request.learning_center_id
        ).first()
        if not center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="O'quv markazi topilmadi"
            )
    
    # Check phone uniqueness if updating phone (exclude deleted users)
    if request.phone and request.phone != user.phone:
        learning_center_id = request.learning_center_id or user.learning_center_id
        existing_phone = db.query(User).filter(
            User.phone == request.phone,
            User.learning_center_id == learning_center_id,
            User.id != user_id,
            User.deleted_at.is_(None)
        ).first()
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu telefon raqami ushbu o'quv markazida allaqachon mavjud"
            )
    
    # Update fields if provided
    for field, value in request.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) user (Super Admin only)"""
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    # Soft delete: mark as inactive and set deleted_at timestamp
    from sqlalchemy.sql import func
    user.is_active = False
    user.deleted_at = func.now()
    db.commit()
    
    return {"message": "Foydalanuvchi muvaffaqiyatli o'chirildi"}


# Content Management Schemas
class CreateCourseRequest(BaseModel):
    title: str
    learning_center_id: int


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
    learning_center_id: Optional[int] = None


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


class GenerateAudioRequest(BaseModel):
    text: str
    voice: Optional[str] = None


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


# Content Management Endpoints (Super Admin Only)

@router.post("/content/courses", response_model=CourseResponse)
async def create_course(
    request: CreateCourseRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new course (Super Admin only)"""
    # Verify learning center exists
    center = db.query(LearningCenter).filter(
        LearningCenter.id == request.learning_center_id
    ).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'quv markazi topilmadi"
        )
    
    course = Course(
        title=request.title,
        learning_center_id=request.learning_center_id
    )
    
    db.add(course)
    db.commit()
    db.refresh(course)
    
    # Invalidate course cache
    
    return course


@router.get("/content/courses", response_model=List[CourseResponse])
async def list_all_courses(
    learning_center_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all courses across all learning centers (Super Admin only)"""
    from sqlalchemy import func
    
    # Get courses with lesson count
    query = db.query(
        Course.id,
        Course.title,
        Course.learning_center_id,
        Course.is_active,
        Course.created_at,
        func.count(Lesson.id).label('lesson_count')
    ).outerjoin(Lesson, (Lesson.course_id == Course.id) & (Lesson.deleted_at.is_(None))).filter(
        Course.deleted_at.is_(None)
    )
    
    if learning_center_id:
        query = query.filter(Course.learning_center_id == learning_center_id)
    
    courses = query.group_by(Course.id).offset(skip).limit(limit).all()
    
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


@router.put("/content/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    request: UpdateCourseRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update course (Super Admin only)"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None)
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs topilmadi"
        )
    
    # Update fields if provided
    if request.title:
        course.title = request.title
    if request.learning_center_id:
        # Verify new learning center exists
        center = db.query(LearningCenter).filter(
            LearningCenter.id == request.learning_center_id
        ).first()
        if not center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="O'quv markazi topilmadi"
            )
        course.learning_center_id = request.learning_center_id
    
    db.commit()
    db.refresh(course)
    
    return course


@router.delete("/content/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Delete course (Super Admin only)"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None)
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs topilmadi"
        )
    
    # Soft delete: mark as inactive and set deleted_at timestamp
    from sqlalchemy.sql import func
    course.is_active = False
    course.deleted_at = func.now()
    db.commit()
    
    return {"message": "Kurs muvaffaqiyatli o'chirildi"}


@router.post("/content/courses/{course_id}/lessons", response_model=LessonResponse)
async def create_lesson(
    course_id: int,
    request: CreateLessonRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new lesson (Super Admin only)"""
    # Verify course exists and is not deleted
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None)
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs topilmadi"
        )
    
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


@router.get("/content/lessons", response_model=List[LessonResponse])
async def list_all_lessons(
    course_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all lessons (Super Admin only)"""
    from sqlalchemy import func
    
    # Get lessons with word count
    query = db.query(
        Lesson.id,
        Lesson.title,
        Lesson.content,
        Lesson.order,
        Lesson.course_id,
        Lesson.created_at,
        func.count(Word.id).label('word_count')
    ).outerjoin(Word, (Word.lesson_id == Lesson.id) & (Word.deleted_at.is_(None))).filter(
        Lesson.deleted_at.is_(None)
    )
    
    if course_id:
        query = query.filter(Lesson.course_id == course_id)
    
    lessons = query.group_by(Lesson.id).order_by(Lesson.order).offset(skip).limit(limit).all()
    
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


@router.put("/content/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    request: UpdateLessonRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update lesson (Super Admin only)"""
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.deleted_at.is_(None)
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dars topilmadi"
        )
    
    # Update fields if provided
    if request.title:
        lesson.title = request.title
    if request.content is not None:
        lesson.content = request.content
    if request.order:
        lesson.order = request.order
    
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.delete("/content/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Delete lesson (Super Admin only)"""
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.deleted_at.is_(None)
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dars topilmadi"
        )
    
    from sqlalchemy.sql import func
    lesson.deleted_at = func.now()
    db.commit()
    
    return {"message": "Dars muvaffaqiyatli o'chirildi"}


@router.post("/content/lessons/{lesson_id}/words", response_model=WordResponse)
async def create_word(
    lesson_id: int,
    request: CreateWordRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new word (Super Admin only)"""
    # Verify lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dars topilmadi"
        )
    
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


@router.get("/content/words", response_model=List[WordResponse])
async def list_all_words(
    lesson_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all words (Super Admin only)"""
    query = db.query(Word).filter(Word.deleted_at.is_(None))
    
    if lesson_id:
        query = query.filter(Word.lesson_id == lesson_id)
    
    words = query.order_by(Word.order).offset(skip).limit(limit).all()
    return words


@router.put("/content/words/{word_id}", response_model=WordResponse)
async def update_word(
    word_id: int,
    request: UpdateWordRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update word (Super Admin only)"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="So'z topilmadi"
        )
    
    # Update fields if provided
    for field, value in request.dict(exclude_unset=True).items():
        setattr(word, field, value)
    
    db.commit()
    db.refresh(word)
    
    return word


@router.delete("/content/words/{word_id}")
async def delete_word(
    word_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Delete word (Super Admin only)"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="So'z topilmadi"
        )
    
    from sqlalchemy.sql import func
    word.deleted_at = func.now()
    db.commit()
    
    return {"message": "So'z muvaffaqiyatli o'chirildi"}


@router.post("/content/words/{word_id}/audio")
async def upload_word_audio(
    word_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Upload audio for a word (Super Admin only)"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="So'z topilmadi"
        )
    
    # Save audio file
    audio_path = await storage_service.save_audio(file, word_id)
    
    # Update word with audio path
    word.audio = audio_path
    db.commit()
    
    return {"message": "Audio muvaffaqiyatli yuklandi", "path": audio_path}


@router.post("/content/words/{word_id}/image")
async def upload_word_image(
    word_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Upload image for a word (Super Admin only)"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="So'z topilmadi"
        )
    
    # Save image file
    image_path = await storage_service.save_image(file, word_id)
    
    # Update word with image path
    word.image = image_path
    db.commit()
    
    return {"message": "Rasm muvaffaqiyatli yuklandi", "path": image_path}


@router.post("/generate-audio")
async def generate_audio(
    request: GenerateAudioRequest,
    current_user = Depends(get_super_admin_user)
):
    """Generate audio using Narakeet TTS (Super Admin only)"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting audio generation for text: {request.text[:50]}...")
        
        api_key = os.environ.get('NARAKEET')
        logger.info(f"API key present: {bool(api_key)}")
        
        if not api_key:
            logger.error("NARAKEET environment variable not found")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="NARAKEET muhit o'zgaruvchisi o'rnatilmagan"
            )
        
        # Build URL with voice parameter
        url = 'https://api.narakeet.com/text-to-speech/m4a'
        if request.voice:
            url += f'?voice={request.voice}'
            
        logger.info(f"Calling Narakeet API: {url}")
        
        options = {
            'headers': {
                'Accept': 'application/octet-stream',
                'Content-Type': 'text/plain',
                'x-api-key': api_key,
            },
            'data': request.text.encode('utf8')
        }
        
        response = requests.post(url, **options)
        logger.info(f"Narakeet response status: {response.status_code}")
        logger.info(f"Narakeet response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        logger.info(f"Audio generated successfully, size: {len(response.content)} bytes")
        
        return Response(
            content=response.content,
            media_type="audio/m4a",
            headers={
                "Content-Disposition": "attachment; filename=generated_audio.m4a"
            }
        )
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Narakeet HTTP error: {e}")
        logger.error(f"Response status: {e.response.status_code}")
        logger.error(f"Response text: {e.response.text}")
        
        error_message = f'HTTP error: {e.response.status_code} - {e.response.reason}'
        error_details = e.response.text if hasattr(e.response, 'text') else str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'{error_message}. Details: {error_details}'
        )
    except Exception as e:
        logger.error(f"Unexpected error in audio generation: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio yaratish muvaffaqiyatsiz tugadi: {str(e)} - Turi: {type(e).__name__}"
        )