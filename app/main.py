from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .config import settings
from .database import engine, Base
from .middleware.cache_middleware import CacheHeadersMiddleware

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for Language Learning Centers",
)

# Cache headers middleware
app.add_middleware(CacheHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded content
if os.path.exists(settings.STORAGE_PATH):
    app.mount("/static", StaticFiles(directory=settings.STORAGE_PATH), name="static")

# Include routers
from .routers import auth, admin, teacher, student, content, super_admin

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(super_admin.router, prefix="/api/v1/super-admin", tags=["Super Admin"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(teacher.router, prefix="/api/v1/teacher", tags=["Teacher"])
app.include_router(student.router, prefix="/api/v1/student", tags=["Student"])
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])

@app.get("/")
async def root():
    return {
        "message": "Language Learning Center API",
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}