from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        """Convert to dictionary, excluding relationships"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update_from_dict(self, data: dict, exclude: set = None):
        """Update from dictionary with optional exclusions"""
        exclude = exclude or set()
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)