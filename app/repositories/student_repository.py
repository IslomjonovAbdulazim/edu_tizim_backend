from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.models.student import Student
from app.models.user import User
from app.models.group import Group
from app.repositories.base_repository import BaseRepository


class StudentRepository(BaseRepository[Student]):
    def __init__(self):
        super().__init__(Student)

    def create_with_user(self, db: Session, user_data: dict, student_data: dict) -> Student:
        """Create student with associated user"""
        # This would typically be handled by the service layer
        # but including here for completeness
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository()

        # Create user first
        user = user_repo.create(db, user_data)

        # Create student profile
        student_data["user_id"] = user.id
        return self.create(db, student_data)

    def get_by_user_id(self, db: Session, user_id: int) -> Optional[Student]:
        """Get student by user ID"""
        return db.query(Student).filter(Student.user_id == user_id).first()

    def get_with_user(self, db: Session, student_id: int) -> Optional[Student]:
        """Get student with user information loaded"""
        return db.query(Student).options(joinedload(Student.user)).filter(Student.id == student_id).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        Student]:
        """Get students by learning center"""
        return db.query(Student).join(User).filter(
            User.learning_center_id == learning_center_id
        ).options(joinedload(Student.user)).offset(skip).limit(limit).all()

    def get_by_group(self, db: Session, group_id: int) -> List[Student]:
        """Get students in a specific group"""
        return db.query(Student).join(Student.groups).filter(
            Group.id == group_id
        ).options(joinedload(Student.user)).all()

    def get_without_group(self, db: Session, learning_center_id: Optional[int] = None) -> List[Student]:
        """Get students not assigned to any group"""
        query = db.query(Student).filter(~Student.groups.any())

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).all()

    def add_to_group(self, db: Session, student_id: int, group_id: int) -> bool:
        """Add student to a group"""
        student = self.get(db, student_id)
        group = db.query(Group).filter(Group.id == group_id).first()

        if student and group and group not in student.groups:
            student.groups.append(group)
            db.commit()
            return True
        return False

    def remove_from_group(self, db: Session, student_id: int, group_id: int) -> bool:
        """Remove student from a group"""
        student = self.get(db, student_id)
        group = db.query(Group).filter(Group.id == group_id).first()

        if student and group and group in student.groups:
            student.groups.remove(group)
            db.commit()
            return True
        return False

    def get_student_groups(self, db: Session, student_id: int) -> List[Group]:
        """Get all groups for a student"""
        student = self.get(db, student_id)
        return student.groups if student else []

    def search_students(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Student]:
        """Search students by name or phone number"""
        query = db.query(Student).join(User).filter(
            or_(
                User.full_name.ilike(f"%{search_term}%"),
                User.phone_number.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).offset(skip).limit(limit).all()

    def get_active_students(self, db: Session, learning_center_id: Optional[int] = None) -> List[Student]:
        """Get all active students"""
        query = db.query(Student).join(User).filter(User.is_active == True)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).all()

    def get_students_by_age_range(self, db: Session, min_age: int, max_age: int,
                                  learning_center_id: Optional[int] = None) -> List[Student]:
        """Get students within age range (approximate based on birth date)"""
        from datetime import date, timedelta

        today = date.today()
        max_birth_date = today - timedelta(days=min_age * 365)
        min_birth_date = today - timedelta(days=(max_age + 1) * 365)

        query = db.query(Student).filter(
            and_(
                Student.date_of_birth >= min_birth_date,
                Student.date_of_birth <= max_birth_date
            )
        )

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).all()

    def get_students_by_grade_level(self, db: Session, grade_level: str, learning_center_id: Optional[int] = None) -> List[Student]:
        """Get students by grade level"""
        query = db.query(Student).filter(Student.grade_level == grade_level)

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).all()

    def get_student_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive student statistics"""
        base_query = db.query(Student).join(User)

        if learning_center_id:
            base_query = base_query.filter(User.learning_center_id == learning_center_id)

        total_students = base_query.count()
        active_students = base_query.filter(User.is_active == True).count()

        # Count by grade level
        grade_counts = base_query.with_entities(
            Student.grade_level, func.count(Student.id)
        ).group_by(Student.grade_level).all()

        # Students in groups vs without groups
        students_with_groups = base_query.filter(Student.groups.any()).count()
        students_without_groups = total_students - students_with_groups

        return {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_students": total_students - active_students,
            "grade_distribution": {grade or "unspecified": count for grade, count in grade_counts},
            "students_with_groups": students_with_groups,
            "students_without_groups": students_without_groups,
            "group_participation_rate": (students_with_groups / total_students * 100) if total_students > 0 else 0
        }