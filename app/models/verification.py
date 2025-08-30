from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer
from datetime import datetime, timedelta
from .base import BaseModel


class VerificationCode(BaseModel):
    __tablename__ = "verification_codes"

    # Contact info (globally unique verification)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)

    # Verification details
    code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)

    # Timing
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Attempts tracking
    verification_attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Rate limiting: prevent spam for same phone/telegram combination
    # Multiple codes allowed over time (expired/used codes remain for history)

    def __str__(self):
        return f"VerificationCode({self.phone_number}, {self.code[:2]}**)"

    @classmethod
    def create_new(cls, telegram_id: int, phone_number: str, code: str, expires_in_minutes: int = 10):
        """Create a new verification code"""
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        return cls(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )

    @property
    def is_valid(self):
        """Check if code is still valid"""
        now = datetime.utcnow()
        return (
                not self.is_used and
                not self.is_expired and
                now < self.expires_at and
                self.verification_attempts < self.max_attempts
        )

    @property
    def time_remaining_minutes(self) -> int:
        """Get remaining minutes before expiration"""
        if self.expires_at <= datetime.utcnow():
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))

    @property
    def attempts_remaining(self) -> int:
        """Get remaining verification attempts"""
        return max(0, self.max_attempts - self.verification_attempts)

    def verify_code(self, provided_code: str) -> bool:
        """Verify the provided code"""
        # Input validation
        if not provided_code or not provided_code.strip():
            return False

        # Case-insensitive comparison and strip whitespace
        provided_code = provided_code.strip()

        if not self.is_valid:
            return False

        self.verification_attempts += 1

        if self.code == provided_code:
            self.is_used = True
            self.used_at = datetime.utcnow()
            return True

        # Mark as expired if max attempts reached
        if self.verification_attempts >= self.max_attempts:
            self.is_expired = True

        return False

    def expire_code(self):
        """Manually expire the code"""
        self.is_expired = True

    def is_recently_created(self, minutes: int = 1) -> bool:
        """Check if code was created within the specified minutes (for rate limiting)"""
        created_cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return self.created_at > created_cutoff

    @classmethod
    def cleanup_expired_codes(cls, session, days_old: int = 7):
        """Class method to clean up old verification codes"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        return session.query(cls).filter(cls.created_at < cutoff_date).delete()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'telegram_id': self.telegram_id,
            'phone_number': self.phone_number,
            'is_used': self.is_used,
            'is_expired': self.is_expired,
            'expires_at': self.expires_at.isoformat(),
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'verification_attempts': self.verification_attempts,
            'max_attempts': self.max_attempts,
            'is_valid': self.is_valid,
            'time_remaining_minutes': self.time_remaining_minutes,
            'attempts_remaining': self.attempts_remaining
        }