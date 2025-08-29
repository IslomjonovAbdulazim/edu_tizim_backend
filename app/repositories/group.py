from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from app.models import Group, User, student_groups
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    def __init__(self, db: Session):
        super().__init__(Group, db)

    def get_by_branch(self, branch_id: int) -> List[Group]:
        """Get all groups in branch"""
        return self.db.query(Group).filter(Group.branch_id == branch_id).all()

    def get_active_by_branch(self, branch_id: int) -> List[Group]:
        """Get active groups in branch"""
        return self.db.query(Group).filter(
            and_(
                Group.branch_id == branch_id,
                Group.is_active == True
            )
        ).all()

    def get_by_teacher(self, teacher_id: int) -> List[Group]:
        """Get groups taught by teacher"""
        return self.db.query(Group).filter(Group.teacher_id == teacher_id).all()

    def get_by_course(self, course_id: int) -> List[Group]:
        """Get groups for specific course"""
        return self.db.query(Group).filter(Group.course_id == course_id).all()

    def get_with_students(self, group_id: int) -> Optional[Group]:
        """Get group with all students loaded"""
        return self.db.query(Group).options(
            joinedload(Group.students)
        ).filter(Group.id == group_id).first()

    def add_student_to_group(self, user_id: int, group_id: int) -> bool:
        """Add student to group"""
        # Check if student is already in group
        existing = self.db.query(student_groups).filter(
            and_(
                student_groups.c.user_id == user_id,
                student_groups.c.group_id == group_id
            )
        ).first()

        if existing:
            return False  # Already in group

        # Check if user is a student
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "student":
            return False

        # Add to group
        stmt = student_groups.insert().values(user_id=user_id, group_id=group_id)
        self.db.execute(stmt)
        self.db.commit()
        return True

    def remove_student_from_group(self, user_id: int, group_id: int) -> bool:
        """Remove student from group"""
        result = self.db.query(student_groups).filter(
            and_(
                student_groups.c.user_id == user_id,
                student_groups.c.group_id == group_id
            )
        ).delete()

        self.db.commit()
        return result > 0

    def add_students_to_group(self, user_ids: List[int], group_id: int) -> int:
        """Add multiple students to group"""
        added_count = 0
        for user_id in user_ids:
            if self.add_student_to_group(user_id, group_id):
                added_count += 1
        return added_count

    def get_group_students(self, group_id: int) -> List[User]:
        """Get all students in group"""
        return self.db.query(User).join(
            student_groups, User.id == student_groups.c.user_id
        ).filter(student_groups.c.group_id == group_id).all()

    def get_student_groups(self, user_id: int) -> List[Group]:
        """Get all groups a student belongs to"""
        return self.db.query(Group).join(
            student_groups, Group.id == student_groups.c.group_id
        ).filter(student_groups.c.user_id == user_id).all()

    def assign_teacher(self, group_id: int, teacher_id: int) -> Optional[Group]:
        """Assign teacher to group"""
        group = self.get(group_id)
        if not group:
            return None

        # Verify teacher exists and has teacher role
        teacher = self.db.query(User).filter(
            and_(
                User.id == teacher_id,
                User.role == "teacher"
            )
        ).first()

        if not teacher:
            return None

        group.teacher_id = teacher_id
        self.db.commit()
        self.db.refresh(group)
        return group

    def remove_teacher(self, group_id: int) -> Optional[Group]:
        """Remove teacher from group"""
        group = self.get(group_id)
        if group:
            group.teacher_id = None
            self.db.commit()
            self.db.refresh(group)
        return group

    def get_groups_by_learning_center(self, learning_center_id: int) -> List[Group]:
        """Get all groups in learning center (across all branches)"""
        from app.models import Branch
        return self.db.query(Group).join(Branch).filter(
            Branch.learning_center_id == learning_center_id
        ).all()

    def search_groups(self, learning_center_id: int, query: str) -> List[Group]:
        """Search groups by title"""
        from app.models import Branch
        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.title.ilike(f"%{query}%")
            )
        ).all()

    def get_group_capacity_info(self, group_id: int) -> dict:
        """Get group capacity information"""
        group = self.get_with_students(group_id)
        if not group:
            return {}

        student_count = len(group.students)
        max_capacity = 25  # Default - you might want to add this as a field

        return {
            'group_id': group_id,
            'current_students': student_count,
            'max_capacity': max_capacity,
            'available_spots': max(0, max_capacity - student_count),
            'is_full': student_count >= max_capacity,
            'capacity_percentage': (student_count / max_capacity * 100) if max_capacity > 0 else 0
        }

    def transfer_student(self, user_id: int, from_group_id: int, to_group_id: int) -> bool:
        """Transfer student from one group to another"""
        # Remove from old group
        if not self.remove_student_from_group(user_id, from_group_id):
            return False

        # Add to new group
        if not self.add_student_to_group(user_id, to_group_id):
            # If adding to new group fails, add back to old group
            self.add_student_to_group(user_id, from_group_id)
            return False

        return True

    def get_groups_needing_teacher(self, learning_center_id: int) -> List[Group]:
        """Get active groups without assigned teacher"""
        from app.models import Branch
        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.is_active == True,
                Group.teacher_id.is_(None)
            )
        ).all()