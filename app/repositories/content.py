from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from app.models import Course, Module, Lesson, Word
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, db: Session):
        super().__init__(Course, db)

    def get_by_center(self, learning_center_id: int) -> List[Course]:
        """Get all courses for learning center"""
        return self.db.query(Course).filter(
            Course.learning_center_id == learning_center_id
        ).order_by(Course.order_index).all()

    def get_active_by_center(self, learning_center_id: int) -> List[Course]:
        """Get active courses for learning center"""
        return self.db.query(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True
            )
        ).order_by(Course.order_index).all()

    def get_with_modules(self, course_id: int) -> Optional[Course]:
        """Get course with all modules loaded"""
        return self.db.query(Course).options(
            joinedload(Course.modules)
        ).filter(Course.id == course_id).first()

    def get_full_content(self, course_id: int) -> Optional[Course]:
        """Get course with modules, lessons, and words"""
        return self.db.query(Course).options(
            joinedload(Course.modules).joinedload(Module.lessons).joinedload(Lesson.words)
        ).filter(Course.id == course_id).first()


class ModuleRepository(BaseRepository[Module]):
    def __init__(self, db: Session):
        super().__init__(Module, db)

    def get_by_course(self, course_id: int) -> List[Module]:
        """Get all modules for course"""
        return self.db.query(Module).filter(
            Module.course_id == course_id
        ).order_by(Module.order_index).all()

    def get_active_by_course(self, course_id: int) -> List[Module]:
        """Get active modules for course"""
        return self.db.query(Module).filter(
            and_(
                Module.course_id == course_id,
                Module.is_active == True
            )
        ).order_by(Module.order_index).all()

    def get_with_lessons(self, module_id: int) -> Optional[Module]:
        """Get module with all lessons loaded"""
        return self.db.query(Module).options(
            joinedload(Module.lessons)
        ).filter(Module.id == module_id).first()

    def get_full_content(self, module_id: int) -> Optional[Module]:
        """Get module with lessons and words"""
        return self.db.query(Module).options(
            joinedload(Module.lessons).joinedload(Lesson.words)
        ).filter(Module.id == module_id).first()


class LessonRepository(BaseRepository[Lesson]):
    def __init__(self, db: Session):
        super().__init__(Lesson, db)

    def get_by_module(self, module_id: int) -> List[Lesson]:
        """Get all lessons for module"""
        return self.db.query(Lesson).filter(
            Lesson.module_id == module_id
        ).order_by(Lesson.order_index).all()

    def get_active_by_module(self, module_id: int) -> List[Lesson]:
        """Get active lessons for module"""
        return self.db.query(Lesson).filter(
            and_(
                Lesson.module_id == module_id,
                Lesson.is_active == True
            )
        ).order_by(Lesson.order_index).all()

    def get_with_words(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson with all words loaded"""
        return self.db.query(Lesson).options(
            joinedload(Lesson.words)
        ).filter(Lesson.id == lesson_id).first()

    def get_by_course(self, course_id: int) -> List[Lesson]:
        """Get all lessons in a course"""
        return self.db.query(Lesson).join(Module).filter(
            Module.course_id == course_id
        ).order_by(Module.order_index, Lesson.order_index).all()

    def get_next_lesson(self, current_lesson_id: int) -> Optional[Lesson]:
        """Get next lesson in sequence"""
        current = self.get(current_lesson_id)
        if not current:
            return None

        # Try next lesson in same module
        next_in_module = self.db.query(Lesson).filter(
            and_(
                Lesson.module_id == current.module_id,
                Lesson.order_index > current.order_index,
                Lesson.is_active == True
            )
        ).order_by(Lesson.order_index).first()

        if next_in_module:
            return next_in_module

        # Try first lesson in next module
        next_module = self.db.query(Module).filter(
            and_(
                Module.course_id == current.module.course_id,
                Module.order_index > current.module.order_index,
                Module.is_active == True
            )
        ).order_by(Module.order_index).first()

        if next_module:
            return self.db.query(Lesson).filter(
                and_(
                    Lesson.module_id == next_module.id,
                    Lesson.is_active == True
                )
            ).order_by(Lesson.order_index).first()

        return None


class WordRepository(BaseRepository[Word]):
    def __init__(self, db: Session):
        super().__init__(Word, db)

    def get_by_lesson(self, lesson_id: int) -> List[Word]:
        """Get all words for lesson"""
        return self.db.query(Word).filter(
            Word.lesson_id == lesson_id
        ).order_by(Word.order_index).all()

    def get_active_by_lesson(self, lesson_id: int) -> List[Word]:
        """Get active words for lesson"""
        return self.db.query(Word).filter(
            and_(
                Word.lesson_id == lesson_id,
                Word.is_active == True
            )
        ).order_by(Word.order_index).all()

    def search_words(self, learning_center_id: int, query: str) -> List[Word]:
        """Search words by foreign or native form"""
        return self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                (Word.foreign_form.ilike(f"%{query}%") | Word.native_form.ilike(f"%{query}%")),
                Word.is_active == True
            )
        ).all()

    def get_by_foreign_form(self, foreign_form: str) -> Optional[Word]:
        """Get word by foreign form (English)"""
        return self.db.query(Word).filter(
            Word.foreign_form.ilike(foreign_form)
        ).first()

    def get_by_native_form(self, native_form: str) -> Optional[Word]:
        """Get word by native form (Uzbek)"""
        return self.db.query(Word).filter(
            Word.native_form.ilike(native_form)
        ).first()

    def bulk_create_words(self, lesson_id: int, words_data: List[dict]) -> List[Word]:
        """Create multiple words for a lesson"""
        words = []
        for i, word_data in enumerate(words_data):
            word_data['lesson_id'] = lesson_id
            word_data['order_index'] = word_data.get('order_index', i)
            word = Word(**word_data)
            words.append(word)

        self.db.add_all(words)
        self.db.commit()
        for word in words:
            self.db.refresh(word)
        return words

    def get_random_words(self, lesson_id: int, count: int = 10) -> List[Word]:
        """Get random words from lesson for quiz"""
        return self.db.query(Word).filter(
            and_(
                Word.lesson_id == lesson_id,
                Word.is_active == True
            )
        ).order_by(func.random()).limit(count).all()

    def get_by_module(self, module_id: int) -> List[Word]:
        """Get all words in a module"""
        return self.db.query(Word).join(Lesson).filter(
            Lesson.module_id == module_id
        ).order_by(Lesson.order_index, Word.order_index).all()

    def get_by_course(self, course_id: int) -> List[Word]:
        """Get all words in a course"""
        return self.db.query(Word).join(Lesson).join(Module).filter(
            Module.course_id == course_id
        ).order_by(Module.order_index, Lesson.order_index, Word.order_index).all()