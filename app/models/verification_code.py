from datetime import datetime, timedelta
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VerificationCode(BaseModel):
    __tablename__ = "verification_codes"

    # Telegram info
    telegram_id = Column(BigInteger, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)

    # Verification code
    code = Column(String(6), nullable=False)  # 6-digit code
    is_used = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)

    # Timing
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Attempts tracking
    verification_attempts = Column(String(10), nullable=False, default=0)
    max_attempts = Column(String(10), nullable=False, default=3)

    def __str__(self):
        return f"VerificationCode(phone='{self.phone_number}', code='{self.code}')"

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

    def mark_as_used(self):
        """Mark code as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()

    def mark_as_expired(self):
        """Mark code as expired"""
        self.is_expired = True

    def increment_attempts(self):
        """Increment verification attempts"""
        self.verification_attempts += 1

        # Mark as expired if max attempts reached
        if self.verification_attempts >= self.max_attempts:
            self.mark_as_expired()

    def verify_code(self, provided_code: str) -> bool:
        """Verify the provided code"""
        if not self.is_valid:
            return False

        self.increment_attempts()

        if self.code == provided_code:
            self.mark_as_used()
            return True

        return False
