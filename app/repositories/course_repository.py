from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self):
        super().__init__(Course)

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Course]:
        """Get courses by learning center"""
        query = db.query(Course).filter(Course.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(Course.is_active == True)

        return query.order_by(Course.order_index, Course.name).all()

    def get_with_modules(self, db: Session, course_id: int, active_only: bool = True) -> Optional[Course]:
        """Get course with modules loaded"""
        query = db.query(Course).options(joinedload(Course.modules)).filter(Course.id == course_id)

        course = query.first()
        if course and active_only:
            course.modules = [m for m in course.modules if m.is_active]

        return course

    def get_by_level(self, db: Session, level: str, learning_center_id: Optional[int] = None) -> List[Course]:
        """Get courses by difficulty level"""
        query = db.query(Course).filter(Course.level == level)

        if learning_center_id:
            query = query.filter(Course.learning_center_id == learning_center_id)

        return query.filter(Course.is_active == True).order_by(Course.order_index).all()

    def search_courses(self, db: Session, term: str, learning_center_id: Optional[int] = None) -> List[Course]:
        """Search courses by name or description"""
        query = db.query(Course).filter(
            Course.name.ilike(f"%{term}%") |
            Course.description.ilike(f"%{term}%")
        )

        if learning_center_id:
            query = query.filter(Course.learning_center_id == learning_center_id)

        return query.filter(Course.is_active == True).all()

    def reorder_courses(self, db: Session, course_orders: List[dict]) -> bool:
        """Update course order indexes"""
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

    def get_course_statistics(self, db: Session, course_id: int) -> dict:
        """Get course statistics"""
        course = self.get_with_modules(db, course_id)

        if not course:
            return {}

        total_lessons = sum(len(module.lessons) for module in course.modules)
        total_words = sum(
            sum(len(lesson.words) for lesson in module.lessons)
            for module in course.modules
        )

        return {
            "course_id": course_id,
            "name": course.name,
            "total_modules": len(course.modules),
            "total_lessons": total_lessons,
            "total_words": total_words,
            "completion_points": course.completion_points,
            "level": course.level
        }