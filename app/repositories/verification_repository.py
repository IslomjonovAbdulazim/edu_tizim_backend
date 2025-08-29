from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
from app.models.verification_code import VerificationCode
from app.models.user import User
from app.repositories.base_repository import BaseRepository
import random
import string


class VerificationCodeRepository(BaseRepository[VerificationCode]):
    def __init__(self):
        super().__init__(VerificationCode)

    def get_by_telegram_id(self, db: Session, telegram_id: int) -> List[VerificationCode]:
        """Get all verification codes for a Telegram ID"""
        return db.query(VerificationCode).filter(
            VerificationCode.telegram_id == telegram_id
        ).order_by(desc(VerificationCode.created_at)).all()

    def get_by_phone_number(self, db: Session, phone_number: str) -> List[VerificationCode]:
        """Get all verification codes for a phone number"""
        return db.query(VerificationCode).filter(
            VerificationCode.phone_number == phone_number
        ).order_by(desc(VerificationCode.created_at)).all()

    def get_active_code(self, db: Session, telegram_id: int, phone_number: str) -> Optional[VerificationCode]:
        """Get the most recent active verification code for telegram_id and phone combination"""
        now = datetime.utcnow()
        return db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False,
                VerificationCode.expires_at > now,
                VerificationCode.verification_attempts < VerificationCode.max_attempts
            )
        ).order_by(desc(VerificationCode.created_at)).first()

    def create_verification_code(
            self,
            db: Session,
            telegram_id: int,
            phone_number: str,
            expires_in_minutes: int = 10
    ) -> VerificationCode:
        """Create a new verification code"""

        # Generate 6-digit code
        code = self._generate_code()

        # Expire any existing active codes for this telegram_id/phone combination
        self._expire_existing_codes(db, telegram_id, phone_number)

        # Create new verification code
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

        verification_code = VerificationCode.create_new(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_in_minutes=expires_in_minutes
        )

        db.add(verification_code)
        db.commit()
        db.refresh(verification_code)

        return verification_code

    def verify_code(
            self,
            db: Session,
            telegram_id: int,
            phone_number: str,
            provided_code: str
    ) -> Dict[str, Any]:
        """Verify a code and return result details"""
        verification_code = self.get_active_code(db, telegram_id, phone_number)

        if not verification_code:
            return {
                "success": False,
                "message": "No active verification code found",
                "error_code": "NO_ACTIVE_CODE",
                "can_request_new": True
            }

        # Use the model's verify method
        is_valid = verification_code.verify_code(provided_code)

        db.commit()
        db.refresh(verification_code)

        if is_valid:
            return {
                "success": True,
                "message": "Code verified successfully",
                "verification_code_id": verification_code.id,
                "is_used": True
            }
        else:
            attempts_remaining = verification_code.max_attempts - verification_code.verification_attempts
            return {
                "success": False,
                "message": "Invalid verification code",
                "error_code": "INVALID_CODE",
                "attempts_remaining": max(0, attempts_remaining),
                "can_request_new": verification_code.is_expired or attempts_remaining <= 0
            }

    def find_user_by_phone(self, db: Session, phone_number: str, learning_center_id: Optional[int] = None) -> List[
        User]:
        """Find users with this phone number, optionally filtered by learning center"""
        query = db.query(User).filter(User.phone_number == phone_number)

        if learning_center_id:
            query = query.filter(User.learning_center_id == learning_center_id)

        return query.all()

    def get_verification_context(
            self,
            db: Session,
            telegram_id: int,
            phone_number: str
    ) -> Dict[str, Any]:
        """Get context about verification for this telegram_id/phone combination"""

        # Find existing users with this phone number across all learning centers
        existing_users = self.find_user_by_phone(db, phone_number)

        # Check if this telegram_id is already associated with any user
        telegram_user = db.query(User).filter(User.telegram_id == telegram_id).first()

        context = {
            "phone_number": phone_number,
            "telegram_id": telegram_id,
            "existing_users_count": len(existing_users),
            "existing_users": [
                {
                    "user_id": user.id,
                    "learning_center_id": user.learning_center_id,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_active": user.is_active
                }
                for user in existing_users
            ],
            "telegram_already_used": telegram_user is not None,
            "telegram_user": {
                "user_id": telegram_user.id,
                "learning_center_id": telegram_user.learning_center_id,
                "phone_number": telegram_user.phone_number,
                "full_name": telegram_user.full_name
            } if telegram_user else None
        }

        return context

    def get_recent_codes_count(
            self,
            db: Session,
            telegram_id: int,
            phone_number: str,
            hours: int = 24
    ) -> int:
        """Get count of verification codes requested in recent hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.created_at >= cutoff_time
            )
        ).count()

    def is_rate_limited(
            self,
            db: Session,
            telegram_id: int,
            phone_number: str,
            max_requests_per_hour: int = 5,
            max_requests_per_day: int = 10
    ) -> Dict[str, Any]:
        """Check if user is rate limited"""

        # Check hourly limit
        hourly_count = self.get_recent_codes_count(db, telegram_id, phone_number, hours=1)

        # Check daily limit
        daily_count = self.get_recent_codes_count(db, telegram_id, phone_number, hours=24)

        is_limited = (hourly_count >= max_requests_per_hour or daily_count >= max_requests_per_day)

        # Calculate reset time (next hour)
        next_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        return {
            "is_rate_limited": is_limited,
            "hourly_requests": hourly_count,
            "daily_requests": daily_count,
            "max_hourly": max_requests_per_hour,
            "max_daily": max_requests_per_day,
            "reset_time": next_hour,
            "can_request": not is_limited
        }

    def cleanup_expired_codes(self, db: Session, days_old: int = 7) -> int:
        """Delete expired verification codes older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        deleted_count = db.query(VerificationCode).filter(
            or_(
                VerificationCode.expires_at < cutoff_date,
                and_(
                    VerificationCode.is_expired == True,
                    VerificationCode.created_at < cutoff_date
                )
            )
        ).delete()

        db.commit()
        return deleted_count

    def get_verification_statistics(
            self,
            db: Session,
            days: int = 30
    ) -> Dict[str, Any]:
        """Get verification code statistics"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        base_query = db.query(VerificationCode).filter(
            VerificationCode.created_at >= start_date
        )

        total_codes = base_query.count()
        used_codes = base_query.filter(VerificationCode.is_used == True).count()
        expired_codes = base_query.filter(VerificationCode.is_expired == True).count()
        max_attempts_reached = base_query.filter(
            VerificationCode.verification_attempts >= VerificationCode.max_attempts
        ).count()

        # Success rate calculation
        success_rate = (used_codes / total_codes * 100) if total_codes > 0 else 0

        # Average verification time (for successful verifications)
        avg_verification_time = base_query.filter(
            VerificationCode.is_used == True
        ).with_entities(
            func.avg(
                func.extract('epoch', VerificationCode.used_at - VerificationCode.created_at)
            )
        ).scalar() or 0

        # Daily breakdown
        daily_stats = db.query(
            func.date(VerificationCode.created_at).label('date'),
            func.count(VerificationCode.id).label('total'),
            func.sum(func.case([(VerificationCode.is_used == True, 1)], else_=0)).label('verified'),
            func.sum(func.case([(VerificationCode.is_expired == True, 1)], else_=0)).label('expired')
        ).filter(
            VerificationCode.created_at >= start_date
        ).group_by(func.date(VerificationCode.created_at)).order_by('date').all()

        return {
            "period": {
                "start_date": start_date.date(),
                "end_date": end_date.date(),
                "days": days
            },
            "totals": {
                "codes_generated": total_codes,
                "codes_used": used_codes,
                "codes_expired": expired_codes,
                "max_attempts_reached": max_attempts_reached,
                "success_rate": round(success_rate, 2),
                "avg_verification_time_seconds": round(avg_verification_time, 2)
            },
            "daily_breakdown": [
                {
                    "date": str(row.date),
                    "total": row.total,
                    "verified": row.verified,
                    "expired": row.expired,
                    "success_rate": round((row.verified / row.total * 100) if row.total > 0 else 0, 2)
                }
                for row in daily_stats
            ]
        }

    def get_user_verification_history(
            self,
            db: Session,
            telegram_id: Optional[int] = None,
            phone_number: Optional[str] = None,
            limit: int = 50
    ) -> List[VerificationCode]:
        """Get verification history for a user"""
        query = db.query(VerificationCode)

        if telegram_id:
            query = query.filter(VerificationCode.telegram_id == telegram_id)

        if phone_number:
            query = query.filter(VerificationCode.phone_number == phone_number)

        return query.order_by(desc(VerificationCode.created_at)).limit(limit).all()

    def _generate_code(self, length: int = 6) -> str:
        """Generate a random verification code"""
        return ''.join(random.choices(string.digits, k=length))

    def _expire_existing_codes(self, db: Session, telegram_id: int, phone_number: str) -> int:
        """Expire all existing active codes for a telegram_id/phone combination"""
        updated_count = db.query(VerificationCode).filter(
            and_(
                VerificationCode.telegram_id == telegram_id,
                VerificationCode.phone_number == phone_number,
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False
            )
        ).update({
            "is_expired": True
        })

        db.commit()
        return updated_count

    def mark_as_used(self, db: Session, verification_code_id: int) -> Optional[VerificationCode]:
        """Mark a verification code as used"""
        code = self.get(db, verification_code_id)
        if code and not code.is_used:
            code.mark_as_used()
            db.commit()
            db.refresh(code)
        return code

    def extend_expiry(
            self,
            db: Session,
            verification_code_id: int,
            additional_minutes: int
    ) -> Optional[VerificationCode]:
        """Extend the expiry time of a verification code"""
        code = self.get(db, verification_code_id)
        if code and not code.is_used and not code.is_expired:
            code.expires_at += timedelta(minutes=additional_minutes)
            db.commit()
            db.refresh(code)
        return code