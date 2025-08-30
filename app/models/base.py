from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Consistent soft delete pattern across all models
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        """Convert to dictionary, excluding relationships"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def soft_delete(self):
        """Soft delete the record"""
        self.is_active = False