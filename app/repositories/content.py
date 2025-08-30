from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, asc
from app.models.content import Course, Module, Lesson, Word
from app.repositories.base import BaseRepository
import random


class CourseRepository(BaseRepository):
    """Course repository for educational content management"""

    def __init__(self, db: Session):
        super().__init__(db, Course)

    def get_by_center(self, learning_center_id: int) -> List[Course]:
        """Get all courses for learning center"""
        return self.filter_by(learning_center_id=learning_center_id)

    def get_active_by_center(self, learning_center_id: int) -> List[Course]:
        """Get active courses for learning center ordered by index"""
        return self.db.query(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True
            )
        ).order_by(asc(Course.order_index)).all()

    def get_by_level(self, learning_center_id: int, level: str) -> List[Course]:
        """Get courses by difficulty level"""
        return self.db.query(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.level == level,
                Course.is_active == True
            )
        ).order_by(asc(Course.order_index)).all()

    def get_full_content(self, course_id: int) -> Optional[Course]:
        """Get course with full content hierarchy"""
        return self.db.query(Course).options(
            joinedload(Course.modules).joinedload(Module.lessons).joinedload(Lesson.words)
        ).filter(
            and_(Course.id == course_id, Course.is_active == True)
        ).first()

    def get_with_modules(self, course_id: int) -> Optional[Course]:
        """Get course with modules only"""
        return self.db.query(Course).options(
            joinedload(Course.modules)
        ).filter(
            and_(Course.id == course_id, Course.is_active == True)
        ).first()

    def search_courses(self, learning_center_id: int, query: str) -> List[Course]:
        """Search courses by name or description"""
        return self.db.query(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                or_(
                    Course.name.ilike(f"%{query}%"),
                    Course.description.ilike(f"%{query}%")
                )
            )
        ).order_by(asc(Course.order_index)).all()

    def reorder_courses(self, learning_center_id: int, course_order: List[int]) -> bool:
        """Reorder courses by updating order_index"""
        try:
            for index, course_id in enumerate(course_order):
                self.update(course_id, {"order_index": index})
            return True
        except:
            return False

    def get_course_stats(self, course_id: int) -> Dict[str, Any]:
        """Get course statistics"""
        course = self.get(course_id)
        if not course:
            return {}

        # Count modules, lessons, words
        module_count = self.db.query(Module).filter(
            and_(Module.course_id == course_id, Module.is_active == True)
        ).count()

        lesson_count = self.db.query(Lesson).join(Module).filter(
            and_(
                Module.course_id == course_id,
                Module.is_active == True,
                Lesson.is_active == True
            )
        ).count()

        word_count = self.db.query(Word).join(Lesson).join(Module).filter(
            and_(
                Module.course_id == course_id,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).count()

        return {
            "course_id": course.id,
            "name": course.name,
            "level": course.level,
            "total_modules": module_count,
            "total_lessons": lesson_count,
            "total_words": word_count
        }


class ModuleRepository(BaseRepository):
    """Module repository for content modules"""

    def __init__(self, db: Session):
        super().__init__(db, Module)

    def get_by_course(self, course_id: int) -> List[Module]:
        """Get all modules for course ordered by index"""
        return self.db.query(Module).filter(
            and_(
                Module.course_id == course_id,
                Module.is_active == True
            )
        ).order_by(asc(Module.order_index)).all()

    def get_full_content(self, module_id: int) -> Optional[Module]:
        """Get module with lessons and words"""
        return self.db.query(Module).options(
            joinedload(Module.lessons).joinedload(Lesson.words)
        ).filter(
            and_(Module.id == module_id, Module.is_active == True)
        ).first()

    def get_with_lessons(self, module_id: int) -> Optional[Module]:
        """Get module with lessons only"""
        return self.db.query(Module).options(
            joinedload(Module.lessons)
        ).filter(
            and_(Module.id == module_id, Module.is_active == True)
        ).first()

    def get_next_module(self, current_module_id: int) -> Optional[Module]:
        """Get next module in course"""
        current = self.get(current_module_id)
        if not current:
            return None

        return self.db.query(Module).filter(
            and_(
                Module.course_id == current.course_id,
                Module.order_index > current.order_index,
                Module.is_active == True
            )
        ).order_by(asc(Module.order_index)).first()

    def get_previous_module(self, current_module_id: int) -> Optional[Module]:
        """Get previous module in course"""
        current = self.get(current_module_id)
        if not current:
            return None

        return self.db.query(Module).filter(
            and_(
                Module.course_id == current.course_id,
                Module.order_index < current.order_index,
                Module.is_active == True
            )
        ).order_by(desc(Module.order_index)).first()

    def reorder_modules(self, course_id: int, module_order: List[int]) -> bool:
        """Reorder modules within course"""
        try:
            for index, module_id in enumerate(module_order):
                self.update(module_id, {"order_index": index})
            return True
        except:
            return False

    def get_module_stats(self, module_id: int) -> Dict[str, Any]:
        """Get module statistics"""
        module = self.get(module_id)
        if not module:
            return {}

        lesson_count = self.db.query(Lesson).filter(
            and_(Lesson.module_id == module_id, Lesson.is_active == True)
        ).count()

        word_count = self.db.query(Word).join(Lesson).filter(
            and_(
                Lesson.module_id == module_id,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).count()

        return {
            "module_id": module.id,
            "title": module.title,
            "course_id": module.course_id,
            "total_lessons": lesson_count,
            "total_words": word_count
        }


class LessonRepository(BaseRepository):
    """Lesson repository for individual lessons"""

    def __init__(self, db: Session):
        super().__init__(db, Lesson)

    def get_by_module(self, module_id: int) -> List[Lesson]:
        """Get all lessons for module ordered by index"""
        return self.db.query(Lesson).filter(
            and_(
                Lesson.module_id == module_id,
                Lesson.is_active == True
            )
        ).order_by(asc(Lesson.order_index)).all()

    def get_with_words(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson with all words"""
        return self.db.query(Lesson).options(
            joinedload(Lesson.words)
        ).filter(
            and_(Lesson.id == lesson_id, Lesson.is_active == True)
        ).first()

    def get_next_lesson(self, current_lesson_id: int) -> Optional[Lesson]:
        """Get next lesson in module or next module"""
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
        ).order_by(asc(Lesson.order_index)).first()

        if next_in_module:
            return next_in_module

        # If no more lessons in module, get first lesson of next module
        module_repo = ModuleRepository(self.db)
        next_module = module_repo.get_next_module(current.module_id)

        if next_module:
            return self.db.query(Lesson).filter(
                and_(
                    Lesson.module_id == next_module.id,
                    Lesson.is_active == True
                )
            ).order_by(asc(Lesson.order_index)).first()

        return None

    def get_previous_lesson(self, current_lesson_id: int) -> Optional[Lesson]:
        """Get previous lesson in module or previous module"""
        current = self.get(current_lesson_id)
        if not current:
            return None

        # Try previous lesson in same module
        prev_in_module = self.db.query(Lesson).filter(
            and_(
                Lesson.module_id == current.module_id,
                Lesson.order_index < current.order_index,
                Lesson.is_active == True
            )
        ).order_by(desc(Lesson.order_index)).first()

        if prev_in_module:
            return prev_in_module

        # If no previous lessons in module, get last lesson of previous module
        module_repo = ModuleRepository(self.db)
        prev_module = module_repo.get_previous_module(current.module_id)

        if prev_module:
            return self.db.query(Lesson).filter(
                and_(
                    Lesson.module_id == prev_module.id,
                    Lesson.is_active == True
                )
            ).order_by(desc(Lesson.order_index)).first()

        return None

    def search_lessons(self, learning_center_id: int, query: str) -> List[Lesson]:
        """Search lessons across all courses in learning center"""
        return self.db.query(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                or_(
                    Lesson.title.ilike(f"%{query}%"),
                    Lesson.description.ilike(f"%{query}%"),
                    Lesson.content.ilike(f"%{query}%")
                )
            )
        ).all()

    def reorder_lessons(self, module_id: int, lesson_order: List[int]) -> bool:
        """Reorder lessons within module"""
        try:
            for index, lesson_id in enumerate(lesson_order):
                self.update(lesson_id, {"order_index": index})
            return True
        except:
            return False

    def get_lesson_stats(self, lesson_id: int) -> Dict[str, Any]:
        """Get lesson statistics"""
        lesson = self.get(lesson_id)
        if not lesson:
            return {}

        word_count = self.db.query(Word).filter(
            and_(Word.lesson_id == lesson_id, Word.is_active == True)
        ).count()

        return {
            "lesson_id": lesson.id,
            "title": lesson.title,
            "module_id": lesson.module_id,
            "total_words": word_count
        }


class WordRepository(BaseRepository):
    """Word repository for vocabulary management"""

    def __init__(self, db: Session):
        super().__init__(db, Word)

    def get_by_lesson(self, lesson_id: int) -> List[Word]:
        """Get all words for lesson ordered by index"""
        return self.db.query(Word).filter(
            and_(
                Word.lesson_id == lesson_id,
                Word.is_active == True
            )
        ).order_by(asc(Word.order_index)).all()

    def get_random_words(self, lesson_id: int, count: int) -> List[Word]:
        """Get random words from lesson for quiz"""
        words = self.get_by_lesson(lesson_id)
        return random.sample(words, min(count, len(words))) if words else []

    def get_by_foreign_form(self, foreign_form: str, learning_center_id: int) -> Optional[Word]:
        """Get word by foreign form within learning center"""
        return self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Word.foreign_form.ilike(foreign_form),
                Word.is_active == True
            )
        ).first()

    def search_words(self, learning_center_id: int, query: str, search_in: str = "both") -> List[Word]:
        """Search words by foreign/native form or example"""
        query_filter = None

        if search_in == "foreign":
            query_filter = Word.foreign_form.ilike(f"%{query}%")
        elif search_in == "native":
            query_filter = Word.native_form.ilike(f"%{query}%")
        elif search_in == "example":
            query_filter = Word.example_sentence.ilike(f"%{query}%")
        else:  # both
            query_filter = or_(
                Word.foreign_form.ilike(f"%{query}%"),
                Word.native_form.ilike(f"%{query}%"),
                Word.example_sentence.ilike(f"%{query}%")
            )

        return self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True,
                query_filter
            )
        ).limit(100).all()

    def bulk_create_words(self, lesson_id: int, words_data: List[Dict[str, Any]]) -> List[Word]:
        """Bulk create words for a lesson"""
        words = []
        for i, word_data in enumerate(words_data):
            word_data["lesson_id"] = lesson_id
            word_data["order_index"] = word_data.get("order_index", i)
            words.append(word_data)

        return self.bulk_create(words)

    def reorder_words(self, lesson_id: int, word_order: List[int]) -> bool:
        """Reorder words within lesson"""
        try:
            for index, word_id in enumerate(word_order):
                self.update(word_id, {"order_index": index})
            return True
        except:
            return False

    def duplicate_word_check(self, lesson_id: int, foreign_form: str, exclude_id: int = None) -> bool:
        """Check if word already exists in lesson"""
        query = self.db.query(Word).filter(
            and_(
                Word.lesson_id == lesson_id,
                Word.foreign_form.ilike(foreign_form),
                Word.is_active == True
            )
        )

        if exclude_id:
            query = query.filter(Word.id != exclude_id)

        return query.first() is not None

    def get_words_by_module(self, module_id: int) -> List[Word]:
        """Get all words in a module"""
        return self.db.query(Word).join(Lesson).filter(
            and_(
                Lesson.module_id == module_id,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).order_by(asc(Lesson.order_index), asc(Word.order_index)).all()

    def get_words_by_course(self, course_id: int) -> List[Word]:
        """Get all words in a course"""
        return self.db.query(Word).join(Lesson).join(Module).filter(
            and_(
                Module.course_id == course_id,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).order_by(asc(Module.order_index), asc(Lesson.order_index), asc(Word.order_index)).all()

    def get_words_for_practice(self, learning_center_id: int, limit: int = 50) -> List[Word]:
        """Get random words for practice across all courses"""
        return self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).order_by(func.random()).limit(limit).all()

    def get_word_stats(self, learning_center_id: int) -> Dict[str, Any]:
        """Get vocabulary statistics for learning center"""
        total_words = self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True
            )
        ).count()

        words_with_audio = self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True,
                Word.audio_url.isnot(None)
            )
        ).count()

        words_with_images = self.db.query(Word).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Course.is_active == True,
                Module.is_active == True,
                Lesson.is_active == True,
                Word.is_active == True,
                Word.image_url.isnot(None)
            )
        ).count()

        return {
            "total_words": total_words,
            "words_with_audio": words_with_audio,
            "words_with_images": words_with_images,
            "audio_coverage": (words_with_audio / total_words * 100) if total_words > 0 else 0,
            "image_coverage": (words_with_images / total_words * 100) if total_words > 0 else 0
        }