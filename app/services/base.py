from __future__ import annotations
from typing import Generic, TypeVar, List, Optional, Iterable, Tuple, Any, Dict, Callable
from contextlib import contextmanager
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import SQLAlchemyError

T = TypeVar("T")


class ServiceError(RuntimeError):
    """Domain/service-layer error."""


class NotFound(ServiceError):
    pass


class BaseService(Generic[T]):
    """Shared helpers for services.
    - transaction() context manager (commit/rollback)
    - paginate()
    - safe_sort()
    - guard_exists()
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------- transactions ----------------
    @contextmanager
    def transaction(self):
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ---------------- pagination ------------------
    def paginate(self, q: Query, page: int = 1, size: int = 20) -> Tuple[List[T], int, int, bool]:
        if page < 1:
            page = 1
        if size < 1:
            size = 20
        total = q.order_by(None).count()
        items = q.limit(size).offset((page - 1) * size).all()
        has_next = (page * size) < total
        return items, total, page, has_next

    # ---------------- sorting ---------------------
    def safe_sort(self, model: Any, q: Query, sort_by: Optional[str], order: str = "asc", *, allowed: Iterable[str]) -> Query:
        if not sort_by:
            return q
        sort_by = sort_by.strip()
        if sort_by not in allowed:
            return q
        col = getattr(model, sort_by, None)
        if col is None:
            return q
        return q.order_by(col.asc() if order.lower() != "desc" else col.desc())

    # ---------------- guards ----------------------
    def guard_exists(self, obj: Optional[T], *, msg: str = "Not found") -> T:
        if obj is None:
            raise NotFound(msg)
        return obj
