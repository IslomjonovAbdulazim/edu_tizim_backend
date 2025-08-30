from __future__ import annotations
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, asc
from app.models.user import User, UserCenterRole
from app.repositories.base import BaseRepository
from .base import BaseService


class UserService(BaseService[User]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[User](db, User)

    def get(self, user_id: int) -> Optional[User]:
        return self.repo.get(user_id)

    def get_by_telegram(self, telegram_id: int) -> Optional[User]:
        res = self.repo.list(telegram_id=telegram_id)
        return res[0] if res else None

    def search(self, center_id: Optional[int], query: str, *, limit: int = 50) -> List[User]:
        pattern = f"%{query}%"
        q = self.db.query(User).filter(User.is_active.is_(True))
        if center_id is not None:
            q = q.join(UserCenterRole).filter(and_(UserCenterRole.learning_center_id == center_id, UserCenterRole.is_active.is_(True)))
        q = q.filter(or_(User.full_name.ilike(pattern), User.phone_number.ilike(pattern)))
        return q.order_by(asc(User.full_name)).limit(limit).all()

    def create(self, data: Dict[str, Any]) -> User:
        return self.repo.create(data)

    def update(self, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        return self.repo.update(user_id, data)

    def delete(self, user_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(user_id, hard=hard)

    def list_roles(self, user_id: int) -> List[UserCenterRole]:
        return self.db.query(UserCenterRole).filter(and_(UserCenterRole.user_id == user_id, UserCenterRole.is_active.is_(True))).all()
