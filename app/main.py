from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import engine, get_db
from models import Base, User, UserRole
from utils import verify_token, hash_password
import schemas

# Import routers (we'll create these)
from routers import auth, admin, content, student, teacher, super_admin

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "Language Learning Center API"),
    version=os.getenv("VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Auth dependency
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return {
        "user": user,
        "center_id": payload.get("center_id")
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(super_admin.router, prefix="/super-admin", tags=["Super Admin"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(teacher.router, prefix="/teacher", tags=["Teacher"])
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(content.router, prefix="/content", tags=["Content"])


@app.get("/")
def root():
    return {"message": "Language Learning Center API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


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
                email=os.getenv("SUPER_ADMIN_EMAIL"),
                password_hash=hash_password(os.getenv("SUPER_ADMIN_PASSWORD")),
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            db.add(super_admin)
            db.commit()
            print("Super admin created successfully")

    except Exception as e:
        print(f"Error creating super admin: {e}")
    finally:
        db.close()