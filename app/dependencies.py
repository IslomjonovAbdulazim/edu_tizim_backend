from __future__ import annotations
from typing import Optional, Iterable, Callable, Annotated, Union
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole  # UserRole is an Enum[str] in your models
from app.services import UserService


# -------- helpers ------------------------------------------------------------
def _parse_telegram_id(raw: Optional[str]) -> int:
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram ID header required for authentication",
        )
    try:
        tid = int(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram ID format",
        )
    if tid <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram ID value",
        )
    return tid


def _has_any_role(user: User, roles: Iterable[Union[str, UserRole]]) -> bool:
    """Check user roles across all centers (active roles only).
    Uses model helper if present; otherwise inspects center_roles.
    """
    maybe = getattr(user, "has_any_role", None)
    if callable(maybe):
        return bool(maybe([r.value if isinstance(r, UserRole) else str(r) for r in roles]))

    wanted = {(r.value if isinstance(r, UserRole) else str(r)).lower() for r in roles}
    user_roles = set()

    if hasattr(user, "center_roles") and user.center_roles:
        for cr in user.center_roles:
            if getattr(cr, "is_active", True):
                role_value = getattr(cr, "role", None)
                if role_value is None:
                    continue
                role_str = role_value.value if isinstance(role_value, UserRole) else str(role_value)
                user_roles.add(role_str.lower())

    return bool(user_roles.intersection(wanted))


# -------- core dependencies --------------------------------------------------
def get_current_user(
    db: Session = Depends(get_db),
    telegram_id: Annotated[Optional[str], Header(None, alias="X-Telegram-ID")] = None,
) -> User:
    """Authenticate by the `X-Telegram-ID` header and return the active User.
    - 401 when missing/invalid header or user not found
    - 401 when user is deactivated
    """
    tid = _parse_telegram_id(telegram_id)

    user = UserService(db).get_by_telegram(tid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is deactivated")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    telegram_id: Annotated[Optional[str], Header(None, alias="X-Telegram-ID")] = None,
) -> Optional[User]:
    """Same as get_current_user but returns None if header missing."""
    if not telegram_id:
        return None
    tid = _parse_telegram_id(telegram_id)
    return UserService(db).get_by_telegram(tid)


def get_current_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has completed phone verification."""
    if not getattr(current_user, "is_verified", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phone number verification required")
    return current_user


def require_roles(*roles: Union[str, UserRole]) -> Callable[[User], User]:
    """Ensure the user has ANY of the given roles (across any center)."""
    def _dep(current_user: User = Depends(get_current_verified_user)) -> User:
        if not _has_any_role(current_user, roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return _dep


def require_admin(current_user: User = Depends(get_current_verified_user)) -> User:
    """Convenience dependency for admin/super_admin."""
    if not _has_any_role(current_user, [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_center_role(*roles: Union[str, UserRole]):
    """Ensure the user has one of the roles **in the route's center**.
    Route must include a `center_id: int` param.
    """
    def _dep(center_id: int, current_user: User = Depends(get_current_verified_user)) -> User:
        if hasattr(current_user, "get_role_in_center") and callable(getattr(current_user, "get_role_in_center")):
            role = current_user.get_role_in_center(center_id)
            role = role.value if isinstance(role, UserRole) else role
            if role and any((r.value if isinstance(r, UserRole) else str(r)).lower() == str(role).lower() for r in roles):
                return current_user
        else:
            for cr in getattr(current_user, "center_roles", []) or []:
                if getattr(cr, "is_active", True) and getattr(cr, "learning_center_id", None) == center_id:
                    r = getattr(cr, "role", None)
                    r = r.value if isinstance(r, UserRole) else r
                    if r and any((x.value if isinstance(x, UserRole) else str(x)).lower() == str(r).lower() for x in roles):
                        return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Required center role not present")
    return _dep
