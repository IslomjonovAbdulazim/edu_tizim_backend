from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer
from datetime import datetime, timedelta
from .base import BaseModel


class VerificationCode(BaseModel):
    __tablename__ = "verification_codes"

    # Contact info
    telegram_id = Column(BigInteger, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)

    # Verification details
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)

    # Timing
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Attempts tracking
    verification_attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    def __str__(self):
        return f"VerificationCode({self.phone_number}, expires: {self.expires_at})"

    @classmethod
    def create_new(cls, telegram_id: int, phone_number: str, code: str):
        """Create a new verification code with 10 minute expiry"""
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        return cls(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )

    @property
    def is_valid(self):
        """Check if code is still valid for use"""
        return (
            not self.is_used and
            not self.is_expired and
            datetime.utcnow() < self.expires_at and
            self.verification_attempts < self.max_attempts
        )

    def try_verify(self, provided_code: str) -> bool:
        """Attempt to verify the provided code"""
        if not self.is_valid:
            return False

        self.verification_attempts += 1

        if self.code == provided_code:
            self.is_used = True
            self.used_at = datetime.utcnow()
            return True

        # Auto-expire if max attempts reached
        if self.verification_attempts >= self.max_attempts:
            self.is_expired = True

        return False

    @property
    def attempts_remaining(self):
        """Get remaining verification attempts"""
        return max(0, self.max_attempts - self.verification_attempts)