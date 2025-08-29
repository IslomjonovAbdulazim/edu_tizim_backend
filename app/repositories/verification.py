from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta
from app.models import VerificationCode
from app.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[VerificationCode]):
    def __init__(self, db: Session):
        super().__init__(VerificationCode, db)

    def get_by_telegram_phone(self, telegram_id: int, phone_number: str) -> Optional[VerificationCode]:
        """Get latest verification code for telegram ID and phone"""
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number
            )
        ).order_by(desc(VerificationCode.created_at)).first()

    def get_valid_code(self, telegram_id: int, phone_number: str) -> Optional[VerificationCode]:
        """Get valid (non-expired, non-used) verification code"""
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False,
                VerificationCode.expires_at > datetime.utcnow()
            )
        ).order_by(desc(VerificationCode.created_at)).first()

    def create_verification_code(
            self,
            telegram_id: int,
            phone_number: str,
            code: str,
            expires_in_minutes: int = 10
    ) -> VerificationCode:
        """Create new verification code"""
        # Expire all previous codes for this telegram_id and phone
        self.expire_previous_codes(telegram_id, phone_number)

        # Create new code
        verification_code = VerificationCode.create_new(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_in_minutes=expires_in_minutes
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

        success = verification_code.verify_code(provided_code)
        self.db.commit()
        self.db.refresh(verification_code)

        return success, verification_code

    def expire_previous_codes(self, telegram_id: int, phone_number: str) -> int:
        """Expire all previous codes for telegram ID and phone"""
        expired_count = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_expired == False,
                VerificationCode.is_used == False
            )
        ).update({
            VerificationCode.is_expired: True
        })

        self.db.commit()
        return expired_count

    def get_recent_codes(self, telegram_id: int, hours: int = 1) -> List[VerificationCode]:
        """Get codes sent to telegram ID in recent hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= cutoff_time
            )
        ).order_by(desc(VerificationCode.created_at)).all()

    def can_send_new_code(self, telegram_id: int, phone_number: str, cooldown_minutes: int = 1) -> tuple[
        bool, Optional[datetime]]:
        """Check if new code can be sent (rate limiting)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        recent_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at > cutoff_time
            )
        ).first()

        if recent_code:
            next_allowed = recent_code.created_at + timedelta(minutes=cooldown_minutes)
            return False, next_allowed

        return True, None

    def cleanup_expired_codes(self, days_old: int = 7) -> int:
        """Clean up old expired verification codes"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = self.db.query(VerificationCode).filter(
            VerificationCode.created_at < cutoff_date
        ).delete()

        self.db.commit()
        return deleted_count

    def get_verification_stats(self, telegram_id: int, phone_number: str) -> dict:
        """Get verification statistics for user"""
        # Total attempts
        total_codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number
            )
        ).count()

        # Successful verifications
        successful = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == True
            )
        ).count()

        # Recent attempts (last hour)
        recent_attempts = len(self.get_recent_codes(telegram_id, hours=1))

        # Current valid code
        valid_code = self.get_valid_code(telegram_id, phone_number)

        return {
            'total_codes_sent': total_codes,
            'successful_verifications': successful,
            'recent_attempts': recent_attempts,
            'has_valid_code': valid_code is not None,
            'attempts_remaining': valid_code.max_attempts - valid_code.verification_attempts if valid_code else 0,
            'expires_at': valid_code.expires_at if valid_code else None
        }

    def block_phone_temporarily(self, phone_number: str, hours: int = 24) -> None:
        """Block phone number temporarily by creating expired codes (rate limiting)"""
        # This is a simple implementation - you might want a separate blocking table
        pass

    def is_phone_blocked(self, phone_number: str) -> bool:
        """Check if phone number is temporarily blocked"""
        # Check if too many failed attempts recently
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        failed_attempts = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at > cutoff_time,
                VerificationCode.verification_attempts >= VerificationCode.max_attempts,
                VerificationCode.is_used == False
            )
        ).count()

        return failed_attempts >= 5  # Block after 5 failed attempts in an hour