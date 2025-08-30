from fastapi import APIRouter

# Import concrete endpoint modules if they exist in your project
try:
    from app.api.v1.endpoints import auth, content, gamification, groups, learning, learning_centers, users
except Exception:  # keep router import resilient during boot
    auth = content = gamification = groups = learning = learning_centers = users = None  # type: ignore

api_v1 = APIRouter()
if auth: api_v1.include_router(auth.router)
if users: api_v1.include_router(users.router)
if content: api_v1.include_router(content.router)
if groups: api_v1.include_router(groups.router)
if learning: api_v1.include_router(learning.router)
if learning_centers: api_v1.include_router(learning_centers.router)
if gamification: api_v1.include_router(gamification.router)

# Backwards compatibility with older imports:
api_router = api_v1
