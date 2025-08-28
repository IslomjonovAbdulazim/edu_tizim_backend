from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.models.parent import Parent
from app.models.student import Student
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class ParentRepository(BaseRepository[Parent]):
    def __init__(self):
        super().__init__(Parent)

    def create_with_user(self, db: Session, user_data: dict, parent_data: dict) -> Parent:
        """Create parent with associated user"""
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository()

        # Create user first
        user = user_repo.create(db, user_data)

        # Create parent profile
        parent_data["user_id"] = user.id
        return self.create(db, parent_data)

    def get_by_user_id(self, db: Session, user_id: int) -> Optional[Parent]:
        """Get parent by user ID"""
        return db.query(Parent).filter(Parent.user_id == user_id).first()

    def get_with_user(self, db: Session, parent_id: int) -> Optional[Parent]:
        """Get parent with user information loaded"""
        return db.query(Parent).options(joinedload(Parent.user)).filter(Parent.id == parent_id).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        Parent]:
        """Get parents by learning center"""
        return db.query(Parent).join(User).filter(
            User.learning_center_id == learning_center_id
        ).options(joinedload(Parent.user)).offset(skip).limit(limit).all()

    def get_by_relationship(self, db: Session, relationship: str, learning_center_id: Optional[int] = None) -> List[
        Parent]:
        """Get parents by relationship to student (father, mother, guardian, etc.)"""
        query = db.query(Parent).filter(Parent.relationship_to_student == relationship)

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Parent.user)).all()

    def get_parents_of_student(self, db: Session, student_id: int) -> List[Parent]:
        """Get all parents of a specific student"""
        return db.query(Parent).join(Parent.students).filter(
            Student.id == student_id
        ).options(joinedload(Parent.user)).all()

    def get_student_children(self, db: Session, parent_id: int) -> List[Student]:
        """Get all student children of a parent"""
        parent = self.get(db, parent_id)
        return parent.students if parent else []

    def add_child(self, db: Session, parent_id: int, student_id: int) -> bool:
        """Link a parent to a student (add child)"""
        parent = self.get(db, parent_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if parent and student and student not in parent.students:
            parent.students.append(student)
            db.commit()
            return True
        return False

    def remove_child(self, db: Session, parent_id: int, student_id: int) -> bool:
        """Unlink a parent from a student (remove child)"""
        parent = self.get(db, parent_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if parent and student and student in parent.students:
            parent.students.remove(student)
            db.commit()
            return True
        return False

    def search_parents(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            relationship: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Parent]:
        """Search parents by name, phone number, or workplace"""
        query = db.query(Parent).join(User).filter(
            or_(
                User.full_name.ilike(f"%{search_term}%"),
                User.phone_number.ilike(f"%{search_term}%"),
                Parent.workplace.ilike(f"%{search_term}%"),
                Parent.occupation.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        if relationship:
            query = query.filter(Parent.relationship_to_student == relationship)

        return query.options(joinedload(Parent.user)).offset(skip).limit(limit).all()

    def get_active_parents(self, db: Session, learning_center_id: Optional[int] = None) -> List[Parent]:
        """Get all active parents"""
        query = db.query(Parent).join(User).filter(User.is_active == True)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Parent.user)).all()

    def get_parents_without_children(self, db: Session, learning_center_id: Optional[int] = None) -> List[Parent]:
        """Get parents who don't have any linked students"""
        query = db.query(Parent).filter(~Parent.students.any())

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Parent.user)).all()

    def get_parents_with_multiple_children(self, db: Session, learning_center_id: Optional[int] = None) -> List[Parent]:
        """Get parents who have multiple children"""
        # This requires a subquery to count students per parent
        from sqlalchemy import exists, select

        query = db.query(Parent).join(User)

        # Add condition for multiple children
        subq = db.query(Parent.id).join(Parent.students).group_by(Parent.id).having(
            func.count(Student.id) > 1).subquery()
        query = query.filter(Parent.id.in_(subq))

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Parent.user)).all()

    def update_relationship(self, db: Session, parent_id: int, new_relationship: str) -> Optional[Parent]:
        """Update parent's relationship to student"""
        parent = self.get(db, parent_id)
        if parent:
            parent.relationship_to_student = new_relationship
            db.commit()
            db.refresh(parent)
        return parent

    def get_parent_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive parent statistics"""
        base_query = db.query(Parent).join(User)

        if learning_center_id:
            base_query = base_query.filter(User.learning_center_id == learning_center_id)

        total_parents = base_query.count()
        active_parents = base_query.filter(User.is_active == True).count()

        # Count by relationship
        relationship_counts = base_query.with_entities(
            Parent.relationship_to_student, func.count(Parent.id)
        ).group_by(Parent.relationship_to_student).all()

        # Parents with/without children
        parents_with_children = base_query.filter(Parent.students.any()).count()
        parents_without_children = total_parents - parents_with_children

        # Count parents with multiple children
        multiple_children_subq = db.query(Parent.id).join(Parent.students).group_by(Parent.id).having(
            func.count(Student.id) > 1).subquery()
        parents_with_multiple_children = base_query.filter(Parent.id.in_(multiple_children_subq)).count()

        return {
            "total_parents": total_parents,
            "active_parents": active_parents,
            "inactive_parents": total_parents - active_parents,
            "relationship_distribution": {rel or "unspecified": count for rel, count in relationship_counts},
            "parents_with_children": parents_with_children,
            "parents_without_children": parents_without_children,
            "parents_with_multiple_children": parents_with_multiple_children,
            "child_coverage_rate": (parents_with_children / total_parents * 100) if total_parents > 0 else 0
        }