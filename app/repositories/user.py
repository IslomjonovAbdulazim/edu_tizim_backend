from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.models import User, UserRole, UserCenterRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    # User Lookup Methods
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            return self.db.query(User).filter(
                and_(
                    User.telegram_id == telegram_id,
                    User.is_active == True
                )
            ).first()
        except Exception:
            return None

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        try:
            return self.db.query(User).filter(
                and_(
                    User.phone_number == phone_number,
                    User.is_active == True
                )
            ).first()
        except Exception:
            return None

    def get_by_phone_and_center(self, phone_number: str, learning_center_id: int) -> Optional[User]:
        """Get user by phone number within a specific learning center"""
        try:
            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    User.phone_number == phone_number,
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).first()
        except Exception:
            return None

    def get_with_roles(self, user_id: int) -> Optional[User]:
        """Get user with all center roles loaded"""
        try:
            return self.db.query(User).options(
                joinedload(User.center_roles).joinedload(UserCenterRole.learning_center)
            ).filter(
                and_(User.id == user_id, User.is_active == True)
            ).first()
        except Exception:
            return None

    # Role-based Queries
    def get_users_by_role(self, role: UserRole, learning_center_id: int) -> List[User]:
        """Get all users with specific role in learning center"""
        try:
            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.role == role,
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).all()
        except Exception:
            return []

    def get_users_by_center(self, learning_center_id: int, include_inactive: bool = False) -> List[User]:
        """Get all users in learning center"""
        try:
            query = self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    UserCenterRole.is_active == True
                )
            )

            if not include_inactive:
                query = query.filter(User.is_active == True)

            return query.order_by(User.full_name).all()
        except Exception:
            return []

    def get_active_users_by_center(self, learning_center_id: int) -> List[User]:
        """Get only active users in learning center"""
        return self.get_users_by_center(learning_center_id, include_inactive=False)

    def get_users_by_branch(self, branch_id: int) -> List[User]:
        """Get all users assigned to a specific branch"""
        try:
            # This would need to be implemented based on how you want to track branch assignments
            # For now, assuming UserCenterRole might have branch_id
            return self.db.query(User).filter(
                and_(
                    # User.branch_id == branch_id,  # If you add branch_id to User model
                    User.is_active == True
                )
            ).all()
        except Exception:
            return []

    # Search and Filter Methods
    def search_users(self, learning_center_id: int, query: str, limit: int = 50) -> List[User]:
        """Search users by name or phone within learning center"""
        try:
            if not query.strip():
                return []

            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    or_(
                        User.full_name.ilike(f"%{query}%"),
                        User.phone_number.ilike(f"%{query}%")
                    ),
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).limit(limit).all()
        except Exception:
            return []

    def get_users_with_filters(
            self,
            learning_center_id: int,
            role: Optional[UserRole] = None,
            is_verified: Optional[bool] = None,
            skip: int = 0,
            limit: int = 50
    ) -> List[User]:
        """Get users with various filters"""
        try:
            query = self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            )

            if role:
                query = query.filter(UserCenterRole.role == role)

            if is_verified is not None:
                query = query.filter(User.is_verified == is_verified)

            return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        except Exception:
            return []

    # Verification Methods
    def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        try:
            user = self.get(user_id)
            if user:
                user.is_verified = True
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            return None

    def unverify_user(self, user_id: int) -> Optional[User]:
        """Mark user as unverified"""
        try:
            user = self.get(user_id)
            if user:
                user.is_verified = False
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            return None

    # Account Management
    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user account"""
        return self.restore(user_id)

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account (soft delete)"""
        return self.delete(user_id, hard_delete=False)

    def link_telegram(self, user_id: int, telegram_id: int) -> Optional[User]:
        """Link Telegram ID to user account"""
        try:
            # Check if telegram_id is already used by another user
            existing_user = self.get_by_telegram_id(telegram_id)
            if existing_user and existing_user.id != user_id:
                return None  # Already linked to another user

            user = self.get(user_id)
            if user:
                user.telegram_id = telegram_id
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            return None

    def unlink_telegram(self, user_id: int) -> Optional[User]:
        """Remove Telegram link from user account"""
        try:
            user = self.get(user_id)
            if user:
                user.telegram_id = None
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            return None

    # Validation Methods
    def telegram_id_exists(self, telegram_id: int, exclude_user_id: Optional[int] = None) -> bool:
        """Check if Telegram ID is already in use"""
        try:
            query = self.db.query(User).filter(
                and_(
                    User.telegram_id == telegram_id,
                    User.is_active == True
                )
            )

            if exclude_user_id:
                query = query.filter(User.id != exclude_user_id)

            return query.first() is not None
        except Exception:
            return False

    def phone_exists(self, phone_number: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if phone number is already in use"""
        try:
            query = self.db.query(User).filter(
                and_(
                    User.phone_number == phone_number,
                    User.is_active == True
                )
            )

            if exclude_user_id:
                query = query.filter(User.id != exclude_user_id)

            return query.first() is not None
        except Exception:
            return False

    def phone_exists_in_center(self, phone_number: str, learning_center_id: int,
                               exclude_user_id: Optional[int] = None) -> bool:
        """Check if phone number exists in specific learning center"""
        try:
            query = self.db.query(User).join(UserCenterRole).filter(
                and_(
                    User.phone_number == phone_number,
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            )

            if exclude_user_id:
                query = query.filter(User.id != exclude_user_id)

            return query.first() is not None
        except Exception:
            return False

    # Statistics and Analytics
    def get_user_count_by_center(self, learning_center_id: int) -> int:
        """Get total user count for learning center"""
        try:
            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).count()
        except Exception:
            return 0

    def get_verified_user_count(self, learning_center_id: int) -> int:
        """Get verified user count for learning center"""
        try:
            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_verified == True,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).count()
        except Exception:
            return 0

    def get_role_distribution(self, learning_center_id: int) -> Dict[str, int]:
        """Get user count by role for learning center"""
        try:
            results = self.db.query(
                UserCenterRole.role,
                func.count(User.id)
            ).join(User).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).group_by(UserCenterRole.role).all()

            return {role: count for role, count in results}
        except Exception:
            return {}

    # Recent Activity
    def get_recently_created_users(self, learning_center_id: int, days: int = 7, limit: int = 10) -> List[User]:
        """Get recently created users"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.created_at >= cutoff_date,
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).order_by(User.created_at.desc()).limit(limit).all()
        except Exception:
            return []

    def get_recently_verified_users(self, learning_center_id: int, days: int = 7, limit: int = 10) -> List[User]:
        """Get recently verified users"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            return self.db.query(User).join(UserCenterRole).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    User.is_verified == True,
                    User.updated_at >= cutoff_date,  # Assuming verification updates the updated_at field
                    User.is_active == True,
                    UserCenterRole.is_active == True
                )
            ).order_by(User.updated_at.desc()).limit(limit).all()
        except Exception:
            return []


class UserCenterRoleRepository(BaseRepository[UserCenterRole]):
    """Repository for managing user-center-role relationships"""

    def __init__(self, db: Session):
        super().__init__(UserCenterRole, db)

    def get_user_role(self, user_id: int, learning_center_id: int) -> Optional[UserCenterRole]:
        """Get user's role in specific learning center"""
        try:
            return self.db.query(UserCenterRole).filter(
                and_(
                    UserCenterRole.user_id == user_id,
                    UserCenterRole.learning_center_id == learning_center_id,
                    UserCenterRole.is_active == True
                )
            ).first()
        except Exception:
            return None

    def assign_role(self, user_id: int, learning_center_id: int, role: UserRole) -> Optional[UserCenterRole]:
        """Assign role to user in learning center"""
        try:
            # Check if role assignment already exists
            existing_role = self.get_user_role(user_id, learning_center_id)

            if existing_role:
                # Update existing role
                existing_role.role = role
                self.db.commit()
                self.db.refresh(existing_role)
                return existing_role
            else:
                # Create new role assignment
                return self.create({
                    'user_id': user_id,
                    'learning_center_id': learning_center_id,
                    'role': role
                })
        except Exception:
            self.db.rollback()
            return None

    def change_role(self, user_id: int, learning_center_id: int, new_role: UserRole) -> Optional[UserCenterRole]:
        """Change user's role in learning center"""
        return self.assign_role(user_id, learning_center_id, new_role)

    def remove_role(self, user_id: int, learning_center_id: int) -> bool:
        """Remove user's role in learning center (soft delete)"""
        try:
            role_assignment = self.get_user_role(user_id, learning_center_id)
            if role_assignment:
                role_assignment.is_active = False
                self.db.commit()
                return True
            return False
        except Exception:
            self.db.rollback()
            return False

    def get_user_centers(self, user_id: int) -> List[UserCenterRole]:
        """Get all learning centers where user has roles"""
        try:
            return self.db.query(UserCenterRole).options(
                joinedload(UserCenterRole.learning_center)
            ).filter(
                and_(
                    UserCenterRole.user_id == user_id,
                    UserCenterRole.is_active == True
                )
            ).all()
        except Exception:
            return []

    def get_center_users(self, learning_center_id: int, role: Optional[UserRole] = None) -> List[UserCenterRole]:
        """Get all users in learning center with optional role filter"""
        try:
            query = self.db.query(UserCenterRole).options(
                joinedload(UserCenterRole.user)
            ).filter(
                and_(
                    UserCenterRole.learning_center_id == learning_center_id,
                    UserCenterRole.is_active == True
                )
            )

            if role:
                query = query.filter(UserCenterRole.role == role)

            return query.all()
        except Exception:
            return []