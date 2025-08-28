from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.models.word import Word
from app.repositories.base_repository import BaseRepository


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

        return query.options(
            joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(Module.order_index, Lesson.order_index).all()

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Lesson]:
        """Get all lessons in a learning center"""
        query = db.query(Lesson).join(Module).join(Course).filter(
            Course.learning_center_id == learning_center_id
        )

        if active_only:
            query = query.filter(
                and_(
                    Lesson.is_active == True,
                    Module.is_active == True,
                    Course.is_active == True
                )
            )

        return query.options(
            joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(Course.order_index, Module.order_index, Lesson.order_index).all()

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
            learning_center_id: Optional[int] = None,
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
        elif learning_center_id:
            query = query.join(Module).join(Course).filter(Course.learning_center_id == learning_center_id)

        return query.filter(Lesson.is_active == True).options(
            joinedload(Lesson.module).joinedload(Module.course)
        ).offset(skip).limit(limit).all()

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

    def get_lesson_statistics(self, db: Session, lesson_id: int) -> dict:
        """Get statistics for a lesson"""
        lesson = self.get(db, lesson_id)
        if not lesson:
            return {}

        total_words = db.query(Word).filter(Word.lesson_id == lesson_id).count()
        active_words = db.query(Word).filter(
            and_(Word.lesson_id == lesson_id, Word.is_active == True)
        ).count()

        # Average difficulty of words in lesson
        avg_difficulty = db.query(func.avg(Word.difficulty_level)).filter(
            Word.lesson_id == lesson_id
        ).scalar() or 0.0

        return {
            "lesson_id": lesson_id,
            "title": lesson.title,
            "base_points": lesson.base_points,
            "total_words": total_words,
            "active_words": active_words,
            "completion_points": lesson.completion_points,
            "average_word_difficulty": round(float(avg_difficulty), 2)
        }

    def get_next_lesson(self, db: Session, current_lesson_id: int) -> Optional[Lesson]:
        """Get the next lesson in order within the same module"""
        current_lesson = self.get(db, current_lesson_id)
        if not current_lesson:
            return None

        # Try to find next lesson in same module
        next_lesson = db.query(Lesson).filter(
            and_(
                Lesson.module_id == current_lesson.module_id,
                Lesson.order_index > current_lesson.order_index,
                Lesson.is_active == True
            )
        ).order_by(Lesson.order_index).first()

        if next_lesson:
            return next_lesson

        # If no next lesson in current module, try first lesson of next module
        current_module = db.query(Module).filter(Module.id == current_lesson.module_id).first()
        if not current_module:
            return None

        next_module = db.query(Module).filter(
            and_(
                Module.course_id == current_module.course_id,
                Module.order_index > current_module.order_index,
                Module.is_active == True
            )
        ).order_by(Module.order_index).first()

        if next_module:
            return db.query(Lesson).filter(
                and_(
                    Lesson.module_id == next_module.id,
                    Lesson.is_active == True
                )
            ).order_by(Lesson.order_index).first()

        return None

    def get_previous_lesson(self, db: Session, current_lesson_id: int) -> Optional[Lesson]:
        """Get the previous lesson in order within the same module"""
        current_lesson = self.get(db, current_lesson_id)
        if not current_lesson:
            return None

        # Try to find previous lesson in same module
        prev_lesson = db.query(Lesson).filter(
            and_(
                Lesson.module_id == current_lesson.module_id,
                Lesson.order_index < current_lesson.order_index,
                Lesson.is_active == True
            )
        ).order_by(desc(Lesson.order_index)).first()

        if prev_lesson:
            return prev_lesson

        # If no previous lesson in current module, try last lesson of previous module
        current_module = db.query(Module).filter(Module.id == current_lesson.module_id).first()
        if not current_module:
            return None

        prev_module = db.query(Module).filter(
            and_(
                Module.course_id == current_module.course_id,
                Module.order_index < current_module.order_index,
                Module.is_active == True
            )
        ).order_by(desc(Module.order_index)).first()

        if prev_module:
            return db.query(Lesson).filter(
                and_(
                    Lesson.module_id == prev_module.id,
                    Lesson.is_active == True
                )
            ).order_by(desc(Lesson.order_index)).first()

        return None

    def get_lessons_by_difficulty(self, db: Session, difficulty_range: tuple, course_id: Optional[int] = None) -> List[
        Lesson]:
        """Get lessons within a difficulty range based on average word difficulty"""
        min_difficulty, max_difficulty = difficulty_range

        # Subquery to calculate average difficulty per lesson
        difficulty_subq = db.query(
            Word.lesson_id,
            func.avg(Word.difficulty_level).label('avg_difficulty')
        ).filter(Word.is_active == True).group_by(Word.lesson_id).subquery()

        query = db.query(Lesson).join(
            difficulty_subq, Lesson.id == difficulty_subq.c.lesson_id
        ).filter(
            and_(
                difficulty_subq.c.avg_difficulty >= min_difficulty,
                difficulty_subq.c.avg_difficulty <= max_difficulty,
                Lesson.is_active == True
            )
        )

        if course_id:
            query = query.join(Module).filter(Module.course_id == course_id)

        return query.options(
            joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(difficulty_subq.c.avg_difficulty).all()

    def bulk_update_points(self, db: Session, lesson_point_map: dict) -> bool:
        """Bulk update base points for multiple lessons"""
        try:
            for lesson_id, base_points in lesson_point_map.items():
                lesson = self.get(db, lesson_id)
                if lesson:
                    lesson.base_points = base_points

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False