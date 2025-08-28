from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, date, timedelta
from app.models.learning_center import LearningCenter
from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent
from app.models.course import Course
from app.models.group import Group
from app.repositories.base_repository import BaseRepository
from app.constants.roles import UserRole


class LearningCenterRepository(BaseRepository[LearningCenter]):
    def __init__(self):
        super().__init__(LearningCenter)

    def get_by_location(self, db: Session, location: str, active_only: bool = True) -> List[LearningCenter]:
        """Get learning centers by location (country code)"""
        query = db.query(LearningCenter).filter(LearningCenter.location == location)

        if active_only:
            query = query.filter(LearningCenter.is_active == True)

        return query.order_by(LearningCenter.name).all()

    def search_centers(
            self,
            db: Session,
            search_term: str,
            location: Optional[str] = None,
            active_only: bool = True
    ) -> List[LearningCenter]:
        """Search learning centers by name or address"""
        query = db.query(LearningCenter).filter(
            or_(
                LearningCenter.name.ilike(f"%{search_term}%"),
                LearningCenter.address.ilike(f"%{search_term}%")
            )
        )

        if location:
            query = query.filter(LearningCenter.location == location)

        if active_only:
            query = query.filter(LearningCenter.is_active == True)

        return query.order_by(LearningCenter.name).all()

    def get_with_statistics(self, db: Session, center_id: int) -> Optional[Dict[str, Any]]:
        """Get learning center with comprehensive statistics"""
        center = self.get(db, center_id)
        if not center:
            return None

        # Get user counts
        total_users = db.query(User).filter(User.learning_center_id == center_id).count()
        active_users = db.query(User).filter(
            and_(User.learning_center_id == center_id, User.is_active == True)
        ).count()

        # Count by role
        role_counts = db.query(User.role, func.count(User.id)).filter(
            User.learning_center_id == center_id
        ).group_by(User.role).all()

        role_distribution = {role: count for role, count in role_counts}

        # Get student-specific counts
        students = db.query(Student).join(User).filter(
            User.learning_center_id == center_id
        )
        total_students = students.count()
        active_students = students.filter(User.is_active == True).count()

        # Get parent counts
        parents = db.query(Parent).join(User).filter(
            User.learning_center_id == center_id
        )
        total_parents = parents.count()
        active_parents = parents.filter(User.is_active == True).count()

        # Get course and group counts
        total_courses = db.query(Course).filter(Course.learning_center_id == center_id).count()
        active_courses = db.query(Course).filter(
            and_(Course.learning_center_id == center_id, Course.is_active == True)
        ).count()

        total_groups = db.query(Group).filter(Group.learning_center_id == center_id).count()
        active_groups = db.query(Group).filter(
            and_(Group.learning_center_id == center_id, Group.is_active == True)
        ).count()

        return {
            "center": center,
            "statistics": {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "inactive": total_users - active_users,
                    "role_distribution": role_distribution
                },
                "students": {
                    "total": total_students,
                    "active": active_students,
                    "inactive": total_students - active_students
                },
                "parents": {
                    "total": total_parents,
                    "active": active_parents,
                    "inactive": total_parents - active_parents
                },
                "courses": {
                    "total": total_courses,
                    "active": active_courses,
                    "inactive": total_courses - active_courses
                },
                "groups": {
                    "total": total_groups,
                    "active": active_groups,
                    "inactive": total_groups - active_groups
                }
            }
        }

    def get_ceo(self, db: Session, center_id: int) -> Optional[User]:
        """Get the CEO user for a learning center"""
        return db.query(User).filter(
            and_(
                User.learning_center_id == center_id,
                User.role == UserRole.CEO,
                User.is_active == True
            )
        ).first()

    def assign_ceo(self, db: Session, center_id: int, user_id: int) -> bool:
        """Assign a CEO to a learning center"""
        # Verify learning center exists
        center = self.get(db, center_id)
        if not center:
            return False

        # Verify user exists and update their learning center and role
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Remove any existing CEO for this center
        db.query(User).filter(
            and_(
                User.learning_center_id == center_id,
                User.role == UserRole.CEO
            )
        ).update({"role": UserRole.RECEPTION})  # Demote to reception or another role

        # Assign new CEO
        user.learning_center_id = center_id
        user.role = UserRole.CEO

        db.commit()
        return True

    def get_staff_members(self, db: Session, center_id: int, active_only: bool = True) -> List[User]:
        """Get all staff members for a learning center"""
        staff_roles = [UserRole.CEO, UserRole.RECEPTION, UserRole.CONTENT_MANAGER, UserRole.GROUP_MANAGER]

        query = db.query(User).filter(
            and_(
                User.learning_center_id == center_id,
                User.role.in_(staff_roles)
            )
        )

        if active_only:
            query = query.filter(User.is_active == True)

        return query.order_by(User.role, User.full_name).all()

    def get_activity_summary(
            self,
            db: Session,
            center_id: int,
            days: int = 30
    ) -> Dict[str, Any]:
        """Get activity summary for a learning center"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # This would typically join with progress/activity tables
        # For now, providing basic user activity

        # New users in period
        new_users = db.query(User).filter(
            and_(
                User.learning_center_id == center_id,
                func.date(User.created_at) >= start_date,
                func.date(User.created_at) <= end_date
            )
        ).count()

        # New students in period
        new_students = db.query(Student).join(User).filter(
            and_(
                User.learning_center_id == center_id,
                func.date(Student.created_at) >= start_date,
                func.date(Student.created_at) <= end_date
            )
        ).count()

        # Active users (users created or updated recently)
        recently_active_users = db.query(User).filter(
            and_(
                User.learning_center_id == center_id,
                or_(
                    func.date(User.created_at) >= start_date,
                    func.date(User.updated_at) >= start_date
                )
            )
        ).count()

        return {
            "center_id": center_id,
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "activity": {
                "new_users": new_users,
                "new_students": new_students,
                "recently_active_users": recently_active_users
            }
        }

    def get_performance_metrics(
            self,
            db: Session,
            center_id: int,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get performance metrics for a learning center"""
        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today()

        # Get basic counts
        total_students = db.query(Student).join(User).filter(
            and_(
                User.learning_center_id == center_id,
                User.is_active == True
            )
        ).count()

        total_groups = db.query(Group).filter(
            and_(
                Group.learning_center_id == center_id,
                Group.is_active == True
            )
        ).count()

        total_courses = db.query(Course).filter(
            and_(
                Course.learning_center_id == center_id,
                Course.is_active == True
            )
        ).count()

        # Calculate group utilization
        group_capacity_data = db.query(
            func.sum(Group.max_capacity).label('total_capacity'),
            func.count(Student.id).label('enrolled_students')
        ).select_from(Group).outerjoin(Group.students).filter(
            and_(
                Group.learning_center_id == center_id,
                Group.is_active == True
            )
        ).first()

        total_capacity = group_capacity_data.total_capacity or 0
        enrolled_students = group_capacity_data.enrolled_students or 0

        utilization_rate = (enrolled_students / total_capacity * 100) if total_capacity > 0 else 0

        # Student distribution by proficiency level
        proficiency_distribution = db.query(
            Student.proficiency_level,
            func.count(Student.id).label('count')
        ).join(User).filter(
            and_(
                User.learning_center_id == center_id,
                User.is_active == True
            )
        ).group_by(Student.proficiency_level).all()

        return {
            "center_id": center_id,
            "period": {
                "date_from": date_from,
                "date_to": date_to
            },
            "metrics": {
                "total_students": total_students,
                "total_groups": total_groups,
                "total_courses": total_courses,
                "group_utilization": {
                    "total_capacity": total_capacity,
                    "enrolled_students": enrolled_students,
                    "utilization_rate": round(utilization_rate, 2)
                },
                "student_distribution": {
                    level: count for level, count in proficiency_distribution
                }
            }
        }

    def get_centers_comparison(self, db: Session, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get comparison metrics across all learning centers"""
        query = db.query(LearningCenter)

        if active_only:
            query = query.filter(LearningCenter.is_active == True)

        centers = query.all()

        comparison_data = []

        for center in centers:
            # Get basic stats
            total_users = db.query(User).filter(User.learning_center_id == center.id).count()
            total_students = db.query(Student).join(User).filter(
                User.learning_center_id == center.id
            ).count()
            total_courses = db.query(Course).filter(Course.learning_center_id == center.id).count()
            total_groups = db.query(Group).filter(Group.learning_center_id == center.id).count()

            comparison_data.append({
                "center_id": center.id,
                "center_name": center.name,
                "location": center.location,
                "is_active": center.is_active,
                "created_at": center.created_at,
                "metrics": {
                    "total_users": total_users,
                    "total_students": total_students,
                    "total_courses": total_courses,
                    "total_groups": total_groups
                }
            })

        return sorted(comparison_data, key=lambda x: x["metrics"]["total_students"], reverse=True)

    def update_settings(
            self,
            db: Session,
            center_id: int,
            settings: Dict[str, Any]
    ) -> Optional[LearningCenter]:
        """Update learning center settings"""
        center = self.get(db, center_id)
        if not center:
            return None

        # Update allowed fields
        allowed_fields = [
            'name', 'location', 'timezone', 'phone_number',
            'address', 'leaderboard_reset_time'
        ]

        for field, value in settings.items():
            if field in allowed_fields and hasattr(center, field):
                setattr(center, field, value)

        db.commit()
        db.refresh(center)
        return center

    def deactivate_center(self, db: Session, center_id: int) -> bool:
        """Deactivate a learning center and all its related entities"""
        center = self.get(db, center_id)
        if not center:
            return False

        try:
            # Deactivate center
            center.is_active = False

            # Deactivate all users in the center
            db.query(User).filter(User.learning_center_id == center_id).update(
                {"is_active": False}
            )

            # Deactivate all courses
            db.query(Course).filter(Course.learning_center_id == center_id).update(
                {"is_active": False}
            )

            # Deactivate all groups
            db.query(Group).filter(Group.learning_center_id == center_id).update(
                {"is_active": False}
            )

            db.commit()
            return True

        except Exception:
            db.rollback()
            return False

    def get_timezone_groups(self, db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Group learning centers by timezone for scheduling purposes"""
        centers = db.query(LearningCenter).filter(LearningCenter.is_active == True).all()

        timezone_groups = {}
        for center in centers:
            timezone = center.timezone
            if timezone not in timezone_groups:
                timezone_groups[timezone] = []

            timezone_groups[timezone].append({
                "center_id": center.id,
                "center_name": center.name,
                "location": center.location,
                "leaderboard_reset_time": center.leaderboard_reset_time
            })

        return timezone_groups