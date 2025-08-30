from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, asc
from app.models.group import Group
from app.models.user import User, StudentGroup
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository):
    """Group repository for managing student groups"""

    def __init__(self, db: Session):
        super().__init__(db, Group)

    def get_by_branch(self, branch_id: int) -> List[Group]:
        """Get all groups in a branch"""
        return self.db.query(Group).filter(
            and_(
                Group.branch_id == branch_id,
                Group.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    def get_with_students(self, group_id: int) -> Optional[Group]:
        """Get group with student information"""
        return self.db.query(Group).options(
            joinedload(Group.student_memberships).joinedload(StudentGroup.user)
        ).filter(
            and_(Group.id == group_id, Group.is_active == True)
        ).first()

    def get_by_teacher(self, teacher_id: int) -> List[Group]:
        """Get groups assigned to a teacher"""
        return self.db.query(Group).filter(
            and_(
                Group.teacher_id == teacher_id,
                Group.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    def get_by_course(self, course_id: int) -> List[Group]:
        """Get groups using specific course"""
        return self.db.query(Group).filter(
            and_(
                Group.course_id == course_id,
                Group.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    def get_groups_by_learning_center(self, learning_center_id: int) -> List[Group]:
        """Get all groups in a learning center"""
        from app.models.learning_center import Branch

        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.is_active == True,
                Branch.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    def search_groups(self, learning_center_id: int, query: str) -> List[Group]:
        """Search groups by title in learning center"""
        from app.models.learning_center import Branch

        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.title.ilike(f"%{query}%"),
                Group.is_active == True,
                Branch.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    # Student management methods
    def add_student_to_group(self, user_id: int, group_id: int) -> bool:
        """Add student to group"""
        # Check if already exists
        existing = self.db.query(StudentGroup).filter(
            and_(
                StudentGroup.user_id == user_id,
                StudentGroup.group_id == group_id,
                StudentGroup.is_active == True
            )
        ).first()

        if existing:
            return False

        # Create relationship
        student_group = StudentGroup(
            user_id=user_id,
            group_id=group_id,
            is_active=True
        )
        self.db.add(student_group)
        self._commit()
        return True

    def remove_student_from_group(self, user_id: int, group_id: int) -> bool:
        """Remove student from group"""
        relationship = self.db.query(StudentGroup).filter(
            and_(
                StudentGroup.user_id == user_id,
                StudentGroup.group_id == group_id,
                StudentGroup.is_active == True
            )
        ).first()

        if relationship:
            relationship.is_active = False
            self._commit()
            return True
        return False

    def add_students_to_group(self, user_ids: List[int], group_id: int) -> int:
        """Add multiple students to group"""
        added_count = 0
        for user_id in user_ids:
            if self.add_student_to_group(user_id, group_id):
                added_count += 1
        return added_count

    def transfer_student(self, user_id: int, from_group_id: int, to_group_id: int) -> bool:
        """Transfer student between groups"""
        # Remove from old group
        if not self.remove_student_from_group(user_id, from_group_id):
            return False

        # Add to new group
        return self.add_student_to_group(user_id, to_group_id)

    def get_group_students(self, group_id: int) -> List[User]:
        """Get all students in a group"""
        return self.db.query(User).join(StudentGroup).filter(
            and_(
                StudentGroup.group_id == group_id,
                StudentGroup.is_active == True,
                User.is_active == True
            )
        ).order_by(asc(User.full_name)).all()

    def get_student_groups(self, user_id: int) -> List[Group]:
        """Get all groups a student belongs to"""
        return self.db.query(Group).join(StudentGroup).filter(
            and_(
                StudentGroup.user_id == user_id,
                StudentGroup.is_active == True,
                Group.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    # Teacher management methods
    def assign_teacher(self, group_id: int, teacher_id: int) -> Optional[Group]:
        """Assign teacher to group"""
        group = self.get(group_id)
        if group:
            group.teacher_id = teacher_id
            self._commit()
            self.db.refresh(group)
        return group

    def remove_teacher(self, group_id: int) -> Optional[Group]:
        """Remove teacher from group"""
        group = self.get(group_id)
        if group:
            group.teacher_id = None
            self._commit()
            self.db.refresh(group)
        return group

    def get_groups_needing_teacher(self, learning_center_id: int) -> List[Group]:
        """Get groups without assigned teacher"""
        from app.models.learning_center import Branch

        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.teacher_id.is_(None),
                Group.is_active == True,
                Branch.is_active == True
            )
        ).order_by(asc(Group.title)).all()

    # Group capacity and statistics
    def get_group_capacity_info(self, group_id: int) -> Dict[str, Any]:
        """Get group capacity information"""
        group = self.get(group_id)
        if not group:
            return {}

        current_students = self.db.query(StudentGroup).filter(
            and_(
                StudentGroup.group_id == group_id,
                StudentGroup.is_active == True
            )
        ).count()

        max_capacity = 25  # Default capacity, could be stored in group model

        return {
            "group_id": group_id,
            "current_students": current_students,
            "max_capacity": max_capacity,
            "available_spots": max(0, max_capacity - current_students),
            "is_full": current_students >= max_capacity,
            "capacity_percentage": round((current_students / max_capacity * 100), 1),
            "recommended_capacity": 20  # Recommended optimal size
        }

    def get_group_stats(self, group_id: int) -> Dict[str, Any]:
        """Get comprehensive group statistics"""
        group = self.get(group_id)
        if not group:
            return {}

        students = self.get_group_students(group_id)
        capacity_info = self.get_group_capacity_info(group_id)

        # Calculate activity stats (would need progress data)
        active_students_7d = len(students)  # Simplified - would need actual activity check

        return {
            "group_id": group_id,
            "title": group.title,
            "branch_id": group.branch_id,
            "course_id": group.course_id,
            "teacher_id": group.teacher_id,
            "total_students": len(students),
            "active_students_7d": active_students_7d,
            "has_teacher": group.teacher_id is not None,
            "has_course": group.course_id is not None,
            **capacity_info
        }

    def get_branch_group_stats(self, branch_id: int) -> Dict[str, Any]:
        """Get statistics for all groups in branch"""
        groups = self.get_by_branch(branch_id)

        total_students = 0
        groups_with_teachers = 0
        groups_with_courses = 0

        for group in groups:
            students_count = self.db.query(StudentGroup).filter(
                and_(
                    StudentGroup.group_id == group.id,
                    StudentGroup.is_active == True
                )
            ).count()

            total_students += students_count

            if group.teacher_id:
                groups_with_teachers += 1
            if group.course_id:
                groups_with_courses += 1

        return {
            "branch_id": branch_id,
            "total_groups": len(groups),
            "active_groups": len([g for g in groups if g.is_active]),
            "total_students": total_students,
            "groups_with_teachers": groups_with_teachers,
            "groups_with_courses": groups_with_courses,
            "average_students_per_group": total_students / len(groups) if groups else 0,
            "teacher_assignment_rate": (groups_with_teachers / len(groups) * 100) if groups else 0,
            "course_assignment_rate": (groups_with_courses / len(groups) * 100) if groups else 0
        }

    # Advanced queries
    def get_groups_by_criteria(self, learning_center_id: int, **filters) -> List[Group]:
        """Get groups by various criteria"""
        from app.models.learning_center import Branch

        query = self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.is_active == True,
                Branch.is_active == True
            )
        )

        # Apply filters
        if filters.get("branch_id"):
            query = query.filter(Group.branch_id == filters["branch_id"])

        if filters.get("teacher_id"):
            query = query.filter(Group.teacher_id == filters["teacher_id"])

        if filters.get("course_id"):
            query = query.filter(Group.course_id == filters["course_id"])

        if filters.get("has_teacher") is not None:
            if filters["has_teacher"]:
                query = query.filter(Group.teacher_id.isnot(None))
            else:
                query = query.filter(Group.teacher_id.is_(None))

        if filters.get("has_course") is not None:
            if filters["has_course"]:
                query = query.filter(Group.course_id.isnot(None))
            else:
                query = query.filter(Group.course_id.is_(None))

        return query.order_by(asc(Group.title)).all()

    def get_available_groups_for_student(self, user_id: int, learning_center_id: int) -> List[Group]:
        """Get groups available for student enrollment"""
        # Get groups student is not already in
        current_group_ids = self.db.query(StudentGroup.group_id).filter(
            and_(
                StudentGroup.user_id == user_id,
                StudentGroup.is_active == True
            )
        ).subquery()

        from app.models.learning_center import Branch

        return self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.is_active == True,
                Branch.is_active == True,
                ~Group.id.in_(current_group_ids)
            )
        ).order_by(asc(Group.title)).all()

    def get_groups_by_teacher_availability(self, learning_center_id: int, has_teacher: bool = False) -> List[Group]:
        """Get groups based on teacher assignment status"""
        from app.models.learning_center import Branch

        query = self.db.query(Group).join(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Group.is_active == True,
                Branch.is_active == True
            )
        )

        if has_teacher:
            query = query.filter(Group.teacher_id.isnot(None))
        else:
            query = query.filter(Group.teacher_id.is_(None))

        return query.order_by(asc(Group.title)).all()

    def bulk_assign_course(self, group_ids: List[int], course_id: int) -> int:
        """Bulk assign course to multiple groups"""
        updated_count = 0
        for group_id in group_ids:
            if self.update(group_id, {"course_id": course_id}):
                updated_count += 1
        return updated_count

    def bulk_assign_teacher(self, group_ids: List[int], teacher_id: int) -> int:
        """Bulk assign teacher to multiple groups"""
        updated_count = 0
        for group_id in group_ids:
            if self.update(group_id, {"teacher_id": teacher_id}):
                updated_count += 1
        return updated_count

    def get_student_count_by_group(self, group_ids: List[int]) -> Dict[int, int]:
        """Get student count for multiple groups"""
        results = self.db.query(
            StudentGroup.group_id,
            func.count(StudentGroup.user_id).label('student_count')
        ).filter(
            and_(
                StudentGroup.group_id.in_(group_ids),
                StudentGroup.is_active == True
            )
        ).group_by(StudentGroup.group_id).all()

        return {group_id: count for group_id, count in results}

    def cleanup_inactive_memberships(self) -> int:
        """Clean up old inactive student-group relationships"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=90)

        inactive_memberships = self.db.query(StudentGroup).filter(
            and_(
                StudentGroup.is_active == False,
                StudentGroup.updated_at < cutoff_date
            )
        ).all()

        for membership in inactive_memberships:
            self.db.delete(membership)

        self._commit()
        return len(inactive_memberships)