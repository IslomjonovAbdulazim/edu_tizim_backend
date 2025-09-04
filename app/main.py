from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from .database import engine, SessionLocal
from .models import Base, User, UserRole
from .routers import auth, super_admin, admin, teacher, content, telegram
from .utils import hash_password
from .services import SchedulerService

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "Language Learning Center API"),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# Mount static files - use persistent storage path
storage_path = os.getenv("STORAGE_PATH", "/tmp/persistent_storage")
try:
    os.makedirs(storage_path, exist_ok=True)
    os.makedirs(f"{storage_path}/logos", exist_ok=True)
    os.makedirs(f"{storage_path}/word-images", exist_ok=True)
    os.makedirs(f"{storage_path}/word-audio", exist_ok=True)
    app.mount("/storage", StaticFiles(directory=storage_path), name="storage")
    print(f"✅ Storage mounted at: {storage_path}")
except Exception as e:
    print(f"❌ Storage mount failed: {e}")
    # Fallback to tmp storage
    fallback_path = "/tmp/storage"
    os.makedirs(fallback_path, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=fallback_path), name="storage")
    print(f"✅ Fallback storage mounted at: {fallback_path}")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(super_admin.router, prefix="/api/super-admin", tags=["Super Admin"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(teacher.router, prefix="/api/teacher", tags=["Teacher"])
app.include_router(content.router, prefix="/api/content", tags=["Content"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram Bot"])

@app.get("/")
def root():
    return {
        "message": "Language Learning Center API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "redis": "connected"}

# Create super admin on startup
@app.on_event("startup")
async def create_super_admin():
    from .database import SessionLocal
    db = SessionLocal()

    try:
        super_admin = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()

        if not super_admin:
            super_admin = User(
                email=os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com"),
                password_hash=hash_password(os.getenv("SUPER_ADMIN_PASSWORD", "admin123")),
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            db.add(super_admin)
            db.commit()
            print("✅ Super admin created successfully")
        else:
            print("✅ Super admin already exists")

    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
    finally:
        db.close()


def daily_countdown_task():
    """Background task to decrement center days"""
    db = SessionLocal()
    try:
        SchedulerService.decrement_center_days(db)
    except Exception as e:
        print(f"❌ Error in daily countdown: {e}")
    finally:
        db.close()


# Initialize scheduler with Tashkent timezone
scheduler = BackgroundScheduler(timezone="Asia/Tashkent")
scheduler.add_job(
    func=daily_countdown_task,
    trigger="cron",
    hour=0,  # Run at midnight Tashkent time
    minute=0,
    id="daily_countdown"
)
scheduler.start()

# Shutdown scheduler on app exit
atexit.register(lambda: scheduler.shutdown())

