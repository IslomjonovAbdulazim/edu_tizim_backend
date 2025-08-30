from typing import Optional, List, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from app.models.base import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def _commit(self) -> None:
        """Commit with rollback on error."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def get(self, id: int) -> Optional[T]:
        """Get single record by ID"""
        return self.db.query(self.model).filter(
            and_(self.model.id == id, self.model.is_active == True)
        ).first()

    def get_all(self, ids: List[int]) -> List[T]:
        """Get multiple records by IDs"""
        return self.db.query(self.model).filter(
            and_(self.model.id.in_(ids), self.model.is_active == True)
        ).all()

    def get_multi(
            self,
            skip: int = 0,
            limit: int = 100,
            filters: Dict[str, Any] = None,
            order_by: str = "created_at",
            order_desc: bool = True
    ) -> List[T]:
        """Get multiple records with pagination and filtering"""
        query = self.db.query(self.model).filter(self.model.is_active == True)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)

        # Apply ordering
        if hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def create(self, obj_in: Dict[str, Any]) -> T:
        """Create new record"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self._commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[T]:
        """Update existing record"""
        db_obj = self.get(id)
        if db_obj:
            for key, value in obj_in.items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
            self._commit()
            self.db.refresh(db_obj)
        return db_obj

    def soft_delete(self, id: int) -> Optional[T]:
        """Soft delete record"""
        db_obj = self.get(id)
        if db_obj:
            db_obj.is_active = False
            self._commit()
            self.db.refresh(db_obj)
        return db_obj

    def hard_delete(self, id: int) -> bool:
        """Hard delete record (use with caution)"""
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self._commit()
            return True
        return False

    def count(self, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filters"""
        query = self.db.query(self.model).filter(self.model.is_active == True)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)

        return query.count()

    def exists(self, id: int) -> bool:
        """Check if record exists"""
        return self.db.query(self.model).filter(
            and_(self.model.id == id, self.model.is_active == True)
        ).first() is not None

    def bulk_create(self, objects_in: List[Dict[str, Any]]) -> List[T]:
        """Bulk create multiple records"""
        db_objects = [self.model(**obj) for obj in objects_in]
        self.db.add_all(db_objects)
        self._commit()
        for obj in db_objects:
            self.db.refresh(obj)
        return db_objects

    def bulk_update(self, updates: List[Dict[str, Any]]) -> List[T]:
        """Bulk update multiple records"""
        updated_objects = []
        for update_data in updates:
            if 'id' in update_data:
                obj_id = update_data.pop('id')
                updated_obj = self.update(obj_id, update_data)
                if updated_obj:
                    updated_objects.append(updated_obj)
        return updated_objects

    def search(
            self,
            search_fields: List[str],
            query: str,
            filters: Dict[str, Any] = None,
            limit: int = 50
    ) -> List[T]:
        """Search records by multiple fields"""
        db_query = self.db.query(self.model).filter(self.model.is_active == True)

        # Apply filters first
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    db_query = db_query.filter(getattr(self.model, key) == value)

        # Apply search conditions
        if query and search_fields:
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    search_conditions.append(field_attr.ilike(f"%{query}%"))

            if search_conditions:
                db_query = db_query.filter(or_(*search_conditions))

        return db_query.limit(limit).all()

    def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get single record by any field"""
        if hasattr(self.model, field):
            return self.db.query(self.model).filter(
                and_(
                    getattr(self.model, field) == value,
                    self.model.is_active == True
                )
            ).first()
        return None

    def get_by_fields(self, **kwargs) -> Optional[T]:
        """Get single record by multiple fields"""
        query = self.db.query(self.model).filter(self.model.is_active == True)

        for key, value in kwargs.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)

        return query.first()

    def filter_by(self, **kwargs) -> List[T]:
        """Get multiple records by fields"""
        query = self.db.query(self.model).filter(self.model.is_active == True)

        for key, value in kwargs.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)

        return query.all()

    def activate(self, id: int) -> Optional[T]:
        """Activate (undelete) record"""
        db_obj = self.db.query(self.model).filter(self.model.id == id).first()
        if db_obj:
            db_obj.is_active = True
            self._commit()
            self.db.refresh(db_obj)
        return db_obj