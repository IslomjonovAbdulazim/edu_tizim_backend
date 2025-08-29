from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.repositories.user import UserRepository


async def get_current_user(
        db: Session = Depends(get_db),
        telegram_id: Optional[str] = Header(None, alias="X-Telegram-ID")
) -> User:
    """
    Get current user from Telegram ID header
    For telegram bot authentication, we use X-Telegram-ID header
    """

    if not telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Telegram ID header required for authentication"
        )

    try:
        telegram_id_int = int(telegram_id)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram ID format"
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_telegram_id(telegram_id_int)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is deactivated"
        )

    return user


async def get_current_verified_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and ensure they are verified"""

    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Phone number verification required"
        )

    return current_user


async def get_admin_user(
        current_user: User = Depends(get_current_verified_user)
) -> User:
    """Get current user and ensure they have admin privileges"""

    if not current_user.has_any_role(["admin", "super_admin"]):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user