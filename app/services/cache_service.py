import json
import hashlib
import inspect
from typing import Any, Optional, List, Union
from functools import wraps
import logging

from ..database import get_redis
from ..config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.redis = get_redis()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_data = f"{prefix}:{':'.join(map(str, args))}"
        if kwargs:
            key_data += f":{json.dumps(kwargs, sort_keys=True)}"
        
        # Use hash for very long keys
        if len(key_data) > 200:
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
        
        return key_data
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds"""
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern using safe scan_iter"""
        try:
            deleted_count = 0
            batch = []
            batch_size = 100  # Process in batches to avoid blocking
            
            async for key in self.redis.scan_iter(match=pattern):
                batch.append(key)
                if len(batch) >= batch_size:
                    if batch:
                        deleted_count += await self.redis.delete(*batch)
                        batch = []
            
            # Delete remaining keys
            if batch:
                deleted_count += await self.redis.delete(*batch)
            
            return deleted_count
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    # Learning Center caching
    async def get_learning_centers(self) -> Optional[List[dict]]:
        """Get cached learning centers"""
        return await self.get("learning_centers:active")
    
    async def set_learning_centers(self, centers: List[dict], ttl: int = 600) -> bool:
        """Cache learning centers for 10 minutes"""
        return await self.set("learning_centers:active", centers, ttl)
    
    async def invalidate_learning_centers(self):
        """Invalidate learning centers cache"""
        await self.delete("learning_centers:active")
    
    # User caching
    async def get_user(self, user_id: int) -> Optional[dict]:
        """Get cached user"""
        return await self.get(f"user:{user_id}")
    
    async def set_user(self, user_id: int, user_data: dict, ttl: int = 1800) -> bool:
        """Cache user for 30 minutes"""
        return await self.set(f"user:{user_id}", user_data, ttl)
    
    async def invalidate_user(self, user_id: int):
        """Invalidate user cache"""
        await self.delete(f"user:{user_id}")
        # Also invalidate related caches
        await self.delete_pattern(f"user_groups:{user_id}:*")
        await self.delete_pattern(f"student_progress:{user_id}:*")
    
    # Course content caching
    async def get_course_lessons(self, course_id: int) -> Optional[List[dict]]:
        """Get cached course lessons"""
        return await self.get(f"course_lessons:{course_id}")
    
    async def set_course_lessons(self, course_id: int, lessons: List[dict], ttl: int = 3600) -> bool:
        """Cache course lessons for 1 hour"""
        return await self.set(f"course_lessons:{course_id}", lessons, ttl)
    
    async def get_lesson_words(self, lesson_id: int) -> Optional[List[dict]]:
        """Get cached lesson words"""
        return await self.get(f"lesson_words:{lesson_id}")
    
    async def set_lesson_words(self, lesson_id: int, words: List[dict], ttl: int = 3600) -> bool:
        """Cache lesson words for 1 hour"""
        return await self.set(f"lesson_words:{lesson_id}", words, ttl)
    
    async def invalidate_course_content(self, course_id: int, lesson_ids: List[int] = None):
        """Invalidate all course-related content"""
        await self.delete_pattern(f"course_lessons:{course_id}")
        
        # If specific lesson IDs provided, invalidate only those
        if lesson_ids:
            for lesson_id in lesson_ids:
                await self.delete(f"lesson_words:{lesson_id}")
        else:
            # Fallback: invalidate all lesson words (less efficient)
            await self.delete_pattern(f"lesson_words:*")
    
    # Progress caching
    async def get_student_progress(self, student_id: int, lesson_id: int) -> Optional[dict]:
        """Get cached student progress"""
        return await self.get(f"student_progress:{student_id}:{lesson_id}")
    
    async def set_student_progress(self, student_id: int, lesson_id: int, progress: dict, ttl: int = 300) -> bool:
        """Cache student progress for 5 minutes"""
        return await self.set(f"student_progress:{student_id}:{lesson_id}", progress, ttl)
    
    async def invalidate_student_progress(self, student_id: int, lesson_id: int = None):
        """Invalidate student progress cache"""
        if lesson_id:
            await self.delete(f"student_progress:{student_id}:{lesson_id}")
        else:
            await self.delete_pattern(f"student_progress:{student_id}:*")
    
    # Leaderboard caching
    async def get_leaderboard(self, learning_center_id: int) -> Optional[List[dict]]:
        """Get cached leaderboard"""
        return await self.get(f"leaderboard:{learning_center_id}")
    
    async def set_leaderboard(self, learning_center_id: int, leaderboard: List[dict], ttl: int = 900) -> bool:
        """Cache leaderboard for 15 minutes"""
        return await self.set(f"leaderboard:{learning_center_id}", leaderboard, ttl)
    
    async def invalidate_leaderboard(self, learning_center_id: int):
        """Invalidate leaderboard cache"""
        await self.delete(f"leaderboard:{learning_center_id}")


# Singleton instance
cache_service = CacheService()


def cache_result(prefix: str, ttl: int = 300, key_args: List[str] = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_args:
                # Map positional args to parameter names
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                # Create combined kwargs from args and kwargs
                bound_args = {}
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        bound_args[param_names[i]] = arg
                bound_args.update(kwargs)
                
                # Extract specified key arguments
                cache_key_parts = []
                for arg_name in key_args:
                    if arg_name in bound_args:
                        cache_key_parts.append(str(bound_args[arg_name]))
                
                cache_key = cache_service._generate_key(prefix, *cache_key_parts)
            else:
                cache_key = cache_service._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:  # Only cache non-None results
                await cache_service.set(cache_key, result, ttl)
                logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        return wrapper
    return decorator