from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.word import Word
from app.repositories.base_repository import BaseRepository


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

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Module]:
        """Get all modules in a learning center"""
        query = db.query(Module).join(Course).filter(Course.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(and_(Module.is_active == True, Course.is_active == True))

        return query.options(joinedload(Module.course)).order_by(Course.order_index, Module.order_index).all()

    def search_modules(
            self,
            db: Session,
            search_term: str,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
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
        elif learning_center_id:
            query = query.join(Course).filter(Course.learning_center_id == learning_center_id)

        return query.filter(Module.is_active == True).options(
            joinedload(Module.course)
        ).offset(skip).limit(limit).all()

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

    def get_module_statistics(self, db: Session, module_id: int) -> dict:
        """Get statistics for a module"""
        module = self.get(db, module_id)
        if not module:
            return {}

        total_lessons = db.query(Lesson).filter(Lesson.module_id == module_id).count()
        active_lessons = db.query(Lesson).filter(
            and_(Lesson.module_id == module_id, Lesson.is_active == True)
        ).count()

        # Total words across all lessons in module
        total_words = db.query(func.count(Word.id)).select_from(Lesson).join(Word).filter(
            Lesson.module_id == module_id
        ).scalar() or 0

        return {
            "module_id": module_id,
            "title": module.title,
            "total_lessons": total_lessons,
            "active_lessons": active_lessons,
            "total_words": total_words,
            "completion_points": module.completion_points
        }

    def get_next_module(self, db: Session, current_module_id: int) -> Optional[Module]:
        """Get the next module in order within the same course"""
        current_module = self.get(db, current_module_id)
        if not current_module:
            return None

        return db.query(Module).filter(
            and_(
                Module.course_id == current_module.course_id,
                Module.order_index > current_module.order_index,
                Module.is_active == True
            )
        ).order_by(Module.order_index).first()

    def get_previous_module(self, db: Session, current_module_id: int) -> Optional[Module]:
        """Get the previous module in order within the same course"""
        current_module = self.get(db, current_module_id)
        if not current_module:
            return None

        return db.query(Module).filter(
            and_(
                Module.course_id == current_module.course_id,
                Module.order_index < current_module.order_index,
                Module.is_active == True
            )
        ).order_by(desc(Module.order_index)).first()