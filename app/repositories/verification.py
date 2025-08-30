from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
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
        # FIXED: Expire all previous codes for this telegram_id and phone
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

    def verify_code(self, telegram_id: int, phone_number: str, provided_code: str) -> Tuple[
        bool, Optional[VerificationCode]]:
        """Verify provided code"""
        # FIXED: Input validation
        if not provided_code or not provided_code.strip():
            return False, None

        verification_code = self.get_valid_code(telegram_id, phone_number)

        if not verification_code:
            return False, None

        success = verification_code.verify_code(provided_code.strip())

        # FIXED: Always commit and refresh after verification attempt
        self.db.commit()
        self.db.refresh(verification_code)

        return success, verification_code

    def expire_previous_codes(self, telegram_id: int, phone_number: str) -> int:
        """Expire all previous codes for telegram ID and phone"""
        try:
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
        except Exception as e:
            self.db.rollback()
            raise e

    def get_recent_codes(self, telegram_id: int, hours: int = 1) -> List[VerificationCode]:
        """Get codes sent to telegram ID in recent hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= cutoff_time
            )
        ).order_by(desc(VerificationCode.created_at)).all()

    def can_send_new_code(self, telegram_id: int, phone_number: str, cooldown_minutes: int = 1) -> Tuple[
        bool, Optional[datetime]]:
        """Check if new code can be sent (rate limiting)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

        recent_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at > cutoff_time
            )
        ).order_by(desc(VerificationCode.created_at)).first()

        if recent_code:
            next_allowed = recent_code.created_at + timedelta(minutes=cooldown_minutes)
            return False, next_allowed

        return True, None

    def cleanup_expired_codes(self, days_old: int = 7) -> int:
        """Clean up old expired verification codes"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = self.db.query(VerificationCode).filter(
                VerificationCode.created_at < cutoff_date
            ).delete()

            self.db.commit()
            return deleted_count
        except Exception as e:
            self.db.rollback()
            raise e

    def get_verification_stats(self, telegram_id: int, phone_number: str) -> dict:
        """Get verification statistics for user"""
        try:
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
                'attempts_remaining': valid_code.attempts_remaining if valid_code else 0,
                'expires_at': valid_code.expires_at if valid_code else None,
                'time_remaining_minutes': valid_code.time_remaining_minutes if valid_code else 0
            }
        except Exception as e:
            # FIXED: Handle database errors gracefully
            return {
                'total_codes_sent': 0,
                'successful_verifications': 0,
                'recent_attempts': 0,
                'has_valid_code': False,
                'attempts_remaining': 0,
                'expires_at': None,
                'time_remaining_minutes': 0,
                'error': str(e)
            }

    def is_phone_blocked(self, phone_number: str) -> bool:
        """Check if phone number is temporarily blocked"""
        try:
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

            # FIXED: Configurable blocking threshold
            blocking_threshold = 5  # Block after 5 failed attempts in an hour
            return failed_attempts >= blocking_threshold

        except Exception:
            # FIXED: If there's a database error, don't block (fail open)
            return False

    # FIXED: Additional helper methods for better functionality

    def get_codes_by_phone(self, phone_number: str, hours: int = 24) -> List[VerificationCode]:
        """Get all recent codes for a phone number (admin function)"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at >= cutoff_time
            )
        ).order_by(desc(VerificationCode.created_at)).all()

    def count_daily_attempts(self, telegram_id: int) -> int:
        """Count verification attempts for telegram ID today"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= today
            )
        ).count()

    def count_hourly_attempts(self, telegram_id: int) -> int:
        """Count verification attempts for telegram ID in the last hour"""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= hour_ago
            )
        ).count()

    def is_user_rate_limited(self, telegram_id: int, max_hourly: int = 5, max_daily: int = 10) -> Tuple[bool, str]:
        """Check if user has exceeded rate limits"""
        try:
            hourly_count = self.count_hourly_attempts(telegram_id)
            daily_count = self.count_daily_attempts(telegram_id)

            if hourly_count >= max_hourly:
                return True, f"Hourly limit exceeded ({hourly_count}/{max_hourly}). Try again later."

            if daily_count >= max_daily:
                return True, f"Daily limit exceeded ({daily_count}/{max_daily}). Try again tomorrow."

            return False, ""

        except Exception:
            # If there's an error checking limits, don't rate limit (fail open)
            return False, ""

    def get_success_rate(self, phone_number: str, days: int = 7) -> float:
        """Get verification success rate for phone number over specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            total_codes = self.db.query(VerificationCode).filter(
                and_(
                    VerificationCode.phone_number == phone_number,
                    VerificationCode.created_at >= cutoff_date
                )
            ).count()

            successful_codes = self.db.query(VerificationCode).filter(
                and_(
                    VerificationCode.phone_number == phone_number,
                    VerificationCode.created_at >= cutoff_date,
                    VerificationCode.is_used == True
                )
            ).count()

            return (successful_codes / total_codes * 100) if total_codes > 0 else 0.0

        except Exception:
            return 0.0

    def force_expire_all_codes(self, telegram_id: int, phone_number: str) -> int:
        """Force expire all codes for user (admin emergency function)"""
        try:
            expired_count = self.db.query(VerificationCode).filter(
                and_(
                    VerificationCode.telegram_id == telegram_id,
                    VerificationCode.phone_number == phone_number,
                    VerificationCode.is_expired == False
                )
            ).update({
                VerificationCode.is_expired: True
            })

            self.db.commit()
            return expired_count
        except Exception as e:
            self.db.rollback()
            raise e

    def get_system_stats(self) -> dict:
        """Get system-wide verification statistics"""
        try:
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)

            total_codes = self.db.query(VerificationCode).count()
            today_codes = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= today
            ).count()
            week_codes = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= week_ago
            ).count()

            successful_today = self.db.query(VerificationCode).filter(
                and_(
                    VerificationCode.created_at >= today,
                    VerificationCode.is_used == True
                )
            ).count()

            active_codes = self.db.query(VerificationCode).filter(
                and_(
                    VerificationCode.is_used == False,
                    VerificationCode.is_expired == False,
                    VerificationCode.expires_at > now
                )
            ).count()

            return {
                'total_codes': total_codes,
                'today_codes': today_codes,
                'week_codes': week_codes,
                'successful_today': successful_today,
                'active_codes': active_codes,
                'success_rate_today': (successful_today / today_codes * 100) if today_codes > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}