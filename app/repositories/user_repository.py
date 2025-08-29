from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.constants.roles import UserRole


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_telegram_id(self, db: Session, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_by_phone_number(self, db: Session, phone_number: str, learning_center_id: int) -> Optional[User]:
        """Get user by phone number within a specific learning center"""
        return db.query(User).filter(
            and_(
                User.phone_number == phone_number,
                User.learning_center_id == learning_center_id
            )
        ).first()

    def get_by_phone_number_global(self, db: Session, phone_number: str) -> List[User]:
        """Get all users with this phone number across all learning centers"""
        return db.query(User).filter(User.phone_number == phone_number).all()

    def get_by_telegram_and_phone(self, db: Session, telegram_id: int, phone_number: str, learning_center_id: int) -> \
    Optional[User]:
        """Get user by both Telegram ID and phone number within learning center"""
        return db.query(User).filter(
            and_(
                User.telegram_id == telegram_id,
                User.phone_number == phone_number,
                User.learning_center_id == learning_center_id
            )
        ).first()

    def phone_exists_in_center(self, db: Session, phone_number: str, learning_center_id: int) -> bool:
        """Check if phone number already exists in the learning center"""
        return db.query(User).filter(
            and_(
                User.phone_number == phone_number,
                User.learning_center_id == learning_center_id
            )
        ).first() is not None

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        User]:
        """Get users by learning center"""
        return db.query(User).filter(User.learning_center_id == learning_center_id).offset(skip).limit(limit).all()

    def get_by_role(self, db: Session, role: UserRole, learning_center_id: Optional[int] = None) -> List[User]:
        """Get users by role, optionally filtered by learning center"""
        query = db.query(User).filter(User.role == role)
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_active_users(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get all active users, optionally filtered by learning center"""
        query = db.query(User).filter(User.is_active == True)
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_verified_users(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get all verified users, optionally filtered by learning center"""
        query = db.query(User).filter(User.is_verified == True)
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_students(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get all student users"""
        return self.get_by_role(db, UserRole.STUDENT, learning_center_id)

    def get_parents(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get all parent users"""
        return self.get_by_role(db, UserRole.PARENT, learning_center_id)

    def get_staff_members(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get all staff members (reception, content manager, group manager)"""
        staff_roles = [UserRole.RECEPTION, UserRole.CONTENT_MANAGER, UserRole.GROUP_MANAGER]
        query = db.query(User).filter(User.role.in_(staff_roles))
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_ceos(self, db: Session) -> List[User]:
        """Get all CEO users"""
        return self.get_by_role(db, UserRole.CEO)

    def get_super_admins(self, db: Session) -> List[User]:
        """Get all super admin users"""
        return self.get_by_role(db, UserRole.SUPER_ADMIN)

    def verify_user(self, db: Session, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        user = self.get(db, user_id)
        if user:
            user.is_verified = True
            db.commit()
            db.refresh(user)
        return user

    def deactivate_user(self, db: Session, user_id: int) -> Optional[User]:
        """Deactivate a user"""
        user = self.get(db, user_id)
        if user:
            user.is_active = False
            db.commit()
            db.refresh(user)
        return user

    def activate_user(self, db: Session, user_id: int) -> Optional[User]:
        """Activate a user"""
        user = self.get(db, user_id)
        if user:
            user.is_active = True
            db.commit()
            db.refresh(user)
        return user

    def update_phone_number(self, db: Session, user_id: int, new_phone: str) -> Optional[User]:
        """Update user's phone number"""
        user = self.get(db, user_id)
        if user:
            # Check if new phone already exists in the same learning center
            if self.phone_exists_in_center(db, new_phone, user.learning_center_id):
                raise ValueError("Phone number already exists in this learning center")

            user.phone_number = new_phone
            user.is_verified = False  # Require re-verification with new phone
            db.commit()
            db.refresh(user)
        return user

    def update_telegram_id(self, db: Session, user_id: int, new_telegram_id: int) -> Optional[User]:
        """Update user's Telegram ID"""
        user = self.get(db, user_id)
        if user:
            user.telegram_id = new_telegram_id
            user.is_verified = False  # Require re-verification
            db.commit()
            db.refresh(user)
        return user

    def search_users(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            role: Optional[UserRole] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[User]:
        """Search users by name or phone number"""
        query = db.query(User).filter(
            or_(
                User.full_name.ilike(f"%{search_term}%"),
                User.phone_number.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        if role:
            query = query.filter(User.role == role)

        return query.offset(skip).limit(limit).all()

    def count_by_role(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Count users by role"""
        query = db.query(User.role, func.count(User.id))

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        counts = query.group_by(User.role).all()
        return {role: count for role, count in counts}

    def get_user_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive user statistics"""
        base_query = db.query(User)
        if learning_center_id:
            base_query = base_query.filter(User.learning_center_id == learning_center_id)

        total_users = base_query.count()
        active_users = base_query.filter(User.is_active == True).count()
        verified_users = base_query.filter(User.is_verified == True).count()

        role_counts = self.count_by_role(db, learning_center_id)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "inactive_users": total_users - active_users,
            "unverified_users": total_users - verified_users,
            "role_distribution": role_counts
        }