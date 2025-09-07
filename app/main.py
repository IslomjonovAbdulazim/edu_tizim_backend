from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from .database import engine, SessionLocal
from .models import Base, User, UserRole
from .routers import auth, super_admin, admin, teacher, content, telegram, student
from .utils import hash_password
from .services import SchedulerService

# Try to import Socket.IO (optional for now)
try:
    if os.getenv("DISABLE_SOCKETIO") == "true":
        raise ImportError("Socket.IO manually disabled")
    
    import socketio
    from .socket_manager import sio
    from .routers import quiz
    SOCKETIO_AVAILABLE = True
    print("✅ Socket.IO enabled")
except ImportError as e:
    SOCKETIO_AVAILABLE = False
    print(f"⚠️ Socket.IO disabled: {e}")

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "Language Learning Center API"),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - restrict in production (MUST be before Socket.IO wrapping)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
print(f"✅ CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Create Socket.IO app AFTER CORS middleware (if available)
if SOCKETIO_AVAILABLE:
    socket_app = socketio.ASGIApp(sio, app)
    print("✅ Socket.IO app created")
else:
    socket_app = app
    print("⚠️ Using FastAPI app without Socket.IO")


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
app.include_router(student.router, prefix="/api/student", tags=["Student"])

# Include quiz router only if Socket.IO is available
if SOCKETIO_AVAILABLE:
    app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz System"])
    print("✅ Quiz endpoints enabled")
else:
    print("⚠️ Quiz endpoints disabled (Socket.IO not available)")

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

def quiz_cleanup_task():
    """Background task to clean up old quiz rooms"""
    if not SOCKETIO_AVAILABLE:
        return
    try:
        from .quiz_models import cleanup_disconnected_rooms
        cleanup_disconnected_rooms()
        print("✅ Quiz rooms cleaned up")
    except Exception as e:
        print(f"❌ Error in quiz cleanup: {e}")


# Initialize scheduler with Tashkent timezone
scheduler = BackgroundScheduler(timezone="Asia/Tashkent")
scheduler.add_job(
    func=daily_countdown_task,
    trigger="cron",
    hour=0,  # Run at midnight Tashkent time
    minute=0,
    id="daily_countdown"
)
scheduler.add_job(
    func=quiz_cleanup_task,
    trigger="interval",
    minutes=5,  # Clean up quiz rooms every 5 minutes
    id="quiz_cleanup"
)
scheduler.start()

# Shutdown scheduler on app exit
atexit.register(lambda: scheduler.shutdown())

# For uvicorn compatibility, export both app and socket_app
app = socket_app  # This makes uvicorn app.main:app work
application = socket_app  # Alternative export name

