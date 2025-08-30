from __future__ import annotations
"""Central SQLAlchemy session/engine wiring and FastAPI dependency."""
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    # pydantic-settings v2 (see app/core/config.py)
    from app.core.config import settings
    DATABASE_URL: Optional[str] = settings.DATABASE_URL
except Exception:  # keeps import working during scaffolding
    DATABASE_URL = None

# Dev fallback if no env var is set
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./app.db"

# Create sync engine. Driver taken from DATABASE_URL, e.g.:
#   postgresql+psycopg://user:pass@host:5432/dbname
#   sqlite:///./app.db
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
    future=True,
)

def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a session and closes it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager for scripts/cron jobs.
    Example:
        with db_session() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
