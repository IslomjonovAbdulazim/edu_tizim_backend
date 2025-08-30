from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import (
    CourseService, ModuleService, LessonService, WordService,
    GroupService, LearningService, LearningCenterService,
    GamificationService, UserService, VerificationService,
)

from app.schemas.content import (
    CourseOut, CourseCreate, CourseUpdate,
    ModuleOut, ModuleCreate, ModuleUpdate,
    LessonOut, LessonCreate, LessonUpdate,
    WordOut, WordCreate, WordUpdate,
)

router = APIRouter(prefix="/content", tags=["content"])


# ---------- Helpers (DI) ----------
def course_svc(db: Session = Depends(get_db)) -> CourseService:
    return CourseService(db)

def module_svc(db: Session = Depends(get_db)) -> ModuleService:
    return ModuleService(db)

def lesson_svc(db: Session = Depends(get_db)) -> LessonService:
    return LessonService(db)

def word_svc(db: Session = Depends(get_db)) -> WordService:
    return WordService(db)


# ---------- Courses ----------
@router.get("/courses", response_model=List[CourseOut])
def list_courses(
    learning_center_id: int = Query(..., description="Learning center ID"),
    q: Optional[str] = Query(None, description="Search string for course name/description"),
    svc: CourseService = Depends(course_svc),
):
    if q:
        return svc.search(learning_center_id, q)
    return svc.list_active_by_center(learning_center_id)


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: int, svc: CourseService = Depends(course_svc)):
    course = svc.get_full(course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, svc: CourseService = Depends(course_svc)):
    return svc.create(payload.model_dump())


@router.put("/courses/{course_id}", response_model=CourseOut)
def update_course(course_id: int, payload: CourseUpdate, svc: CourseService = Depends(course_svc)):
    updated = svc.update(course_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return updated


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, svc: CourseService = Depends(course_svc)):
    ok = svc.delete(course_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return None


@router.post("/courses/{learning_center_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_courses(
    learning_center_id: int,
    course_ids_in_order: List[int] = Body(..., embed=True, description="Full ordered list of course IDs"),
    svc: CourseService = Depends(course_svc),
):
    svc.reorder(learning_center_id, course_ids_in_order)
    return None


@router.get("/courses/{course_id}/stats")
def course_stats(course_id: int, svc: CourseService = Depends(course_svc)):
    return svc.stats(course_id)


# ---------- Modules ----------
@router.get("/courses/{course_id}/modules", response_model=List[ModuleOut])
def list_modules(course_id: int, svc: ModuleService = Depends(module_svc)):
    return svc.list_by_course(course_id)


@router.get("/modules/{module_id}", response_model=ModuleOut)
def get_module(module_id: int, svc: ModuleService = Depends(module_svc)):
    module = svc.get_full(module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


@router.post("/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(payload: ModuleCreate, svc: ModuleService = Depends(module_svc)):
    return svc.create(payload.model_dump())


@router.put("/modules/{module_id}", response_model=ModuleOut)
def update_module(module_id: int, payload: ModuleUpdate, svc: ModuleService = Depends(module_svc)):
    updated = svc.update(module_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return updated


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(module_id: int, svc: ModuleService = Depends(module_svc)):
    ok = svc.delete(module_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return None


@router.post("/modules/{course_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_modules(
    course_id: int,
    module_ids_in_order: List[int] = Body(..., embed=True),
    svc: ModuleService = Depends(module_svc),
):
    svc.reorder(course_id, module_ids_in_order)
    return None


@router.get("/modules/{module_id}/stats")
def module_stats(module_id: int, svc: ModuleService = Depends(module_svc)):
    return svc.stats(module_id)


# ---------- Lessons ----------
@router.get("/modules/{module_id}/lessons", response_model=List[LessonOut])
def list_lessons(module_id: int, svc: LessonService = Depends(lesson_svc)):
    return svc.list_by_module(module_id)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, svc: LessonService = Depends(lesson_svc)):
    lesson = svc.get_with_words(lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(payload: LessonCreate, svc: LessonService = Depends(lesson_svc)):
    return svc.create(payload.model_dump())


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(lesson_id: int, payload: LessonUpdate, svc: LessonService = Depends(lesson_svc)):
    updated = svc.update(lesson_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return updated


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(lesson_id: int, svc: LessonService = Depends(lesson_svc)):
    ok = svc.delete(lesson_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return None


@router.post("/lessons/{module_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_lessons(
    module_id: int,
    lesson_ids_in_order: List[int] = Body(..., embed=True),
    svc: LessonService = Depends(lesson_svc),
):
    svc.reorder(module_id, lesson_ids_in_order)
    return None


@router.get("/lessons/{lesson_id}/stats")
def lesson_stats(lesson_id: int, svc: LessonService = Depends(lesson_svc)):
    return svc.stats(lesson_id)


# ---------- Words ----------
@router.get("/lessons/{lesson_id}/words", response_model=List[WordOut])
def list_words(lesson_id: int, svc: WordService = Depends(word_svc)):
    return svc.list_by_lesson(lesson_id)


@router.post("/lessons/{lesson_id}/words/bulk", response_model=List[WordOut], status_code=status.HTTP_201_CREATED)
def bulk_create_words(lesson_id: int, payload: List[WordCreate], svc: WordService = Depends(word_svc)):
    data = [p.model_dump() for p in payload]
    return svc.bulk_create(lesson_id, data)


@router.post("/words", response_model=WordOut, status_code=status.HTTP_201_CREATED)
def create_word(payload: WordCreate, svc: WordService = Depends(word_svc)):
    return svc.create(payload.model_dump())


@router.put("/words/{word_id}", response_model=WordOut)
def update_word(word_id: int, payload: WordUpdate, svc: WordService = Depends(word_svc)):
    updated = svc.update(word_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")
    return updated


@router.delete("/words/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(word_id: int, svc: WordService = Depends(word_svc)):
    ok = svc.delete(word_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")
    return None


@router.post("/words/{lesson_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_words(
    lesson_id: int,
    word_ids_in_order: List[int] = Body(..., embed=True),
    svc: WordService = Depends(word_svc),
):
    svc.reorder(lesson_id, word_ids_in_order)
    return None
