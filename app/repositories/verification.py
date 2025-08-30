from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
from app.models.verification import VerificationCode
from app.repositories.base import BaseRepository


class VerificationRepository(BaseRepository):
    """Verification repository for phone verification system"""

    def __init__(self, db: Session):
        super().__init__(db, VerificationCode)

    def create_verification_code(
            self,
            telegram_id: int,
            phone_number: str,
            code: str,
            expires_in_minutes: int = 10
    ) -> VerificationCode:
        """Create new verification code"""
        # Expire any existing codes for this telegram_id/phone combination
        self.expire_previous_codes(telegram_id, phone_number)

        # Create new code
        verification_code = VerificationCode.create_new(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_in_minutes=expires_in_minutes
        )

        self.db.add(verification_code)
        self._commit()
        self.db.refresh(verification_code)
        return verification_code

    def get_valid_code(self, telegram_id: int, phone_number: str) -> Optional[VerificationCode]:
        """Get valid (not expired, not used) verification code"""
        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.expires_at > datetime.utcnow(),
                VerificationCode.attempts < VerificationCode.max_attempts,
                VerificationCode.is_active == True
            )
        ).order_by(desc(VerificationCode.created_at)).first()

    def verify_code(self, telegram_id: int, phone_number: str, provided_code: str) -> Tuple[
        bool, Optional[VerificationCode]]:
        """Verify the provided code"""
        verification_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_active == True
            )
        ).order_by(desc(VerificationCode.created_at)).first()

        if not verification_code:
            return False, None

        # Use the model's verify method
        is_valid = verification_code.verify(provided_code)
        self._commit()
        self.db.refresh(verification_code)

        return is_valid, verification_code

    def expire_previous_codes(self, telegram_id: int, phone_number: str) -> int:
        """Expire all previous codes for telegram_id/phone combination"""
        previous_codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_active == True
            )
        ).all()

        for code in previous_codes:
            code.is_active = False

        self._commit()
        return len(previous_codes)

    def can_send_new_code(
            self,
            telegram_id: int,
            phone_number: str,
            cooldown_minutes: int = 1
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if user can request a new verification code (rate limiting)"""
        # Check last code creation time
        last_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number
            )
        ).order_by(desc(VerificationCode.created_at)).first()

        if not last_code:
            return True, None

        # Check cooldown period
        cooldown_end = last_code.created_at + timedelta(minutes=cooldown_minutes)
        if datetime.utcnow() < cooldown_end:
            return False, cooldown_end

        # Check daily limit
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= today_start
            )
        ).count()

        daily_limit = 10  # Could be configurable
        if today_count >= daily_limit:
            # Next allowed is tomorrow
            next_allowed = today_start + timedelta(days=1)
            return False, next_allowed

        return True, None

    def is_phone_blocked(self, phone_number: str, hours: int = 24) -> bool:
        """Check if phone number is temporarily blocked due to too many failures"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Count failed attempts in the last 24 hours
        failed_attempts = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at >= cutoff_time,
                VerificationCode.attempts >= VerificationCode.max_attempts,
                VerificationCode.is_used == False
            )
        ).count()

        # Block if more than 5 failed verification codes in 24 hours
        return failed_attempts >= 5

    def get_verification_stats(self, telegram_id: int, phone_number: str) -> Dict[str, Any]:
        """Get verification status and statistics"""
        valid_code = self.get_valid_code(telegram_id, phone_number)

        if valid_code:
            return {
                "has_valid_code": True,
                "expires_at": valid_code.expires_at,
                "attempts_remaining": valid_code.max_attempts - valid_code.attempts,
                "code_id": valid_code.id
            }

        # Check if there's any recent code (even expired/used)
        recent_code = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number
            )
        ).order_by(desc(VerificationCode.created_at)).first()

        return {
            "has_valid_code": False,
            "expires_at": None,
            "attempts_remaining": 0,
            "last_code_at": recent_code.created_at if recent_code else None
        }

    def get_recent_codes(self, telegram_id: int, hours: int = 24) -> List[VerificationCode]:
        """Get recent verification codes for telegram ID"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= cutoff_time
            )
        ).order_by(desc(VerificationCode.created_at)).all()

    def cleanup_expired_codes(self, days_old: int = 7) -> int:
        """Clean up old verification codes"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        old_codes = self.db.query(VerificationCode).filter(
            VerificationCode.created_at < cutoff_date
        ).all()

        # Hard delete old codes
        for code in old_codes:
            self.db.delete(code)

        self._commit()
        return len(old_codes)

    def get_system_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get system-wide verification statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Total codes sent
        total_codes = self.db.query(VerificationCode).filter(
            VerificationCode.created_at >= cutoff_date
        ).count()

        # Successful verifications
        successful_codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.created_at >= cutoff_date,
                VerificationCode.is_used == True
            )
        ).count()

        # Expired codes
        expired_codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.created_at >= cutoff_date,
                VerificationCode.expires_at < datetime.utcnow(),
                VerificationCode.is_used == False
            )
        ).count()

        # Max attempts exceeded
        max_attempts_codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.created_at >= cutoff_date,
                VerificationCode.attempts >= VerificationCode.max_attempts,
                VerificationCode.is_used == False
            )
        ).count()

        # Success rate
        success_rate = (successful_codes / total_codes * 100) if total_codes > 0 else 0

        # Average attempts per successful verification
        avg_attempts_result = self.db.query(func.avg(VerificationCode.attempts)).filter(
            and_(
                VerificationCode.created_at >= cutoff_date,
                VerificationCode.is_used == True
            )
        ).scalar()

        avg_attempts = float(avg_attempts_result) if avg_attempts_result else 0

        return {
            "period_days": days,
            "total_codes_sent": total_codes,
            "successful_verifications": successful_codes,
            "expired_codes": expired_codes,
            "max_attempts_exceeded": max_attempts_codes,
            "success_rate": success_rate,
            "average_attempts_per_success": avg_attempts
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily verification statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query daily counts
        daily_data = self.db.query(
            func.date(VerificationCode.created_at).label('date'),
            func.count(VerificationCode.id).label('codes_sent'),
            func.sum(func.case([(VerificationCode.is_used == True, 1)], else_=0)).label('successful'),
            func.sum(func.case([(VerificationCode.expires_at < datetime.utcnow(), 1)], else_=0)).label('expired')
        ).filter(
            VerificationCode.created_at >= cutoff_date
        ).group_by(
            func.date(VerificationCode.created_at)
        ).order_by(
            func.date(VerificationCode.created_at)
        ).all()

        daily_stats = []
        for row in daily_data:
            success_rate = (row.successful / row.codes_sent * 100) if row.codes_sent > 0 else 0
            daily_stats.append({
                "date": row.date.isoformat(),
                "codes_sent": row.codes_sent,
                "successful_verifications": row.successful,
                "expired_codes": row.expired,
                "success_rate": success_rate
            })

        return daily_stats

    def get_phone_number_stats(self, phone_number: str, days: int = 30) -> Dict[str, Any]:
        """Get statistics for specific phone number"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at >= cutoff_date
            )
        ).order_by(desc(VerificationCode.created_at)).all()

        if not codes:
            return {
                "phone_number": phone_number,
                "period_days": days,
                "total_codes": 0,
                "successful_verifications": 0,
                "is_blocked": False
            }

        successful_count = sum(1 for code in codes if code.is_used)
        failed_count = sum(1 for code in codes if code.attempts >= code.max_attempts and not code.is_used)

        return {
            "phone_number": phone_number,
            "period_days": days,
            "total_codes": len(codes),
            "successful_verifications": successful_count,
            "failed_verifications": failed_count,
            "success_rate": (successful_count / len(codes) * 100) if codes else 0,
            "is_blocked": self.is_phone_blocked(phone_number),
            "last_attempt": codes[0].created_at if codes else None,
            "unique_telegram_ids": len(set(code.telegram_id for code in codes))
        }

    def get_telegram_id_stats(self, telegram_id: int, days: int = 30) -> Dict[str, Any]:
        """Get statistics for specific telegram ID"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        codes = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.created_at >= cutoff_date
            )
        ).order_by(desc(VerificationCode.created_at)).all()

        if not codes:
            return {
                "telegram_id": telegram_id,
                "period_days": days,
                "total_codes": 0,
                "successful_verifications": 0,
                "can_send_new": True
            }

        successful_count = sum(1 for code in codes if code.is_used)
        can_send, _ = self.can_send_new_code(telegram_id, codes[0].phone_number)

        return {
            "telegram_id": telegram_id,
            "period_days": days,
            "total_codes": len(codes),
            "successful_verifications": successful_count,
            "success_rate": (successful_count / len(codes) * 100) if codes else 0,
            "can_send_new": can_send,
            "last_attempt": codes[0].created_at if codes else None,
            "unique_phone_numbers": len(set(code.phone_number for code in codes))
        }

    def force_expire_codes(self, telegram_id: int = None, phone_number: str = None) -> int:
        """Force expire codes (admin function)"""
        query = self.db.query(VerificationCode).filter(
            and_(
                VerificationCode.is_used == False,
                VerificationCode.is_active == True
            )
        )

        if telegram_id:
            query = query.filter(VerificationCode.telegram_id == telegram_id)

        if phone_number:
            query = query.filter(VerificationCode.phone_number == phone_number)

        codes = query.all()

        for code in codes:
            code.is_active = False

        self._commit()
        return len(codes)

    def get_suspicious_activity(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get suspicious verification activity"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Find phone numbers with many failed attempts
        suspicious_phones = self.db.query(
            VerificationCode.phone_number,
            func.count(VerificationCode.id).label('total_attempts'),
            func.sum(func.case([(VerificationCode.is_used == True, 1)], else_=0)).label('successful')
        ).filter(
            VerificationCode.created_at >= cutoff_time
        ).group_by(
            VerificationCode.phone_number
        ).having(
            func.count(VerificationCode.id) >= 5
        ).all()

        # Find telegram IDs with many attempts across different phones
        suspicious_telegram_ids = self.db.query(
            VerificationCode.telegram_id,
            func.count(func.distinct(VerificationCode.phone_number)).label('unique_phones'),
            func.count(VerificationCode.id).label('total_attempts')
        ).filter(
            VerificationCode.created_at >= cutoff_time
        ).group_by(
            VerificationCode.telegram_id
        ).having(
            func.count(func.distinct(VerificationCode.phone_number)) >= 3
        ).all()

        suspicious_activity = []

        # Add suspicious phones
        for phone_data in suspicious_phones:
            success_rate = (phone_data.successful / phone_data.total_attempts * 100)
            if success_rate < 20:  # Less than 20% success rate
                suspicious_activity.append({
                    "type": "suspicious_phone",
                    "phone_number": phone_data.phone_number,
                    "total_attempts": phone_data.total_attempts,
                    "success_rate": success_rate,
                    "risk_level": "high" if success_rate == 0 else "medium"
                })

        # Add suspicious telegram IDs
        for telegram_data in suspicious_telegram_ids:
            suspicious_activity.append({
                "type": "suspicious_telegram_id",
                "telegram_id": telegram_data.telegram_id,
                "unique_phones": telegram_data.unique_phones,
                "total_attempts": telegram_data.total_attempts,
                "risk_level": "high" if telegram_data.unique_phones >= 5 else "medium"
            })

        return suspicious_activity