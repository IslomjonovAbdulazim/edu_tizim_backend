import jwt
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..config import settings
from ..database import get_redis
from ..models import User
from .sms_service import sms_service


class AuthService:
    def __init__(self):
        self.redis = get_redis()
    
    async def send_verification_code(self, phone: str, learning_center_id: int) -> bool:
        """Send verification code to phone number"""
        # Generate verification code
        if settings.TEST_VERIFICATION_CODE and phone.endswith("0000"):
            # Use test code for testing
            code = settings.TEST_VERIFICATION_CODE
        else:
            code = self._generate_verification_code()
        
        # Store in Redis with 5 minutes expiry
        key = f"verification:{phone}:{learning_center_id}"
        self.redis.setex(key, 300, code)  # 5 minutes
        
        # Send SMS
        return await sms_service.send_verification_code(phone, code)
    
    def verify_code_and_login(
        self, 
        phone: str, 
        code: str, 
        learning_center_id: int, 
        db: Session
    ) -> Tuple[User, str, str]:
        """Verify code and return user with tokens"""
        # Check verification code
        key = f"verification:{phone}:{learning_center_id}"
        stored_code = self.redis.get(key)
        
        if not stored_code or stored_code != code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )
        
        # Get or create user
        user = db.query(User).filter(
            User.phone == phone,
            User.learning_center_id == learning_center_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete verification code
        self.redis.delete(key)
        
        # Generate tokens
        access_token = self._create_access_token(user.id)
        refresh_token = self._create_refresh_token(user.id)
        
        return user, access_token, refresh_token
    
    def refresh_access_token(self, refresh_token: str, db: Session) -> str:
        """Generate new access token from refresh token"""
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            user_id: int = payload.get("sub")
            token_type: str = payload.get("type")
            
            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            return self._create_access_token(user.id)
            
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    def _generate_verification_code(self) -> str:
        """Generate 4-digit verification code"""
        return ''.join(random.choices(string.digits, k=4))
    
    def _create_access_token(self, user_id: int) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "type": "access",
            "exp": expire
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    def _create_refresh_token(self, user_id: int) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "type": "refresh", 
            "exp": expire
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Singleton instance
auth_service = AuthService()