from __future__ import annotations
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, asc, desc, func
from sqlalchemy.exc import SQLAlchemyError

from app.models.content import Course, Module, Lesson, Word
from app.repositories.base import BaseRepository
from .base import BaseService


# ---------------------------- Course ----------------------------
class CourseService(BaseService[Course]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[Course](db, Course)

    # basic reads
    def get(self, course_id: int) -> Optional[Course]:
        return self.repo.get(course_id)

    def get_or_404(self, course_id: int) -> Course:
        return self.guard_exists(self.get(course_id), msg="Course not found")

    def list_by_center(self, learning_center_id: int) -> List[Course]:
        return self.repo.list(learning_center_id=learning_center_id)

    def list_active_by_center(self, learning_center_id: int) -> List[Course]:
        q = self.db.query(Course).filter(and_(Course.learning_center_id == learning_center_id, Course.is_active.is_(True)))
        return q.order_by(asc(Course.order_index)).all()

    def search(self, learning_center_id: int, query: str) -> List[Course]:
        pattern = f"%{query}%"
        return (
            self.db.query(Course)
            .filter(
                and_(
                    Course.learning_center_id == learning_center_id,
                    Course.is_active.is_(True),
                    or_(Course.name.ilike(pattern), Course.description.ilike(pattern)),
                )
            )
            .order_by(asc(Course.order_index))
            .limit(200)
            .all()
        )

    def get_full(self, course_id: int) -> Optional[Course]:
        # use selectinload for large collections to avoid cartesian explosion
        return (
            self.db.query(Course)
            .options(
                selectinload(Course.modules)
                .selectinload(Module.lessons)
                .selectinload(Lesson.words)
            )
            .filter(and_(Course.id == course_id, Course.is_active.is_(True)))
            .first()
        )

    # mutations
    def create(self, data: Dict[str, Any]) -> Course:
        return self.repo.create(data)

    def update(self, course_id: int, data: Dict[str, Any]) -> Optional[Course]:
        return self.repo.update(course_id, data)

    def delete(self, course_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(course_id, hard=hard)

    def reorder(self, learning_center_id: int, course_order: List[int]) -> bool:
        try:
            allowed_ids = {
                cid for (cid,) in self.db.query(Course.id).filter(
                    and_(Course.learning_center_id == learning_center_id, Course.id.in_(course_order))
                ).all()
            }
            for index, cid in enumerate(course_order):
                if cid in allowed_ids:
                    self.repo.update(cid, {"order_index": index})
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    # stats
    def stats(self, course_id: int) -> Dict[str, Any]:
        course = self.get(course_id)
        if not course:
            return {}
        module_count = self.db.query(Module).filter(and_(Module.course_id == course_id, Module.is_active.is_(True))).count()
        lesson_count = (
            self.db.query(Lesson)
            .join(Module)
            .filter(and_(Module.course_id == course_id, Module.is_active.is_(True), Lesson.is_active.is_(True)))
            .count()
        )
        word_count = (
            self.db.query(Word)
            .join(Lesson)
            .join(Module)
            .filter(and_(Module.course_id == course_id, Module.is_active.is_(True), Lesson.is_active.is_(True), Word.is_active.is_(True)))
            .count()
        )
        return {
            "course_id": course.id,
            "name": course.name,
            "level": course.level,
            "total_modules": module_count,
            "total_lessons": lesson_count,
            "total_words": word_count,
        }


# ---------------------------- Module ----------------------------
class ModuleService(BaseService[Module]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[Module](db, Module)

    def get(self, module_id: int) -> Optional[Module]:
        return self.repo.get(module_id)

    def get_or_404(self, module_id: int) -> Module:
        return self.guard_exists(self.get(module_id), msg="Module not found")

    def list_by_course(self, course_id: int) -> List[Module]:
        return (
            self.db.query(Module)
            .filter(and_(Module.course_id == course_id, Module.is_active.is_(True)))
            .order_by(asc(Module.order_index))
            .all()
        )

    def get_full(self, module_id: int) -> Optional[Module]:
        return (
            self.db.query(Module)
            .options(selectinload(Module.lessons).selectinload(Lesson.words))
            .filter(and_(Module.id == module_id, Module.is_active.is_(True)))
            .first()
        )

    def get_with_lessons(self, module_id: int) -> Optional[Module]:
        return (
            self.db.query(Module)
            .options(selectinload(Module.lessons))
            .filter(and_(Module.id == module_id, Module.is_active.is_(True)))
            .first()
        )

    def create(self, data: Dict[str, Any]) -> Module:
        return self.repo.create(data)

    def update(self, module_id: int, data: Dict[str, Any]) -> Optional[Module]:
        return self.repo.update(module_id, data)

    def delete(self, module_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(module_id, hard=hard)

    def get_next(self, current_module_id: int) -> Optional[Module]:
        current = self.get(current_module_id)
        if not current:
            return None
        return (
            self.db.query(Module)
            .filter(and_(Module.course_id == current.course_id, Module.order_index > current.order_index, Module.is_active.is_(True)))
            .order_by(asc(Module.order_index))
            .first()
        )

    def get_previous(self, current_module_id: int) -> Optional[Module]:
        current = self.get(current_module_id)
        if not current:
            return None
        return (
            self.db.query(Module)
            .filter(and_(Module.course_id == current.course_id, Module.order_index < current.order_index, Module.is_active.is_(True)))
            .order_by(desc(Module.order_index))
            .first()
        )

    def reorder(self, course_id: int, module_order: List[int]) -> bool:
        try:
            allowed_ids = {
                mid for (mid,) in self.db.query(Module.id).filter(and_(Module.course_id == course_id, Module.id.in_(module_order))).all()
            }
            for index, mid in enumerate(module_order):
                if mid in allowed_ids:
                    self.repo.update(mid, {"order_index": index})
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    def stats(self, module_id: int) -> Dict[str, Any]:
        module = self.get(module_id)
        if not module:
            return {}
        lesson_count = self.db.query(Lesson).filter(and_(Lesson.module_id == module_id, Lesson.is_active.is_(True))).count()
        word_count = (
            self.db.query(Word)
            .join(Lesson)
            .filter(and_(Lesson.module_id == module_id, Lesson.is_active.is_(True), Word.is_active.is_(True)))
            .count()
        )
        return {
            "module_id": module.id,
            "title": module.title,
            "course_id": module.course_id,
            "total_lessons": lesson_count,
            "total_words": word_count,
        }


# ---------------------------- Lesson ----------------------------
class LessonService(BaseService[Lesson]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[Lesson](db, Lesson)

    def get(self, lesson_id: int) -> Optional[Lesson]:
        return self.repo.get(lesson_id)

    def get_or_404(self, lesson_id: int) -> Lesson:
        return self.guard_exists(self.get(lesson_id), msg="Lesson not found")

    def list_by_module(self, module_id: int) -> List[Lesson]:
        return (
            self.db.query(Lesson)
            .filter(and_(Lesson.module_id == module_id, Lesson.is_active.is_(True)))
            .order_by(asc(Lesson.order_index))
            .all()
        )

    def get_with_words(self, lesson_id: int) -> Optional[Lesson]:
        return (
            self.db.query(Lesson)
            .options(selectinload(Lesson.words))
            .filter(and_(Lesson.id == lesson_id, Lesson.is_active.is_(True)))
            .first()
        )

    def create(self, data: Dict[str, Any]) -> Lesson:
        return self.repo.create(data)

    def update(self, lesson_id: int, data: Dict[str, Any]) -> Optional[Lesson]:
        return self.repo.update(lesson_id, data)

    def delete(self, lesson_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(lesson_id, hard=hard)

    def get_next(self, current_lesson_id: int) -> Optional[Lesson]:
        current = self.get(current_lesson_id)
        if not current:
            return None
        next_in_module = (
            self.db.query(Lesson)
            .filter(and_(Lesson.module_id == current.module_id, Lesson.order_index > current.order_index, Lesson.is_active.is_(True)))
            .order_by(asc(Lesson.order_index))
            .first()
        )
        if next_in_module:
            return next_in_module
        from_module = ModuleService(self.db)
        next_module = from_module.get_next(current.module_id)
        if next_module:
            return (
                self.db.query(Lesson)
                .filter(and_(Lesson.module_id == next_module.id, Lesson.is_active.is_(True)))
                .order_by(asc(Lesson.order_index))
                .first()
            )
        return None

    def get_previous(self, current_lesson_id: int) -> Optional[Lesson]:
        current = self.get(current_lesson_id)
        if not current:
            return None
        prev_in_module = (
            self.db.query(Lesson)
            .filter(and_(Lesson.module_id == current.module_id, Lesson.order_index < current.order_index, Lesson.is_active.is_(True)))
            .order_by(desc(Lesson.order_index))
            .first()
        )
        if prev_in_module:
            return prev_in_module
        from_module = ModuleService(self.db)
        prev_module = from_module.get_previous(current.module_id)
        if prev_module:
            return (
                self.db.query(Lesson)
                .filter(and_(Lesson.module_id == prev_module.id, Lesson.is_active.is_(True)))
                .order_by(desc(Lesson.order_index))
                .first()
            )
        return None

    def search(self, learning_center_id: int, query: str) -> List[Lesson]:
        pattern = f"%{query}%"
        return (
            self.db.query(Lesson)
            .join(Module)
            .join(Course)
            .filter(
                and_(
                    Course.learning_center_id == learning_center_id,
                    Course.is_active.is_(True),
                    Module.is_active.is_(True),
                    Lesson.is_active.is_(True),
                    or_(Lesson.title.ilike(pattern), Lesson.description.ilike(pattern), Lesson.content.ilike(pattern)),
                )
            )
            .limit(500)
            .all()
        )

    def reorder(self, module_id: int, lesson_order: List[int]) -> bool:
        try:
            allowed_ids = {
                lid for (lid,) in self.db.query(Lesson.id).filter(and_(Lesson.module_id == module_id, Lesson.id.in_(lesson_order))).all()
            }
            for index, lid in enumerate(lesson_order):
                if lid in allowed_ids:
                    self.repo.update(lid, {"order_index": index})
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    def stats(self, lesson_id: int) -> Dict[str, Any]:
        lesson = self.get(lesson_id)
        if not lesson:
            return {}
        word_count = self.db.query(Word).filter(and_(Word.lesson_id == lesson_id, Word.is_active.is_(True))).count()
        return {"lesson_id": lesson.id, "title": lesson.title, "module_id": lesson.module_id, "total_words": word_count}


# ---------------------------- Word ----------------------------
class WordService(BaseService[Word]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[Word](db, Word)

    def get(self, word_id: int) -> Optional[Word]:
        return self.repo.get(word_id)

    def list_by_lesson(self, lesson_id: int) -> List[Word]:
        return (
            self.db.query(Word)
            .filter(and_(Word.lesson_id == lesson_id, Word.is_active.is_(True)))
            .order_by(asc(Word.order_index))
            .all()
        )

    def create(self, data: Dict[str, Any]) -> Word:
        return self.repo.create(data)

    def bulk_create(self, lesson_id: int, words_data: List[Dict[str, Any]]) -> List[Word]:
        items: List[Dict[str, Any]] = []
        for i, wd in enumerate(words_data):
            row = dict(wd)
            row.setdefault("order_index", i)
            row["lesson_id"] = lesson_id
            items.append(row)
        return self.repo.bulk_create(items)

    def update(self, word_id: int, data: Dict[str, Any]) -> Optional[Word]:
        return self.repo.update(word_id, data)

    def delete(self, word_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(word_id, hard=hard)

    def get_random(self, lesson_id: int, count: int) -> List[Word]:
        from random import sample
        words = self.list_by_lesson(lesson_id)
        return sample(words, min(count, len(words))) if words else []

    def search(self, learning_center_id: int, query: str, search_in: str = "both") -> List[Word]:
        if search_in == "foreign":
            cond = Word.foreign_form.ilike(f"%{query}%")
        elif search_in == "native":
            cond = Word.native_form.ilike(f"%{query}%")
        elif search_in == "example":
            cond = Word.example_sentence.ilike(f"%{query}%")
        else:
            cond = or_(Word.foreign_form.ilike(f"%{query}%"), Word.native_form.ilike(f"%{query}%"), Word.example_sentence.ilike(f"%{query}%"))

        return (
            self.db.query(Word)
            .join(Lesson)
            .join(Module)
            .join(Course)
            .filter(
                and_(
                    Course.learning_center_id == learning_center_id,
                    Course.is_active.is_(True),
                    Module.is_active.is_(True),
                    Lesson.is_active.is_(True),
                    Word.is_active.is_(True),
                    cond,
                )
            )
            .limit(200)
            .all()
        )

    def reorder(self, lesson_id: int, word_order: List[int]) -> bool:
        try:
            allowed_ids = {
                wid for (wid,) in self.db.query(Word.id).filter(and_(Word.lesson_id == lesson_id, Word.id.in_(word_order))).all()
            }
            for index, wid in enumerate(word_order):
                if wid in allowed_ids:
                    self.repo.update(wid, {"order_index": index})
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    def duplicate_exists(self, lesson_id: int, foreign_form: str, *, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Word).filter(and_(Word.lesson_id == lesson_id, Word.foreign_form.ilike(f"{foreign_form}"), Word.is_active.is_(True)))
        if exclude_id is not None:
            q = q.filter(Word.id != exclude_id)
        return q.first() is not None

    def stats_for_center(self, learning_center_id: int) -> Dict[str, Any]:
        total = (
            self.db.query(Word).join(Lesson).join(Module).join(Course)
            .filter(and_(Course.learning_center_id == learning_center_id, Course.is_active.is_(True), Module.is_active.is_(True), Lesson.is_active.is_(True), Word.is_active.is_(True)))
            .count()
        )
        with_audio = (
            self.db.query(Word).join(Lesson).join(Module).join(Course)
            .filter(and_(Course.learning_center_id == learning_center_id, Course.is_active.is_(True), Module.is_active.is_(True), Lesson.is_active.is_(True), Word.is_active.is_(True), Word.audio_url.isnot(None)))
            .count()
        )
        with_images = (
            self.db.query(Word).join(Lesson).join(Module).join(Course)
            .filter(and_(Course.learning_center_id == learning_center_id, Course.is_active.is_(True), Module.is_active.is_(True), Lesson.is_active.is_(True), Word.is_active.is_(True), Word.image_url.isnot(None)))
            .count()
        )
        return {
            "total_words": total,
            "words_with_audio": with_audio,
            "words_with_images": with_images,
            "audio_coverage": (with_audio / total * 100) if total > 0 else 0.0,
            "image_coverage": (with_images / total * 100) if total > 0 else 0.0,
        }
