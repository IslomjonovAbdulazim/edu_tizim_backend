from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_telegram_id(self, db: Session, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_by_phone(self, db: Session, phone: str, learning_center_id: int) -> Optional[User]:
        """Get user by phone and learning center"""
        return db.query(User).filter(
            and_(User.phone_number == phone, User.learning_center_id == learning_center_id)
        ).first()

    def get_by_learning_center(self, db: Session, learning_center_id: int, skip: int = 0, limit: int = 100) -> List[
        User]:
        """Get users by learning center"""
        return db.query(User).filter(
            User.learning_center_id == learning_center_id
        ).offset(skip).limit(limit).all()

    def get_by_role(self, db: Session, role: str, learning_center_id: Optional[int] = None) -> List[User]:
        """Get users by role"""
        query = db.query(User).filter(User.role == role)
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_active_users(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get active users"""
        query = db.query(User).filter(User.is_active == True)
        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)
        return query.all()

    def get_students(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get student users"""
        return self.get_by_role(db, "student", learning_center_id)

    def get_parents(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get parent users"""
        return self.get_by_role(db, "parent", learning_center_id)

    def get_teachers(self, db: Session, learning_center_id: Optional[int] = None) -> List[User]:
        """Get teacher users"""
        return self.get_by_role(db, "teacher", learning_center_id)

    def search_users(self, db: Session, term: str, learning_center_id: Optional[int] = None) -> List[User]:
        """Search users by name or phone"""
        query = db.query(User)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.filter(
            User.full_name.ilike(f"%{term}%") |
            User.phone_number.ilike(f"%{term}%")
        ).all()

    def activate_user(self, db: Session, user_id: int) -> Optional[User]:
        """Activate user"""
        user = self.get(db, user_id)
        if user:
            user.is_active = True
            db.commit()
            db.refresh(user)
        return user

    def deactivate_user(self, db: Session, user_id: int) -> Optional[User]:
        """Deactivate user"""
        user = self.get(db, user_id)
        if user:
            user.is_active = False
            db.commit()
            db.refresh(user)
        return user