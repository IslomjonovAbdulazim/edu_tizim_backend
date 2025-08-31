from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import engine, get_db
from models import Base, User, UserRole
from utils import verify_token, hash_password, get_current_user_data
import schemas

# Import routers
from routers import auth, admin, content, teacher, super_admin

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

# Security
security = HTTPBearer()

# Auth dependency
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user with proper validation"""
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return get_current_user_data(db, payload["user_id"], payload.get("center_id"))

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(super_admin.router, prefix="/api/super-admin", tags=["Super Admin"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(teacher.router, prefix="/api/teacher", tags=["Teacher"])
app.include_router(content.router, prefix="/api/content", tags=["Content"])

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
    from database import SessionLocal
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