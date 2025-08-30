from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer
from datetime import datetime, timedelta
from .base import BaseModel


class VerificationCode(BaseModel):
    __tablename__ = "verification_codes"

    # Contact info
    telegram_id = Column(BigInteger, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)

    # Simple verification
    code = Column(String(6), nullable=False)  # 6-digit code
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Basic attempt tracking
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    def __str__(self):
        return f"VerificationCode({self.phone_number})"

    @classmethod
    def create_new(cls, telegram_id: int, phone_number: str, code: str, expires_in_minutes: int = 10):
        """Create a new verification code"""
        return cls(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        )

    @property
    def is_valid(self):
        """Check if code is still valid"""
        return (
                not self.is_used and
                datetime.utcnow() < self.expires_at and
                self.attempts < self.max_attempts
        )

    def verify(self, provided_code: str) -> bool:
        """Verify the provided code"""
        self.attempts += 1

        if self.is_valid and self.code == provided_code.strip():
            self.is_used = True
            return True
        return False