from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta
from app.models import VerificationCode
from app.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[VerificationCode]):
    def __init__(self, db: Session):
        super().__init__(VerificationCode, db)

    def get_valid_code(self, telegram_id: int, phone_number: str) -> Optional[VerificationCode]:
        """Get current valid verification code for telegram ID and phone"""
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False,
                VerificationCode.expires_at > datetime.utcnow()
            )
        ).order_by(desc(VerificationCode.created_at)).first()

    def create_code(self, telegram_id: int, phone_number: str, code: str) -> VerificationCode:
        """Create new verification code (expires previous ones)"""
        # Mark all existing codes as expired
        self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False
            )
        ).update({VerificationCode.is_expired: True})

        # Create new code
        verification_code = VerificationCode.create_new(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code
        )

        self.db.add(verification_code)
        self.db.commit()
        self.db.refresh(verification_code)
        return verification_code

    def verify_code(self, telegram_id: int, phone_number: str, provided_code: str) -> tuple[
        bool, Optional[VerificationCode]]:
        """Verify provided code"""
        verification_code = self.get_valid_code(telegram_id, phone_number)

        if not verification_code:
            return False, None

        success = verification_code.try_verify(provided_code)
        self.db.commit()
        self.db.refresh(verification_code)

        return success, verification_code

    def can_send_code(self, telegram_id: int, phone_number: str) -> tuple[bool, Optional[datetime]]:
        """Check if new code can be sent (1 minute cooldown)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)

        recent_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at > cutoff_time
            )
        ).first()

        if recent_code:
            next_allowed = recent_code.created_at + timedelta(minutes=1)
            return False, next_allowed

        return True, None

    def is_phone_blocked(self, phone_number: str) -> bool:
        """Check if phone is temporarily blocked (5+ failed attempts in 1 hour)"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        failed_attempts = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at > cutoff_time,
                VerificationCode.verification_attempts >= VerificationCode.max_attempts,
                VerificationCode.is_used == False
            )
        ).count()

        return failed_attempts >= 5