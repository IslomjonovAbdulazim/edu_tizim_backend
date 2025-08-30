from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.verification import VerificationCode
from app.repositories.base import BaseRepository
from .base import BaseService


class VerificationService(BaseService[VerificationCode]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[VerificationCode](db, VerificationCode)

    def create_code(self, user_id: int, code: str, *, ttl_minutes: int = 10, channel: str = "sms") -> VerificationCode:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=ttl_minutes)
        return self.repo.create({
            "user_id": user_id,
            "code": code,
            "channel": channel,
            "expires_at": expires_at,
            "is_used": False,
            "attempts": 0,
        })

    def verify(self, user_id: int, code: str) -> bool:
        vc = (
            self.db.query(VerificationCode)
            .filter(and_(VerificationCode.user_id == user_id, VerificationCode.is_active.is_(True)))
            .order_by(VerificationCode.created_at.desc())
            .first()
        )
        if not vc:
            return False

        now = datetime.now(tz=timezone.utc)
        if vc.is_used or (vc.expires_at and now > vc.expires_at):
            return False

        if vc.code == code:
            vc.is_used = True
            self.db.commit()
            return True

        vc.attempts = (vc.attempts or 0) + 1
        self.db.commit()
        return False
