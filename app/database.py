from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import redis

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# PostgreSQL Database
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis for caching
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cache helpers
def get_cache(key: str):
    try:
        return redis_client.get(key)
    except:
        return None

def set_cache(key: str, value: str, expire: int = 300):
    try:
        redis_client.setex(key, expire, value)
    except:
        pass

def delete_cache(key: str):
    try:
        redis_client.delete(key)
    except:
        pass

def clear_cache_pattern(pattern: str):
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except:
        pass