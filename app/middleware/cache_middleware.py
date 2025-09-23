from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import hashlib
import json


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Add appropriate cache headers to responses"""
    
    # Routes that should be cached by browsers
    CACHEABLE_ROUTES = {
        "/api/v1/auth/learning-centers": 600,  # 10 minutes
        "/api/v1/student/courses": 1800,       # 30 minutes
        "/api/v1/student/leaderboard": 900,    # 15 minutes
        "/api/v1/content/courses": 1800,       # 30 minutes
    }
    
    # Routes that should never be cached
    NO_CACHE_ROUTES = [
        "/api/v1/auth/send-code",
        "/api/v1/auth/verify-login", 
        "/api/v1/auth/refresh",
        "/api/v1/student/progress",
    ]
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only add cache headers for GET requests
        if request.method != "GET":
            return response
        
        path = request.url.path
        
        # Check if route should not be cached
        if any(no_cache in path for no_cache in self.NO_CACHE_ROUTES):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        # Check if route has specific cache duration
        for route, duration in self.CACHEABLE_ROUTES.items():
            if route in path:
                response.headers["Cache-Control"] = f"public, max-age={duration}"
                
                # Add ETag for content-based caching
                if hasattr(response, "body") and response.body:
                    etag = hashlib.md5(response.body).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'
                
                break
        else:
            # Default cache for other GET requests
            response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
        
        return response