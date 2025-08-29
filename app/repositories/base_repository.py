from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, data: Dict[str, Any]) -> ModelType:
        """Create new record"""
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, id: int, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update record"""
        obj = self.get(db, id)
        if obj:
            obj.update_from_dict(data)
            db.commit()
            db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> bool:
        """Delete record"""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False

    def filter(self, db: Session, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Filter with conditions"""
        query = db.query(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                column = getattr(self.model, key)
                if isinstance(value, list):
                    query = query.filter(column.in_(value))
                else:
                    query = query.filter(column == value)

        return query.offset(skip).limit(limit).all()

    def search(self, db: Session, term: str, fields: List[str]) -> List[ModelType]:
        """Search across multiple fields"""
        if not term or not fields:
            return []

        query = db.query(self.model)
        conditions = []

        for field in fields:
            if hasattr(self.model, field):
                conditions.append(getattr(self.model, field).ilike(f"%{term}%"))

        return query.filter(or_(*conditions)).all() if conditions else []

    def count(self, db: Session, filters: Dict[str, Any] = None) -> int:
        """Count records"""
        query = db.query(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)

        return query.count()

    def exists(self, db: Session, id: int) -> bool:
        """Check if exists"""
        return db.query(self.model.id).filter(self.model.id == id).first() is not None