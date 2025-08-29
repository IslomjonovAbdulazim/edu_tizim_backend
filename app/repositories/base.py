from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[ModelType]:
        """Get single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
            self,
            skip: int = 0,
            limit: int = 100,
            filters: Dict[str, Any] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and filters"""
        query = self.db.query(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filters"""
        query = self.db.query(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        return query.scalar()

    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create new record"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Update existing record"""
        db_obj = self.get(id)
        if not db_obj:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        """Delete record by ID"""
        db_obj = self.get(id)
        if not db_obj:
            return False

        self.db.delete(db_obj)
        self.db.commit()
        return True

    def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get single record by field value"""
        if not hasattr(self.model, field):
            return None
        return self.db.query(self.model).filter(getattr(self.model, field) == value).first()

    def get_multi_by_field(self, field: str, value: Any) -> List[ModelType]:
        """Get multiple records by field value"""
        if not hasattr(self.model, field):
            return []
        return self.db.query(self.model).filter(getattr(self.model, field) == value).all()

    def exists(self, id: int) -> bool:
        """Check if record exists"""
        return self.db.query(self.model).filter(self.model.id == id).first() is not None

    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records at once"""
        db_objects = [self.model(**obj_data) for obj_data in objects]
        self.db.add_all(db_objects)
        self.db.commit()
        for obj in db_objects:
            self.db.refresh(obj)
        return db_objects