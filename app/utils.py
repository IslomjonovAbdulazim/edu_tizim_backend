from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status
from typing import Optional
import requests

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", 30))
BOT_TOKEN = os.getenv("BOT_TOKEN")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        center_id: int = payload.get("center_id")
        if user_id is None:
            return None
        return {"user_id": user_id, "center_id": center_id}
    except JWTError:
        return None


def send_telegram_message(chat_id: str, message: str):
    """Send message via Telegram bot"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message
        }
        response = requests.post(url, json=data)
        return response.status_code == 200
    except:
        return False


def generate_verification_code() -> str:
    """Generate 4-digit verification code"""
    import random
    return str(random.randint(1000, 9999))


def validate_phone(phone: str) -> bool:
    """Basic phone validation"""
    import re
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))


def format_phone(phone: str) -> str:
    """Standardize phone format"""
    # Remove all non-digits except +
    import re
    phone = re.sub(r'[^\d+]', '', phone)
    if not phone.startswith('+'):
        phone = '+' + phone
    return phone


def check_center_active(center_id: int, db):
    """Check if learning center is active"""
    from models import LearningCenter
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center or not center.is_active or center.days_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learning center is inactive or expired"
        )
    return center


def get_user_permissions(user_role: str, center_role: str = None):
    """Get user permissions based on roles"""
    permissions = {
        "can_manage_content": False,
        "can_manage_users": False,
        "can_view_analytics": False,
        "can_manage_payments": False,
        "can_manage_centers": False
    }

    if user_role == "super_admin":
        permissions.update({
            "can_manage_payments": True,
            "can_manage_centers": True,
            "can_view_analytics": True
        })
    elif center_role == "admin":
        permissions.update({
            "can_manage_content": True,
            "can_manage_users": True,
            "can_view_analytics": True
        })
    elif center_role == "teacher":
        permissions.update({
            "can_view_analytics": True
        })

    return permissions


class APIResponse:
    """Standardized API response format"""

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
            "code": code
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