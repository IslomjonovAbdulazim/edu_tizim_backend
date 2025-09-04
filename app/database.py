from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
from dotenv import load_dotenv
import redis

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# PostgreSQL Database
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis for caching and sessions
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    print("✅ Redis connected successfully")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    redis_client = None

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis helpers with error handling
class RedisService:
    @staticmethod
    def get(key: str):
        """Get value from Redis"""
        if not redis_client:
            return None
        try:
            return redis_client.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    @staticmethod
    def set(key: str, value: str, expire: int = 300):
        """Set value in Redis with expiration"""
        if not redis_client:
            return False
        try:
            return redis_client.setex(key, expire, value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    @staticmethod
    def delete(key: str):
        """Delete key from Redis"""
        if not redis_client:
            return False
        try:
            return redis_client.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    @staticmethod
    def clear_pattern(pattern: str):
        """Delete keys matching pattern"""
        if not redis_client:
            return False
        try:
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Redis clear pattern error: {e}")
            return False

    @staticmethod
    def get_json(key: str):
        """Get JSON value from Redis"""
        data = RedisService.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def set_json(key: str, data: dict, expire: int = 300):
        """Set JSON value in Redis"""
        try:
            json_data = json.dumps(data, default=str)
            return RedisService.set(key, json_data, expire)
        except Exception as e:
            print(f"Redis set JSON error: {e}")
            return False

    @staticmethod
    def store_verification_code(phone: str, code: str, expire: int = 300):
        """Store verification code for phone"""
        key = f"verify:{phone}"
        return RedisService.set(key, code, expire)

    @staticmethod
    def get_verification_code(phone: str):
        """Get verification code for phone"""
        key = f"verify:{phone}"
        return RedisService.get(key)

    @staticmethod
    def delete_verification_code(phone: str):
        """Delete verification code after use"""
        key = f"verify:{phone}"
        return RedisService.delete(key)

    @staticmethod
    def get_verification_code_ttl(phone: str):
        """Get remaining TTL for verification code"""
        if not redis_client:
            return 0
        try:
            key = f"verify:{phone}"
            return redis_client.ttl(key)
        except Exception as e:
            print(f"Redis TTL error: {e}")
            return 0

# Backwards compatibility
get_cache = RedisService.get
set_cache = RedisService.set
delete_cache = RedisService.delete
clear_cache_pattern = RedisService.clear_pattern