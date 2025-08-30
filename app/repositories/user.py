from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from app.models.user import User, UserCenterRole, StudentGroup, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """User repository with authentication and role management"""

    def __init__(self, db: Session):
        super().__init__(db, User)

    # Authentication methods
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        return self.db.query(User).filter(
            and_(User.telegram_id == telegram_id, User.is_active == True)
        ).first()

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        return self.db.query(User).filter(
            and_(User.phone_number == phone_number, User.is_active == True)
        ).first()

    def get_by_phone_and_center(self, phone_number: str, learning_center_id: int) -> Optional[User]:
        """Get user by phone and learning center (for login)"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                User.phone_number == phone_number,
                User.is_active == True,
                UserCenterRole.learning_center_id == learning_center_id,
                UserCenterRole.is_active == True
            )
        ).first()

    def telegram_id_exists(self, telegram_id: int) -> bool:
        """Check if Telegram ID already exists"""
        return self.db.query(User).filter(
            and_(User.telegram_id == telegram_id, User.is_active == True)
        ).first() is not None

    def phone_exists_in_center(self, phone_number: str, learning_center_id: int) -> bool:
        """Check if phone exists in specific learning center"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                User.phone_number == phone_number,
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                UserCenterRole.is_active == True
            )
        ).first() is not None

    def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        user = self.get(user_id)
        if user:
            user.is_verified = True
            self.db.commit()
            self.db.refresh(user)
        return user

    # Role management methods
    def create_user_with_role(self, user_data: Dict[str, Any], learning_center_id: int, role: str) -> User:
        """Create user with initial role in learning center"""
        # Create user
        user = self.create(user_data)

        # Create role relationship
        user_role = UserCenterRole(
            user_id=user.id,
            learning_center_id=learning_center_id,
            role=role,
            is_active=True
        )
        self.db.add(user_role)
        self.db.commit()

        # Refresh to get relationships
        self.db.refresh(user)
        return user

    def change_role(self, user_id: int, new_role: str) -> Optional[User]:
        """Change user's role (assumes single center for now)"""
        user = self.get(user_id)
        if user and user.center_roles:
            # Update the first active role
            active_role = next((r for r in user.center_roles if r.is_active), None)
            if active_role:
                active_role.role = new_role
                self.db.commit()
                self.db.refresh(user)
        return user

    def add_role_in_center(self, user_id: int, learning_center_id: int, role: str) -> bool:
        """Add role for user in specific learning center"""
        # Check if role already exists
        existing = self.db.query(UserCenterRole).filter(
            and_(
                UserCenterRole.user_id == user_id,
                UserCenterRole.learning_center_id == learning_center_id,
                UserCenterRole.is_active == True
            )
        ).first()

        if existing:
            # Update existing role
            existing.role = role
        else:
            # Create new role
            new_role = UserCenterRole(
                user_id=user_id,
                learning_center_id=learning_center_id,
                role=role,
                is_active=True
            )
            self.db.add(new_role)

        self.db.commit()
        return True

    def remove_role_in_center(self, user_id: int, learning_center_id: int) -> bool:
        """Remove user's role in specific learning center"""
        role = self.db.query(UserCenterRole).filter(
            and_(
                UserCenterRole.user_id == user_id,
                UserCenterRole.learning_center_id == learning_center_id,
                UserCenterRole.is_active == True
            )
        ).first()

        if role:
            role.is_active = False
            self.db.commit()
            return True
        return False

    # Query methods
    def get_users_by_center(self, learning_center_id: int) -> List[User]:
        """Get all users in learning center"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                UserCenterRole.is_active == True
            )
        ).options(joinedload(User.center_roles)).all()

    def get_users_by_role(self, role: str, learning_center_id: int) -> List[User]:
        """Get users by role in learning center"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                UserCenterRole.role == role,
                User.is_active == True,
                UserCenterRole.is_active == True
            )
        ).all()

    def get_active_users_by_center(self, learning_center_id: int) -> List[User]:
        """Get all active users in learning center"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                User.is_verified == True,
                UserCenterRole.is_active == True
            )
        ).all()

    def search_users(self, learning_center_id: int, query: str) -> List[User]:
        """Search users by name or phone in learning center"""
        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                UserCenterRole.is_active == True,
                or_(
                    User.full_name.ilike(f"%{query}%"),
                    User.phone_number.ilike(f"%{query}%")
                )
            )
        ).limit(50).all()

    # Student-specific methods
    def get_students_by_center(self, learning_center_id: int) -> List[User]:
        """Get all students in learning center"""
        return self.get_users_by_role(UserRole.STUDENT, learning_center_id)

    def get_teachers_by_center(self, learning_center_id: int) -> List[User]:
        """Get all teachers in learning center"""
        return self.get_users_by_role(UserRole.TEACHER, learning_center_id)

    def get_unassigned_students(self, learning_center_id: int) -> List[User]:
        """Get students not assigned to any group"""
        return self.db.query(User).join(UserCenterRole).outerjoin(StudentGroup).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                UserCenterRole.role == UserRole.STUDENT,
                User.is_active == True,
                UserCenterRole.is_active == True,
                StudentGroup.id == None  # Not in any group
            )
        ).all()

    # Statistics methods
    def get_user_stats_summary(self, learning_center_id: int) -> Dict[str, int]:
        """Get user statistics for learning center"""
        stats = {}

        # Total users
        stats['total_users'] = self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                UserCenterRole.is_active == True
            )
        ).count()

        # Active verified users
        stats['active_users'] = self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                User.is_verified == True,
                UserCenterRole.is_active == True
            )
        ).count()

        # Users by role
        for role in UserRole:
            stats[f'{role.value}_count'] = self.get_users_by_role(role.value, learning_center_id).__len__()

        return stats

    def get_recent_registrations(self, learning_center_id: int, days: int = 7) -> List[User]:
        """Get recently registered users"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return self.db.query(User).join(UserCenterRole).filter(
            and_(
                UserCenterRole.learning_center_id == learning_center_id,
                User.is_active == True,
                User.created_at >= cutoff_date,
                UserCenterRole.is_active == True
            )
        ).order_by(desc(User.created_at)).all()

    # User management methods
    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate user"""
        return self.soft_delete(user_id)

    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user"""
        return self.activate(user_id)

    def link_telegram(self, user_id: int, telegram_id: int) -> Optional[User]:
        """Link Telegram ID to user"""
        user = self.get(user_id)
        if user:
            user.telegram_id = telegram_id
            self.db.commit()
            self.db.refresh(user)
        return user

    def unlink_telegram(self, user_id: int) -> Optional[User]:
        """Remove Telegram link from user"""
        user = self.get(user_id)
        if user:
            user.telegram_id = None
            self.db.commit()
            self.db.refresh(user)
        return user

    # Parent-child relationship methods (if needed)
    def get_parent_children(self, parent_id: int) -> List[User]:
        """Get children of a parent user (would need separate table for this)"""
        # This would need a parent_child relationship table
        # For now, return empty list
        return []

    def get_child_parents(self, child_id: int) -> List[User]:
        """Get parents of a child user"""
        # This would need a parent_child relationship table
        # For now, return empty list
        return []


class UserCenterRoleRepository(BaseRepository):
    """Repository for user-center role relationships"""

    def __init__(self, db: Session):
        super().__init__(db, UserCenterRole)

    def get_user_roles(self, user_id: int) -> List[UserCenterRole]:
        """Get all roles for a user"""
        return self.filter_by(user_id=user_id)

    def get_center_users(self, learning_center_id: int) -> List[UserCenterRole]:
        """Get all user roles in a center"""
        return self.filter_by(learning_center_id=learning_center_id)

    def get_role_by_user_center(self, user_id: int, learning_center_id: int) -> Optional[UserCenterRole]:
        """Get specific user role in center"""
        return self.get_by_fields(user_id=user_id, learning_center_id=learning_center_id)


class StudentGroupRepository(BaseRepository):
    """Repository for student-group relationships"""

    def __init__(self, db: Session):
        super().__init__(db, StudentGroup)

    def add_student_to_group(self, user_id: int, group_id: int) -> bool:
        """Add student to group"""
        # Check if already exists
        existing = self.get_by_fields(user_id=user_id, group_id=group_id)
        if existing:
            return False

        # Create new relationship
        self.create({"user_id": user_id, "group_id": group_id})
        return True

    def remove_student_from_group(self, user_id: int, group_id: int) -> bool:
        """Remove student from group"""
        relationship = self.get_by_fields(user_id=user_id, group_id=group_id)
        if relationship:
            self.soft_delete(relationship.id)
            return True
        return False

    def get_student_groups(self, user_id: int) -> List[StudentGroup]:
        """Get all groups for a student"""
        return self.filter_by(user_id=user_id)

    def get_group_students(self, group_id: int) -> List[StudentGroup]:
        """Get all students in a group"""
        return self.filter_by(group_id=group_id)

    def transfer_student(self, user_id: int, from_group_id: int, to_group_id: int) -> bool:
        """Transfer student between groups"""
        # Remove from old group
        if not self.remove_student_from_group(user_id, from_group_id):
            return False

        # Add to new group
        return self.add_student_to_group(user_id, to_group_id)