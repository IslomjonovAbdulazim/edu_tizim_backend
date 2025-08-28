from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.models.group import Group
from app.models.student import Student
from app.models.user import User
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class GroupRepository(BaseRepository[Group]):
    def __init__(self):
        super().__init__(Group)

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Group]:
        """Get groups by learning center"""
        query = db.query(Group).filter(Group.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(Group.is_active == True)

        return query.options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def get_by_course(self, db: Session, course_id: int, active_only: bool = True) -> List[Group]:
        """Get groups by course"""
        query = db.query(Group).filter(Group.course_id == course_id)

        if active_only:
            query = query.filter(Group.is_active == True)

        return query.options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def get_by_manager(self, db: Session, manager_id: int, active_only: bool = True) -> List[Group]:
        """Get groups managed by a specific manager"""
        query = db.query(Group).filter(Group.manager_id == manager_id)

        if active_only:
            query = query.filter(Group.is_active == True)

        return query.options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def get_with_capacity(self, db: Session, learning_center_id: Optional[int] = None) -> List[Group]:
        """Get groups that have available capacity"""
        query = db.query(Group).filter(Group.is_active == True)

        if learning_center_id:
            query = query.filter(Group.learning_center_id == learning_center_id)

        # Add subquery to count current students
        subquery = db.query(
            Group.id.label('group_id'),
            func.count(Student.id).label('student_count')
        ).outerjoin(Group.students).group_by(Group.id).subquery()

        query = query.join(subquery, Group.id == subquery.c.group_id).filter(
            subquery.c.student_count < Group.max_capacity
        )

        return query.options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def get_full_groups(self, db: Session, learning_center_id: Optional[int] = None) -> List[Group]:
        """Get groups that are at full capacity"""
        query = db.query(Group).filter(Group.is_active == True)

        if learning_center_id:
            query = query.filter(Group.learning_center_id == learning_center_id)

        # Add subquery to count current students
        subquery = db.query(
            Group.id.label('group_id'),
            func.count(Student.id).label('student_count')
        ).join(Group.students).group_by(Group.id).subquery()

        query = query.join(subquery, Group.id == subquery.c.group_id).filter(
            subquery.c.student_count >= Group.max_capacity
        )

        return query.options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def get_student_groups(self, db: Session, student_id: int) -> List[Group]:
        """Get all groups a student belongs to"""
        return db.query(Group).join(Group.students).filter(
            Student.id == student_id
        ).options(
            joinedload(Group.course),
            joinedload(Group.manager)
        ).all()

    def add_student_to_group(self, db: Session, group_id: int, student_id: int) -> bool:
        """Add a student to a group"""
        group = self.get(db, group_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if not group or not student:
            return False

        # Check if group has capacity
        if group.current_capacity >= group.max_capacity:
            return False

        # Check if student is already in the group
        if student in group.students:
            return False

        group.students.append(student)
        db.commit()
        return True

    def remove_student_from_group(self, db: Session, group_id: int, student_id: int) -> bool:
        """Remove a student from a group"""
        group = self.get(db, group_id)
        student = db.query(Student).filter(Student.id == student_id).first()

        if not group or not student:
            return False

        if student not in group.students:
            return False

        group.students.remove(student)
        db.commit()
        return True

    def bulk_add_students(self, db: Session, group_id: int, student_ids: List[int]) -> dict:
        """Add multiple students to a group"""
        group = self.get(db, group_id)
        if not group:
            return {"success": False, "message": "Group not found", "added": 0, "failed": len(student_ids)}

        students = db.query(Student).filter(Student.id.in_(student_ids)).all()

        added_count = 0
        failed_count = 0

        for student in students:
            # Check capacity
            if group.current_capacity >= group.max_capacity:
                failed_count += 1
                continue

            # Check if already in group
            if student in group.students:
                failed_count += 1
                continue

            group.students.append(student)
            added_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Added {added_count} students, {failed_count} failed",
            "added": added_count,
            "failed": failed_count
        }

    def bulk_remove_students(self, db: Session, group_id: int, student_ids: List[int]) -> dict:
        """Remove multiple students from a group"""
        group = self.get(db, group_id)
        if not group:
            return {"success": False, "message": "Group not found", "removed": 0, "failed": len(student_ids)}

        students = db.query(Student).filter(Student.id.in_(student_ids)).all()

        removed_count = 0
        failed_count = 0

        for student in students:
            if student in group.students:
                group.students.remove(student)
                removed_count += 1
            else:
                failed_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Removed {removed_count} students, {failed_count} not found",
            "removed": removed_count,
            "failed": failed_count
        }

    def search_groups(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            course_id: Optional[int] = None,
            manager_id: Optional[int] = None,
            has_capacity: Optional[bool] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Group]:
        """Search groups by name or description"""
        query = db.query(Group).filter(
            or_(
                Group.name.ilike(f"%{search_term}%"),
                Group.description.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(Group.learning_center_id == learning_center_id)

        if course_id:
            query = query.filter(Group.course_id == course_id)

        if manager_id:
            query = query.filter(Group.manager_id == manager_id)

        if has_capacity is not None:
            if has_capacity:
                # Groups with available capacity
                subquery = db.query(
                    Group.id.label('group_id'),
                    func.count(Student.id).label('student_count')
                ).outerjoin(Group.students).group_by(Group.id).subquery()

                query = query.join(subquery, Group.id == subquery.c.group_id).filter(
                    subquery.c.student_count < Group.max_capacity
                )
            else:
                # Full groups
                subquery = db.query(
                    Group.id.label('group_id'),
                    func.count(Student.id).label('student_count')
                ).join(Group.students).group_by(Group.id).subquery()

                query = query.join(subquery, Group.id == subquery.c.group_id).filter(
                    subquery.c.student_count >= Group.max_capacity
                )

        return query.filter(Group.is_active == True).options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).offset(skip).limit(limit).all()

    def get_groups_by_schedule_day(self, db: Session, day: str, learning_center_id: Optional[int] = None) -> List[
        Group]:
        """Get groups that meet on a specific day"""
        query = db.query(Group).filter(Group.schedule_days.like(f"%{day}%"))

        if learning_center_id:
            query = query.filter(Group.learning_center_id == learning_center_id)

        return query.filter(Group.is_active == True).options(
            joinedload(Group.course),
            joinedload(Group.manager),
            joinedload(Group.students)
        ).all()

    def assign_manager(self, db: Session, group_id: int, manager_id: int) -> Optional[Group]:
        """Assign a manager to a group"""
        group = self.get(db, group_id)
        manager = db.query(User).filter(User.id == manager_id).first()

        if group and manager:
            group.manager_id = manager_id
            db.commit()
            db.refresh(group)

        return group

    def get_group_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive group statistics"""
        base_query = db.query(Group)

        if learning_center_id:
            base_query = base_query.filter(Group.learning_center_id == learning_center_id)

        total_groups = base_query.count()
        active_groups = base_query.filter(Group.is_active == True).count()

        # Groups with/without managers
        groups_with_managers = base_query.filter(Group.manager_id.isnot(None)).count()
        groups_without_managers = total_groups - groups_with_managers

        # Capacity statistics
        subquery = db.query(
            Group.id,
            Group.max_capacity,
            func.count(Student.id).label('current_capacity')
        ).outerjoin(Group.students).group_by(Group.id, Group.max_capacity).subquery()

        capacity_query = base_query.join(subquery, Group.id == subquery.c.id)

        full_groups = capacity_query.filter(
            subquery.c.current_capacity >= subquery.c.max_capacity
        ).count()

        total_capacity = base_query.with_entities(func.sum(Group.max_capacity)).scalar() or 0
        total_students = db.query(func.count(Student.id)).join(Group.students).scalar() or 0

        return {
            "total_groups": total_groups,
            "active_groups": active_groups,
            "inactive_groups": total_groups - active_groups,
            "groups_with_managers": groups_with_managers,
            "groups_without_managers": groups_without_managers,
            "full_groups": full_groups,
            "groups_with_capacity": active_groups - full_groups,
            "total_capacity": total_capacity,
            "total_enrolled_students": total_students,
            "capacity_utilization_rate": (total_students / total_capacity * 100) if total_capacity > 0 else 0
        }