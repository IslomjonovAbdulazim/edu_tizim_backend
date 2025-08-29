from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models.parent import Parent
from app.models.student import Student
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class ParentRepository(BaseRepository[Parent]):
    def __init__(self):
        super().__init__(Parent)

    def get_by_user_id(self, db: Session, user_id: int) -> Optional[Parent]:
        """Get parent by user ID"""
        return db.query(Parent).filter(Parent.user_id == user_id).first()

    def get_with_user(self, db: Session, parent_id: int) -> Optional[Parent]:
        """Get parent with user data"""
        return db.query(Parent).options(joinedload(Parent.user)).filter(
            Parent.id == parent_id
        ).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        Parent]:
        """Get parents by learning center"""
        return db.query(Parent).join(User).filter(
            User.learning_center_id == learning_center_id
        ).options(joinedload(Parent.user)).offset(skip).limit(limit).all()

    def get_parents_of_student(self, db: Session, student_id: int) -> List[Parent]:
        """Get parents of specific student"""
        return db.query(Parent).join(Parent.students).filter(
            Student.id == student_id
        ).options(joinedload(Parent.user)).all()

    def get_children(self, db: Session, parent_id: int) -> List[Student]:
        """Get children of parent"""
        parent = self.get(db, parent_id)
        return parent.students if parent else []

    def add_child(self, db: Session, parent_id: int, student_id: int) -> bool:
        """Link parent to student"""
        parent = self.get(db, parent_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if parent and student and student not in parent.students:
            parent.students.append(student)
            db.commit()
            return True
        return False

    def remove_child(self, db: Session, parent_id: int, student_id: int) -> bool:
        """Unlink parent from student"""
        parent = self.get(db, parent_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if parent and student and student in parent.students:
            parent.students.remove(student)
            db.commit()
            return True
        return False

    def get_by_relationship(self, db: Session, relationship: str, learning_center_id: Optional[int] = None) -> List[
        Parent]:
        """Get parents by relationship type"""
        query = db.query(Parent).filter(Parent.relationship_to_student == relationship)

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Parent.user)).all()

    def search_parents(self, db: Session, term: str, learning_center_id: Optional[int] = None) -> List[Parent]:
        """Search parents by name"""
        query = db.query(Parent).join(User)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.filter(User.full_name.ilike(f"%{term}%")).options(joinedload(Parent.user)).all()