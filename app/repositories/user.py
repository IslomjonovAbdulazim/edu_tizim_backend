from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_by_phone_and_center(self, phone_number: str, learning_center_id: int) -> Optional[User]:
        """Get user by phone number within learning center"""
        return self.db.query(User).filter(
            and_(
                User.phone_number == phone_number,
                User.learning_center_id == learning_center_id
            )
        ).first()

    def get_users_by_role(self, role: UserRole, learning_center_id: int) -> List[User]:
        """Get all users with specific role in learning center"""
        return self.db.query(User).filter(
            and_(
                User.role == role,
                User.learning_center_id == learning_center_id,
                User.is_active == True
            )
        ).all()

    def get_users_by_center(self, learning_center_id: int) -> List[User]:
        """Get all users in learning center"""
        return self.db.query(User).filter(User.learning_center_id == learning_center_id).all()

    def get_active_users_by_center(self, learning_center_id: int) -> List[User]:
        """Get active users in learning center"""
        return self.db.query(User).filter(
            and_(
                User.learning_center_id == learning_center_id,
                User.is_active == True
            )
        ).all()

    def get_users_by_branch(self, branch_id: int) -> List[User]:
        """Get all users in branch"""
        return self.db.query(User).filter(User.branch_id == branch_id).all()

    def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        user = self.get(user_id)
        if user:
            user.is_verified = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate user"""
        user = self.get(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
        return user

    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user"""
        user = self.get(user_id)
        if user:
            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def change_role(self, user_id: int, new_role: UserRole) -> Optional[User]:
        """Change user role"""
        user = self.get(user_id)
        if user:
            user.role = new_role
            self.db.commit()
            self.db.refresh(user)
        return user

    def phone_exists_in_center(self, phone_number: str, learning_center_id: int) -> bool:
        """Check if phone number exists in learning center"""
        return self.db.query(User).filter(
            and_(
                User.phone_number == phone_number,
                User.learning_center_id == learning_center_id
            )
        ).first() is not None

    def telegram_id_exists(self, telegram_id: int) -> bool:
        """Check if telegram ID already exists"""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first() is not None

    def get_teachers_by_center(self, learning_center_id: int) -> List[User]:
        """Get all teachers in learning center"""
        return self.get_users_by_role(UserRole.TEACHER, learning_center_id)

    def get_students_by_center(self, learning_center_id: int) -> List[User]:
        """Get all students in learning center"""
        return self.get_users_by_role(UserRole.STUDENT, learning_center_id)

    def search_users(self, learning_center_id: int, query: str) -> List[User]:
        """Search users by name or phone"""
        return self.db.query(User).filter(
            and_(
                User.learning_center_id == learning_center_id,
                (User.full_name.ilike(f"%{query}%") | User.phone_number.ilike(f"%{query}%"))
            )
        ).all()