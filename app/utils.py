from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import requests
import random
import re

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        return payload
    except JWTError:
        return None


def get_current_user_data(db: Session, user_id: int, center_id: Optional[int] = None):
    """Get current user data with proper validation"""
    from .models import User, LearningCenter, LearningCenterProfile, UserRole

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # For super admin, no center needed
    if user.role == UserRole.SUPER_ADMIN:
        return {
            "user": user,
            "profile": None,
            "center": None,
            "center_id": None,
            "role": user.role.value
        }

    # For other roles, get profile and center
    profile = None
    center = None

    if center_id:
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.user_id == user_id,
            LearningCenterProfile.center_id == center_id,
            LearningCenterProfile.is_active == True
        ).first()

        if profile:
            center = db.query(LearningCenter).filter(
                LearningCenter.id == center_id,
                LearningCenter.is_active == True
            ).first()

    if not profile and user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this center"
        )

    return {
        "user": user,
        "profile": profile,
        "center": center,
        "center_id": center_id,
        "role": profile.role_in_center.value if profile else user.role.value
    }


def require_role(required_roles: list):
    """Decorator to require specific roles"""

    def decorator(current_user: dict):
        user_role = current_user.get("role")
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {required_roles}"
            )
        return current_user

    return decorator


def check_center_active(center_id: int, db: Session):
    """Check if learning center is active and has remaining days"""
    from .models import LearningCenter

    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    if not center.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learning center is inactive"
        )

    if center.days_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learning center subscription expired"
        )

    return center


def send_telegram_message(chat_id: str, message: str) -> bool:
    """Send message via Telegram bot"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def generate_verification_code() -> str:
    """Generate 4-digit verification code"""
    return str(random.randint(1000, 9999))


def format_phone(phone: str) -> str:
    """Format phone number to standard format"""
    # Remove all non-digits except +
    phone = re.sub(r'[^\d+]', '', phone)
    if not phone.startswith('+'):
        # Assume Uzbekistan if no country code
        phone = '+998' + phone
    return phone


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))


def validate_uzbek_phone(phone: str) -> bool:
    """Validate Uzbekistan phone number format"""
    # Uzbek numbers: +998 followed by 9 digits
    pattern = r'^\+998\d{9}$'
    return bool(re.match(pattern, phone))


class APIResponse:
    """Standardized API response helper"""

    @staticmethod
    def success(data=None, message="Success"):
        return {
            "success": True,
            "message": message,
            "data": data
        }

    @staticmethod
    def error(message="Error", code=400):
        return {
            "success": False,
            "message": message,
            "error_code": code
        }

    @staticmethod
    def paginated(items, total, page, size):
        return {
            "success": True,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "size": size,
                    "pages": (total + size - 1) // size
                }
            }
        }


def paginate(query, page: int = 1, size: int = 20):
    """Simple pagination helper"""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    offset = (page - 1) * size
    total = query.count()
    items = query.offset(offset).limit(size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }