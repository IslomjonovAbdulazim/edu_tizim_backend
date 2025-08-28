from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from app.models.base import BaseModel
from app.schemas.common import PaginationParams, SortParams, SortOrder

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a record by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None,
            sort_params: Optional[SortParams] = None
    ) -> List[ModelType]:
        """Get multiple records with optional filtering and sorting"""
        query = db.query(self.model)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, key).in_(value))
                    else:
                        query = query.filter(getattr(self.model, key) == value)

        # Apply sorting
        if sort_params and sort_params.sort_by and hasattr(self.model, sort_params.sort_by):
            sort_column = getattr(self.model, sort_params.sort_by)
            if sort_params.sort_order == SortOrder.DESC:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sort by created_at desc
            query = query.order_by(desc(self.model.created_at))

        return query.offset(skip).limit(limit).all()

    def get_paginated(
            self,
            db: Session,
            pagination: PaginationParams,
            filters: Optional[Dict[str, Any]] = None,
            sort_params: Optional[SortParams] = None
    ) -> tuple[List[ModelType], int]:
        """Get paginated records with total count"""
        skip = (pagination.page - 1) * pagination.per_page

        # Get filtered query for counting
        query = db.query(self.model)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, key).in_(value))
                    else:
                        query = query.filter(getattr(self.model, key) == value)

        total = query.count()
        items = self.get_multi(db, skip, pagination.per_page, filters, sort_params)

        return items, total

    def update(self, db: Session, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update a record"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> Optional[ModelType]:
        """Delete a record by ID"""
        db_obj = self.get(db, id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

    def exists(self, db: Session, id: int) -> bool:
        """Check if a record exists"""
        return db.query(self.model.id).filter(self.model.id == id).first() is not None

    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters"""
        query = db.query(self.model)

        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, key).in_(value))
                    else:
                        query = query.filter(getattr(self.model, key) == value)

        return query.count()

    def search(
            self,
            db: Session,
            search_term: str,
            search_fields: List[str],
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """Search records across multiple fields"""
        if not search_term or not search_fields:
            return []

        query = db.query(self.model)
        search_conditions = []

        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                search_conditions.append(column.ilike(f"%{search_term}%"))

        if search_conditions:
            query = query.filter(or_(*search_conditions))

        return query.offset(skip).limit(limit).all()

    def bulk_create(self, db: Session, objs_in: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records"""
        db_objs = [self.model(**obj_data) for obj_data in objs_in]
        db.add_all(db_objs)
        db.commit()

        # Refresh all objects
        for db_obj in db_objs:
            db.refresh(db_obj)

        return db_objs

    def bulk_delete(self, db: Session, ids: List[int]) -> int:
        """Delete multiple records by IDs"""
        deleted_count = db.query(self.model).filter(self.model.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return deleted_count

    def get_by_field(self, db: Session, field_name: str, field_value: Any) -> Optional[ModelType]:
        """Get a record by a specific field"""
        if not hasattr(self.model, field_name):
            return None

        return db.query(self.model).filter(getattr(self.model, field_name) == field_value).first()

    def get_multi_by_field(self, db: Session, field_name: str, field_value: Any) -> List[ModelType]:
        """Get multiple records by a specific field"""
        if not hasattr(self.model, field_name):
            return []

        return db.query(self.model).filter(getattr(self.model, field_name) == field_value).all()

    def get_multi_by_ids(self, db: Session, ids: List[int]) -> List[ModelType]:
        """Get multiple records by their IDs"""
        return db.query(self.model).filter(self.model.id.in_(ids)).all()

    def soft_delete(self, db: Session, id: int) -> Optional[ModelType]:
        """Soft delete (if model supports it)"""
        db_obj = self.get(db, id)
        if db_obj and hasattr(db_obj, 'is_active'):
            db_obj.is_active = False
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def restore(self, db: Session, id: int) -> Optional[ModelType]:
        """Restore soft deleted record (if model supports it)"""
        db_obj = self.get(db, id)
        if db_obj and hasattr(db_obj, 'is_active'):
            db_obj.is_active = True
            db.commit()
            db.refresh(db_obj)
        return db_obj