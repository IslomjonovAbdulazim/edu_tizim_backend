from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.word import Word
from app.repositories.base_repository import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self):
        super().__init__(Course)

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Course]:
        """Get courses by learning center"""
        query = db.query(Course).filter(Course.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(Course.is_active == True)

        return query.order_by(Course.order_index, Course.created_at).all()

    def get_by_language_pair(self, db: Session, language_from: str, language_to: str,
                             learning_center_id: Optional[int] = None) -> List[Course]:
        """Get courses by language pair (from -> to)"""
        query = db.query(Course).filter(
            and_(Course.language_from == language_from, Course.language_to == language_to)
        )

        if learning_center_id:
            query = query.filter(Course.learning_center_id == learning_center_id)

        return query.filter(Course.is_active == True).order_by(Course.order_index).all()

    def get_by_level(self, db: Session, level: str, learning_center_id: Optional[int] = None) -> List[Course]:
        """Get courses by level"""
        query = db.query(Course).filter(Course.level == level)

        if learning_center_id:
            query = query.filter(Course.learning_center_id == learning_center_id)

        return query.filter(Course.is_active == True).order_by(Course.order_index).all()

    def get_with_modules(self, db: Session, course_id: int, active_only: bool = True) -> Optional[Course]:
        """Get course with its modules loaded"""
        query = db.query(Course).options(joinedload(Course.modules)).filter(Course.id == course_id)

        course = query.first()
        if course and active_only:
            # Filter active modules
            course.modules = [module for module in course.modules if module.is_active]

        return course

    def search_courses(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            level: Optional[str] = None,
            language_to: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Course]:
        """Search courses by name or description"""
        query = db.query(Course).filter(
            or_(
                Course.name.ilike(f"%{search_term}%"),
                Course.description.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(Course.learning_center_id == learning_center_id)

        if level:
            query = query.filter(Course.level == level)

        if language_to:
            query = query.filter(Course.language_to == language_to)

        return query.filter(Course.is_active == True).offset(skip).limit(limit).all()

    def reorder_courses(self, db: Session, course_orders: List[dict]) -> bool:
        """Reorder courses by updating their order_index"""
        try:
            for order_data in course_orders:
                course = self.get(db, order_data["course_id"])
                if course:
                    course.order_index = order_data["order_index"]

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False


class ModuleRepository(BaseRepository[Module]):
    def __init__(self):
        super().__init__(Module)

    def get_by_course(self, db: Session, course_id: int, active_only: bool = True) -> List[Module]:
        """Get modules by course"""
        query = db.query(Module).filter(Module.course_id == course_id)

        if active_only:
            query = query.filter(Module.is_active == True)

        return query.order_by(Module.order_index, Module.created_at).all()

    def get_with_lessons(self, db: Session, module_id: int, active_only: bool = True) -> Optional[Module]:
        """Get module with its lessons loaded"""
        query = db.query(Module).options(joinedload(Module.lessons)).filter(Module.id == module_id)

        module = query.first()
        if module and active_only:
            module.lessons = [lesson for lesson in module.lessons if lesson.is_active]

        return module

    def search_modules(
            self,
            db: Session,
            search_term: str,
            course_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Module]:
        """Search modules by title or description"""
        query = db.query(Module).filter(
            or_(
                Module.title.ilike(f"%{search_term}%"),
                Module.description.ilike(f"%{search_term}%")
            )
        )

        if course_id:
            query = query.filter(Module.course_id == course_id)

        return query.filter(Module.is_active == True).offset(skip).limit(limit).all()

    def reorder_modules(self, db: Session, module_orders: List[dict]) -> bool:
        """Reorder modules within a course"""
        try:
            for order_data in module_orders:
                module = self.get(db, order_data["module_id"])
                if module:
                    module.order_index = order_data["order_index"]

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False


class LessonRepository(BaseRepository[Lesson]):
    def __init__(self):
        super().__init__(Lesson)

    def get_by_module(self, db: Session, module_id: int, active_only: bool = True) -> List[Lesson]:
        """Get lessons by module"""
        query = db.query(Lesson).filter(Lesson.module_id == module_id)

        if active_only:
            query = query.filter(Lesson.is_active == True)

        return query.order_by(Lesson.order_index, Lesson.created_at).all()

    def get_by_course(self, db: Session, course_id: int, active_only: bool = True) -> List[Lesson]:
        """Get all lessons in a course"""
        query = db.query(Lesson).join(Module).filter(Module.course_id == course_id)

        if active_only:
            query = query.filter(and_(Lesson.is_active == True, Module.is_active == True))

        return query.order_by(Module.order_index, Lesson.order_index).all()

    def get_with_words(self, db: Session, lesson_id: int, active_only: bool = True) -> Optional[Lesson]:
        """Get lesson with its words loaded"""
        query = db.query(Lesson).options(joinedload(Lesson.words)).filter(Lesson.id == lesson_id)

        lesson = query.first()
        if lesson and active_only:
            lesson.words = [word for word in lesson.words if word.is_active]

        return lesson

    def search_lessons(
            self,
            db: Session,
            search_term: str,
            course_id: Optional[int] = None,
            module_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Lesson]:
        """Search lessons by title, description, or content"""
        query = db.query(Lesson).filter(
            or_(
                Lesson.title.ilike(f"%{search_term}%"),
                Lesson.description.ilike(f"%{search_term}%"),
                Lesson.content.ilike(f"%{search_term}%")
            )
        )

        if module_id:
            query = query.filter(Lesson.module_id == module_id)
        elif course_id:
            query = query.join(Module).filter(Module.course_id == course_id)

        return query.filter(Lesson.is_active == True).offset(skip).limit(limit).all()

    def reorder_lessons(self, db: Session, lesson_orders: List[dict]) -> bool:
        """Reorder lessons within a module"""
        try:
            for order_data in lesson_orders:
                lesson = self.get(db, order_data["lesson_id"])
                if lesson:
                    lesson.order_index = order_data["order_index"]

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False


class WordRepository(BaseRepository[Word]):
    def __init__(self):
        super().__init__(Word)

    def get_by_lesson(self, db: Session, lesson_id: int, active_only: bool = True) -> List[Word]:
        """Get words by lesson"""
        query = db.query(Word).filter(Word.lesson_id == lesson_id)

        if active_only:
            query = query.filter(Word.is_active == True)

        return query.order_by(Word.order_index, Word.created_at).all()

    def get_by_module(self, db: Session, module_id: int, active_only: bool = True) -> List[Word]:
        """Get all words in a module"""
        query = db.query(Word).join(Lesson).filter(Lesson.module_id == module_id)

        if active_only:
            query = query.filter(and_(Word.is_active == True, Lesson.is_active == True))

        return query.order_by(Lesson.order_index, Word.order_index).all()

    def get_by_course(self, db: Session, course_id: int, active_only: bool = True) -> List[Word]:
        """Get all words in a course"""
        query = db.query(Word).join(Lesson).join(Module).filter(Module.course_id == course_id)

        if active_only:
            query = query.filter(
                and_(
                    Word.is_active == True,
                    Lesson.is_active == True,
                    Module.is_active == True
                )
            )

        return query.order_by(Module.order_index, Lesson.order_index, Word.order_index).all()

    def search_words(
            self,
            db: Session,
            search_term: str,
            lesson_id: Optional[int] = None,
            module_id: Optional[int] = None,
            course_id: Optional[int] = None,
            difficulty_level: Optional[int] = None,
            word_type: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Word]:
        """Search words by foreign word, local word, or example sentence"""
        query = db.query(Word).filter(
            or_(
                Word.foreign.ilike(f"%{search_term}%"),
                Word.local.ilike(f"%{search_term}%"),
                Word.example_sentence.ilike(f"%{search_term}%")
            )
        )

        if lesson_id:
            query = query.filter(Word.lesson_id == lesson_id)
        elif module_id:
            query = query.join(Lesson).filter(Lesson.module_id == module_id)
        elif course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)

        if difficulty_level:
            query = query.filter(Word.difficulty_level == difficulty_level)

        if word_type:
            query = query.filter(Word.word_type == word_type)

        return query.filter(Word.is_active == True).offset(skip).limit(limit).all()

    def get_by_difficulty_level(self, db: Session, difficulty_level: int, course_id: Optional[int] = None) -> List[
        Word]:
        """Get words by difficulty level"""
        query = db.query(Word).filter(Word.difficulty_level == difficulty_level)

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)

        return query.filter(Word.is_active == True).order_by(func.random()).all()

    def get_random_words(self, db: Session, count: int, course_id: Optional[int] = None,
                         exclude_ids: Optional[List[int]] = None) -> List[Word]:
        """Get random words for practice"""
        query = db.query(Word).filter(Word.is_active == True)

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)

        if exclude_ids:
            query = query.filter(~Word.id.in_(exclude_ids))

        return query.order_by(func.random()).limit(count).all()

    def reorder_words(self, db: Session, word_orders: List[dict]) -> bool:
        """Reorder words within a lesson"""
        try:
            for order_data in word_orders:
                word = self.get(db, order_data["word_id"])
                if word:
                    word.order_index = order_data["order_index"]

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def bulk_update_audio_urls(self, db: Session, word_audio_map: dict) -> bool:
        """Bulk update audio URLs for words"""
        try:
            for word_id, audio_url in word_audio_map.items():
                word = self.get(db, word_id)
                if word:
                    word.audio_url = audio_url

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False