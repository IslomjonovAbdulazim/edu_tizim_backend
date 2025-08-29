from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models.student import Student
from app.models.user import User
from app.models.group import Group
from app.repositories.base_repository import BaseRepository


class StudentRepository(BaseRepository[Student]):
    def __init__(self):
        super().__init__(Student)

    def get_by_user_id(self, db: Session, user_id: int) -> Optional[Student]:
        """Get student by user ID"""
        return db.query(Student).filter(Student.user_id == user_id).first()

    def get_with_user(self, db: Session, student_id: int) -> Optional[Student]:
        """Get student with user data"""
        return db.query(Student).options(joinedload(Student.user)).filter(
            Student.id == student_id
        ).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        Student]:
        """Get students by learning center"""
        return db.query(Student).join(User).filter(
            User.learning_center_id == learning_center_id
        ).options(joinedload(Student.user)).offset(skip).limit(limit).all()

    def get_by_group(self, db: Session, group_id: int) -> List[Student]:
        """Get students in group"""
        return db.query(Student).join(Student.groups).filter(
            Group.id == group_id
        ).options(joinedload(Student.user)).all()

    def get_without_group(self, db: Session, learning_center_id: int) -> List[Student]:
        """Get students not in any group"""
        return db.query(Student).join(User).filter(
            and_(
                User.learning_center_id == learning_center_id,
                ~Student.groups.any()
            )
        ).options(joinedload(Student.user)).all()

    def add_to_group(self, db: Session, student_id: int, group_id: int) -> bool:
        """Add student to group"""
        student = self.get(db, student_id)
        group = db.query(Group).filter(Group.id == group_id).first()

        if student and group and group not in student.groups:
            student.groups.append(group)
            db.commit()
            return True
        return False

    def remove_from_group(self, db: Session, student_id: int, group_id: int) -> bool:
        """Remove student from group"""
        student = self.get(db, student_id)
        group = db.query(Group).filter(Group.id == group_id).first()

        if student and group and group in student.groups:
            student.groups.remove(group)
            db.commit()
            return True
        return False

    def get_by_grade_level(self, db: Session, grade_level: str, learning_center_id: Optional[int] = None) -> List[
        Student]:
        """Get students by grade level"""
        query = db.query(Student).filter(Student.grade_level == grade_level)

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Student.user)).all()

    def search_students(self, db: Session, term: str, learning_center_id: Optional[int] = None) -> List[Student]:
        """Search students by name"""
        query = db.query(Student).join(User)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.filter(User.full_name.ilike(f"%{term}%")).options(joinedload(Student.user)).all()