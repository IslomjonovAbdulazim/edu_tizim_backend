from __future__ import annotations
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from app.models.learning_center import LearningCenter, Branch, Payment
from app.models.user import UserCenterRole, UserRole
from app.repositories.base import BaseRepository
from .base import BaseService


class LearningCenterService(BaseService[LearningCenter]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.center_repo = BaseRepository[LearningCenter](db, LearningCenter)
        self.branch_repo = BaseRepository[Branch](db, Branch)
        self.payment_repo = BaseRepository[Payment](db, Payment)
        self.role_repo = BaseRepository[UserCenterRole](db, UserCenterRole)

    # centers
    def create_center(self, data: Dict[str, Any]) -> LearningCenter:
        return self.center_repo.create(data)

    def update_center(self, center_id: int, data: Dict[str, Any]) -> Optional[LearningCenter]:
        return self.center_repo.update(center_id, data)

    def list_centers(self) -> List[LearningCenter]:
        return self.center_repo.list()

    # branches
    def create_branch(self, data: Dict[str, Any]) -> Branch:
        return self.branch_repo.create(data)

    def list_branches(self, learning_center_id: int) -> List[Branch]:
        return self.branch_repo.list(learning_center_id=learning_center_id)

    # payments
    def create_payment(self, data: Dict[str, Any]) -> Payment:
        return self.payment_repo.create(data)

    # roles
    def assign_role(self, user_id: int, center_id: int, role: UserRole) -> bool:
        with self.transaction():
            try:
                self.role_repo.create({"user_id": user_id, "learning_center_id": center_id, "role": role})
                return True
            except IntegrityError:
                self.db.rollback()
                existing = (
                    self.db.query(UserCenterRole)
                    .filter(and_(UserCenterRole.user_id == user_id, UserCenterRole.learning_center_id == center_id))
                    .first()
                )
                if existing and not existing.is_active:
                    existing.is_active = True
                    existing.role = role
                    self.db.commit()
                    return True
                raise

    def revoke_role(self, user_id: int, center_id: int, *, hard: bool = False) -> bool:
        r = (
            self.db.query(UserCenterRole)
            .filter(and_(UserCenterRole.user_id == user_id, UserCenterRole.learning_center_id == center_id))
            .first()
        )
        if not r:
            return False
        with self.transaction():
            if hasattr(r, "is_active") and not hard:
                r.is_active = False
            else:
                self.db.delete(r)
        return True

    def list_center_roles(self, center_id: int) -> List[UserCenterRole]:
        return self.db.query(UserCenterRole).filter(and_(UserCenterRole.learning_center_id == center_id, UserCenterRole.is_active.is_(True))).all()
