from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import date
from app.models.teacher import Teacher
from app.models.user import User
from app.models.group import Group
from app.repositories.base_repository import BaseRepository
from app.constants.roles import UserRole


class TeacherRepository(BaseRepository[Teacher]):
    def __init__(self):
        super().__init__(Teacher)

    def create_with_user(self, db: Session, user_data: dict, teacher_data: dict) -> Teacher:
        """Create teacher with associated user"""
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository()

        # Ensure user has GROUP_MANAGER role
        user_data["role"] = UserRole.GROUP_MANAGER

        # Create user first
        user = user_repo.create(db, user_data)

        # Create teacher profile
        teacher_data["user_id"] = user.id
        return self.create(db, teacher_data)

    def get_by_user_id(self, db: Session, user_id: int) -> Optional[Teacher]:
        """Get teacher by user ID"""
        return db.query(Teacher).filter(Teacher.user_id == user_id).first()

    def get_with_user(self, db: Session, teacher_id: int) -> Optional[Teacher]:
        """Get teacher with user information loaded"""
        return db.query(Teacher).options(joinedload(Teacher.user)).filter(Teacher.id == teacher_id).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Teacher]:
        """Get teachers by learning center"""
        query = db.query(Teacher).join(User).filter(
            User.learning_center_id == learning_center_id
        )

        if active_only:
            query = query.filter(User.is_active == True)

        return query.options(joinedload(Teacher.user)).all()

    def get_by_subject_specialization(self, db: Session, subject: str, learning_center_id: Optional[int] = None) -> \
    List[Teacher]:
        """Get teachers by subject specialization"""
        query = db.query(Teacher).filter(Teacher.subject_specialization.ilike(f"%{subject}%"))

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Teacher.user)).all()

    def get_by_employment_type(self, db: Session, employment_type: str, learning_center_id: Optional[int] = None) -> \
    List[Teacher]:
        """Get teachers by employment type"""
        query = db.query(Teacher).filter(Teacher.employment_type == employment_type)

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Teacher.user)).all()

    def get_by_experience_range(self, db: Session, min_years: int, max_years: int,
                                learning_center_id: Optional[int] = None) -> List[Teacher]:
        """Get teachers by experience range"""
        query = db.query(Teacher).filter(
            and_(
                Teacher.teaching_experience_years >= min_years,
                Teacher.teaching_experience_years <= max_years
            )
        )

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Teacher.user)).all()

    def get_available_teachers(self, db: Session, learning_center_id: int) -> List[Teacher]:
        """Get teachers who don't have any active groups or have capacity for more"""
        # Get all teachers in learning center
        all_teachers = self.get_by_learning_center(db, learning_center_id)

        # Filter teachers with no groups or those who could handle more
        available_teachers = []
        for teacher in all_teachers:
            active_groups = len([g for g in teacher.groups if g.is_active])
            # Assuming a teacher can handle up to 5 active groups (configurable)
            if active_groups < 5:
                available_teachers.append(teacher)

        return available_teachers

    def get_teachers_without_groups(self, db: Session, learning_center_id: Optional[int] = None) -> List[Teacher]:
        """Get teachers who don't have any groups assigned"""
        query = db.query(Teacher).filter(~Teacher.groups.any())

        if learning_center_id:
            query = query.join(User).filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Teacher.user)).all()

    def get_top_teachers_by_groups(self, db: Session, learning_center_id: Optional[int] = None, limit: int = 10) -> \
    List[dict]:
        """Get teachers with most active groups"""
        query = db.query(
            Teacher.id,
            Teacher.user_id,
            User.full_name,
            Teacher.subject_specialization,
            func.count(Group.id).label('active_groups_count')
        ).join(User).outerjoin(Group).filter(
            and_(Group.is_active == True) if Group else True
        )

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        results = query.group_by(
            Teacher.id, Teacher.user_id, User.full_name, Teacher.subject_specialization
        ).order_by(desc('active_groups_count')).limit(limit).all()

        return [
            {
                "teacher_id": teacher_id,
                "user_id": user_id,
                "full_name": full_name,
                "subject_specialization": subject_specialization,
                "active_groups_count": active_groups_count
            }
            for teacher_id, user_id, full_name, subject_specialization, active_groups_count in results
        ]

    def search_teachers(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            subject: Optional[str] = None,
            employment_type: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Teacher]:
        """Search teachers by name, subject, or qualification"""
        query = db.query(Teacher).join(User).filter(
            or_(
                User.full_name.ilike(f"%{search_term}%"),
                Teacher.subject_specialization.ilike(f"%{search_term}%"),
                Teacher.qualification.ilike(f"%{search_term}%"),
                User.phone_number.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        if subject:
            query = query.filter(Teacher.subject_specialization.ilike(f"%{subject}%"))

        if employment_type:
            query = query.filter(Teacher.employment_type == employment_type)

        return query.options(joinedload(Teacher.user)).offset(skip).limit(limit).all()

    def get_active_teachers(self, db: Session, learning_center_id: Optional[int] = None) -> List[Teacher]:
        """Get all active teachers"""
        query = db.query(Teacher).join(User).filter(User.is_active == True)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.options(joinedload(Teacher.user)).all()

    def assign_to_group(self, db: Session, teacher_id: int, group_id: int) -> bool:
        """Assign teacher to a group"""
        teacher = self.get(db, teacher_id)
        group = db.query(Group).filter(Group.id == group_id).first()

        if teacher and group:
            group.teacher_id = teacher_id
            db.commit()
            return True
        return False

    def unassign_from_group(self, db: Session, group_id: int) -> bool:
        """Remove teacher assignment from a group"""
        group = db.query(Group).filter(Group.id == group_id).first()

        if group:
            group.teacher_id = None
            db.commit()
            return True
        return False

    def update_experience(self, db: Session, teacher_id: int, years: int) -> Optional[Teacher]:
        """Update teacher's experience years"""
        teacher = self.get(db, teacher_id)
        if teacher:
            teacher.teaching_experience_years = years
            db.commit()
            db.refresh(teacher)
        return teacher

    def get_teacher_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive teacher statistics"""
        base_query = db.query(Teacher).join(User)

        if learning_center_id:
            base_query = base_query.filter(User.learning_center_id == learning_center_id)

        total_teachers = base_query.count()
        active_teachers = base_query.filter(User.is_active == True).count()

        # Count by employment type
        employment_counts = base_query.with_entities(
            Teacher.employment_type, func.count(Teacher.id)
        ).group_by(Teacher.employment_type).all()

        # Count by subject specialization
        subject_counts = base_query.filter(Teacher.subject_specialization.isnot(None)).with_entities(
            Teacher.subject_specialization, func.count(Teacher.id)
        ).group_by(Teacher.subject_specialization).all()

        # Average experience
        avg_experience = base_query.with_entities(
            func.avg(Teacher.teaching_experience_years)
        ).scalar() or 0.0

        # Teachers with/without groups
        teachers_with_groups = base_query.filter(Teacher.groups.any()).count()
        teachers_without_groups = total_teachers - teachers_with_groups

        # Experience distribution
        experience_ranges = [
            ("New (0 years)", base_query.filter(Teacher.teaching_experience_years == 0).count()),
            ("Junior (1-2 years)", base_query.filter(
                and_(Teacher.teaching_experience_years >= 1, Teacher.teaching_experience_years <= 2)).count()),
            ("Intermediate (3-5 years)", base_query.filter(
                and_(Teacher.teaching_experience_years >= 3, Teacher.teaching_experience_years <= 5)).count()),
            ("Senior (6-10 years)", base_query.filter(
                and_(Teacher.teaching_experience_years >= 6, Teacher.teaching_experience_years <= 10)).count()),
            ("Expert (10+ years)", base_query.filter(Teacher.teaching_experience_years > 10).count())
        ]

        return {
            "total_teachers": total_teachers,
            "active_teachers": active_teachers,
            "inactive_teachers": total_teachers - active_teachers,
            "average_experience_years": round(float(avg_experience), 1),
            "employment_distribution": {emp_type or "unspecified": count for emp_type, count in employment_counts},
            "subject_distribution": {subject or "unspecified": count for subject, count in subject_counts},
            "teachers_with_groups": teachers_with_groups,
            "teachers_without_groups": teachers_without_groups,
            "group_assignment_rate": (teachers_with_groups / total_teachers * 100) if total_teachers > 0 else 0,
            "experience_distribution": {level: count for level, count in experience_ranges}
        }