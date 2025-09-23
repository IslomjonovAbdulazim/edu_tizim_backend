from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional
import jwt

from .database import get_db
from .config import settings
from .models.user import User
from .services import cache_service


security = HTTPBearer()


async def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id: int = int(user_id_str)
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Super admin check (user_id = 0)
    if user_id == 0:
        # Return a mock user object for super admin
        class SuperAdmin:
            id = 0
            role = "super_admin"
            is_active = True
            learning_center_id = None
        return SuperAdmin()
    
    # Try to get user from cache first
    cached_user = await cache_service.get_user(user_id)
    if cached_user:
        # Create user object from cached data
        user = User()
        for key, value in cached_user.items():
            setattr(user, key, value)
    else:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if user:
            # Cache user data for 30 minutes
            user_dict = {
                "id": user.id,
                "phone": user.phone,
                "name": user.name,
                "role": user.role,
                "learning_center_id": user.learning_center_id,
                "coins": user.coins,
                "is_active": user.is_active
            }
            await cache_service.set_user(user_id, user_dict, ttl=1800)
    
    if user is None:
        raise credentials_exception
    
    # Skip payment check for super admin (they have system-wide access)
    if getattr(user, 'role', None) == "super_admin":
        return user
    
    # Check if learning center is paid (for regular users only)
    from .models import LearningCenter
    learning_center = db.query(LearningCenter).filter(
        LearningCenter.id == user.learning_center_id
    ).first()
    
    if not learning_center or not learning_center.is_paid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Learning center subscription expired"
        )
    
    return user


async def get_super_admin_user(current_user = Depends(get_current_user)):
    """Require super admin permissions"""
    if getattr(current_user, 'role', None) != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_teacher_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_student_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["admin", "teacher", "student"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user