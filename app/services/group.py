from __future__ import annotations
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, asc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.group import Group
from app.models.user import StudentGroup
from app.repositories.base import BaseRepository
from .base import BaseService


class GroupService(BaseService[Group]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[Group](db, Group)
        self.membership_repo = BaseRepository[StudentGroup](db, StudentGroup)

    def get(self, group_id: int) -> Optional[Group]:
        return self.repo.get(group_id)

    def list_by_center(self, learning_center_id: int) -> List[Group]:
        q = self.db.query(Group).filter(and_(Group.learning_center_id == learning_center_id, Group.is_active.is_(True)))
        return q.order_by(asc(Group.order_index)).all()

    def create(self, data: Dict[str, Any]) -> Group:
        return self.repo.create(data)

    def update(self, group_id: int, data: Dict[str, Any]) -> Optional[Group]:
        return self.repo.update(group_id, data)

    def delete(self, group_id: int, *, hard: bool = False) -> bool:
        return self.repo.delete(group_id, hard=hard)

    def reorder(self, learning_center_id: int, group_order: List[int]) -> bool:
        try:
            allowed = {gid for (gid,) in self.db.query(Group.id).filter(and_(Group.learning_center_id == learning_center_id, Group.id.in_(group_order))).all()}
            for idx, gid in enumerate(group_order):
                if gid in allowed:
                    self.repo.update(gid, {"order_index": idx})
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    # memberships
    def add_student(self, user_id: int, group_id: int) -> bool:
        with self.transaction():
            try:
                self.membership_repo.create({"user_id": user_id, "group_id": group_id})
                return True
            except IntegrityError:
                self.db.rollback()
                existing = (
                    self.db.query(StudentGroup)
                    .filter(and_(StudentGroup.user_id == user_id, StudentGroup.group_id == group_id))
                    .first()
                )
                if existing and not existing.is_active:
                    existing.is_active = True
                    self.db.commit()
                    return True
                raise

    def remove_student(self, user_id: int, group_id: int, *, hard: bool = False) -> bool:
        m = (
            self.db.query(StudentGroup)
            .filter(and_(StudentGroup.user_id == user_id, StudentGroup.group_id == group_id))
            .first()
        )
        if not m:
            return False
        with self.transaction():
            if hasattr(m, "is_active") and not hard:
                m.is_active = False
            else:
                self.db.delete(m)
        return True

    def list_members(self, group_id: int) -> List[StudentGroup]:
        return self.db.query(StudentGroup).filter(and_(StudentGroup.group_id == group_id, StudentGroup.is_active.is_(True))).all()
