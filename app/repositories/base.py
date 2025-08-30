from typing import Generic, TypeVar, Type, List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session, Query
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    # Basic CRUD Operations
    def get(self, id: int) -> Optional[ModelType]:
        """Get single record by ID"""
        try:
            return self.db.query(self.model).filter(
                and_(self.model.id == id, self.model.is_active == True)
            ).first()
        except SQLAlchemyError:
            return None

    def get_by_id(self, id: int, include_inactive: bool = False) -> Optional[ModelType]:
        """Get by ID with option to include inactive records"""
        try:
            query = self.db.query(self.model).filter(self.model.id == id)
            if not include_inactive:
                query = query.filter(self.model.is_active == True)
            return query.first()
        except SQLAlchemyError:
            return None

    def get_all(self, include_inactive: bool = False) -> List[ModelType]:
        """Get all records"""
        try:
            query = self.db.query(self.model)
            if not include_inactive:
                query = query.filter(self.model.is_active == True)
            return query.order_by(self.model.created_at.desc()).all()
        except SQLAlchemyError:
            return []

    def get_multi(
            self,
            skip: int = 0,
            limit: int = 100,
            include_inactive: bool = False,
            order_by: str = "created_at",
            order_desc: bool = True
    ) -> List[ModelType]:
        """Get multiple records with pagination and ordering"""
        try:
            query = self.db.query(self.model)

            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            # Apply ordering
            if hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError:
            return []

    def count(self, include_inactive: bool = False, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filters"""
        try:
            query = self.db.query(func.count(self.model.id))

            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            if filters:
                query = self._apply_filters(query, filters)

            return query.scalar() or 0
        except SQLAlchemyError:
            return 0

    def create(self, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """Create new record"""
        try:
            # Ensure is_active is True by default
            if 'is_active' not in obj_data:
                obj_data['is_active'] = True

            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except (IntegrityError, SQLAlchemyError) as e:
            self.db.rollback()
            raise e

    def update(self, id: int, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update existing record"""
        try:
            db_obj = self.get(id)
            if not db_obj:
                return None

            for field, value in obj_data.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)

            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except (IntegrityError, SQLAlchemyError) as e:
            self.db.rollback()
            raise e

    def delete(self, id: int, hard_delete: bool = False) -> bool:
        """Delete record (soft delete by default)"""
        try:
            db_obj = self.get_by_id(id, include_inactive=True)
            if not db_obj:
                return False

            if hard_delete:
                self.db.delete(db_obj)
            else:
                # Soft delete
                db_obj.is_active = False

            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

    def restore(self, id: int) -> Optional[ModelType]:
        """Restore soft-deleted record"""
        try:
            db_obj = self.get_by_id(id, include_inactive=True)
            if db_obj and not db_obj.is_active:
                db_obj.is_active = True
                self.db.commit()
                self.db.refresh(db_obj)
                return db_obj
            return db_obj
        except SQLAlchemyError:
            self.db.rollback()
            return None

    # Advanced Query Methods
    def get_by_field(self, field: str, value: Any, include_inactive: bool = False) -> Optional[ModelType]:
        """Get single record by field value"""
        try:
            if not hasattr(self.model, field):
                return None

            query = self.db.query(self.model).filter(getattr(self.model, field) == value)
            if not include_inactive:
                query = query.filter(self.model.is_active == True)
            return query.first()
        except SQLAlchemyError:
            return None

    def get_multi_by_field(
            self,
            field: str,
            value: Any,
            include_inactive: bool = False,
            limit: Optional[int] = None
    ) -> List[ModelType]:
        """Get multiple records by field value"""
        try:
            if not hasattr(self.model, field):
                return []

            query = self.db.query(self.model).filter(getattr(self.model, field) == value)
            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            if limit:
                query = query.limit(limit)

            return query.all()
        except SQLAlchemyError:
            return []

    def get_by_fields(self, filters: Dict[str, Any], include_inactive: bool = False) -> List[ModelType]:
        """Get records by multiple field values"""
        try:
            query = self.db.query(self.model)

            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            query = self._apply_filters(query, filters)
            return query.all()
        except SQLAlchemyError:
            return []

    def search(
            self,
            search_fields: List[str],
            search_term: str,
            include_inactive: bool = False,
            limit: int = 50
    ) -> List[ModelType]:
        """Search across multiple fields"""
        try:
            if not search_term.strip():
                return []

            query = self.db.query(self.model)

            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            # Build OR conditions for search fields
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    search_conditions.append(column.ilike(f"%{search_term}%"))

            if search_conditions:
                query = query.filter(or_(*search_conditions))

            return query.limit(limit).all()
        except SQLAlchemyError:
            return []

    def exists(self, id: int) -> bool:
        """Check if record exists"""
        try:
            return self.db.query(self.model).filter(
                and_(self.model.id == id, self.model.is_active == True)
            ).first() is not None
        except SQLAlchemyError:
            return False

    def exists_by_field(self, field: str, value: Any, exclude_id: Optional[int] = None) -> bool:
        """Check if record exists by field value"""
        try:
            if not hasattr(self.model, field):
                return False

            query = self.db.query(self.model).filter(
                and_(
                    getattr(self.model, field) == value,
                    self.model.is_active == True
                )
            )

            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            return query.first() is not None
        except SQLAlchemyError:
            return False

    # Bulk Operations
    def bulk_create(self, objects_data: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records"""
        try:
            db_objects = []
            for obj_data in objects_data:
                if 'is_active' not in obj_data:
                    obj_data['is_active'] = True
                db_objects.append(self.model(**obj_data))

            self.db.add_all(db_objects)
            self.db.commit()

            for obj in db_objects:
                self.db.refresh(obj)

            return db_objects
        except (IntegrityError, SQLAlchemyError) as e:
            self.db.rollback()
            raise e

    def bulk_update(self, updates: List[Dict[str, Any]]) -> List[ModelType]:
        """Update multiple records"""
        try:
            updated_objects = []

            for update_data in updates:
                if 'id' not in update_data:
                    continue

                obj_id = update_data.pop('id')
                updated_obj = self.update(obj_id, update_data)
                if updated_obj:
                    updated_objects.append(updated_obj)

            return updated_objects
        except (IntegrityError, SQLAlchemyError) as e:
            self.db.rollback()
            raise e

    def bulk_delete(self, ids: List[int], hard_delete: bool = False) -> int:
        """Delete multiple records"""
        try:
            deleted_count = 0

            for obj_id in ids:
                if self.delete(obj_id, hard_delete):
                    deleted_count += 1

            return deleted_count
        except SQLAlchemyError:
            self.db.rollback()
            return 0

    # Helper Methods
    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply filters to query"""
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                column = getattr(self.model, field)

                if isinstance(value, list):
                    query = query.filter(column.in_(value))
                elif isinstance(value, dict):
                    # Handle range filters like {'gte': 10, 'lte': 100}
                    if 'gte' in value:
                        query = query.filter(column >= value['gte'])
                    if 'lte' in value:
                        query = query.filter(column <= value['lte'])
                    if 'gt' in value:
                        query = query.filter(column > value['gt'])
                    if 'lt' in value:
                        query = query.filter(column < value['lt'])
                else:
                    query = query.filter(column == value)

        return query

    def get_query(self) -> Query:
        """Get base query for advanced operations"""
        return self.db.query(self.model)

    def flush(self):
        """Flush pending operations to database"""
        try:
            self.db.flush()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def commit(self):
        """Commit transaction"""
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def rollback(self):
        """Rollback transaction"""
        self.db.rollback()