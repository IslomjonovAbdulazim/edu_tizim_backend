from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, func
from sqlalchemy import MetaData
# SQLAlchemy naming convention to stabilize Alembic diffs
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

from sqlalchemy.orm import declarative_base

Base = declarative_base(metadata=MetaData(naming_convention=naming_convention))


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Consistent soft delete pattern across all models
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        """Convert to dictionary, excluding relationships"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def soft_delete(self):
        """Soft delete the record"""
        self.is_active = False