from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer, Index, CheckConstraint
from sqlalchemy import MetaData
# SQLAlchemy naming convention to stabilize Alembic diffs
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

from datetime import datetime, timedelta
from .base import BaseModel


class VerificationCode(BaseModel):
    __tablename__ = "verification_codes"

    # Contact info with validation
    telegram_id = Column(BigInteger, nullable=False)
    phone_number = Column(String(20), nullable=False)

    # Verification details
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    # Simple attempt tracking
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint('telegram_id > 0', name='chk_telegram_positive'),
        CheckConstraint("length(phone_number) >= 10", name='chk_phone_length'),
        CheckConstraint("length(code) = 6", name='chk_code_length'),
        CheckConstraint('attempts >= 0', name='chk_attempts_positive'),
        CheckConstraint('max_attempts > 0', name='chk_max_attempts_positive'),
        CheckConstraint('attempts <= max_attempts', name='chk_attempts_not_exceed'),
        Index('idx_verificationcode_telegram_phone', 'telegram_id', 'phone_number'),
        Index('idx_verificationcode_expires_used', 'expires_at', 'is_used'),
    )

    def __str__(self):
        return f"VerificationCode({self.phone_number})"

    @classmethod
    def create_new(cls, telegram_id: int, phone_number: str, code: str, expires_in_minutes: int = 10):
        """Create a new verification code"""
        return cls(
            telegram_id=telegram_id,
            phone_number=phone_number,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            is_active=True  # Use consistent pattern from BaseModel
        )

    @property
    def is_valid(self):
        """Check if code is still valid for use"""
        return (
            self.is_active and
            not self.is_used and
            datetime.utcnow() < self.expires_at and
            self.attempts < self.max_attempts
        )

    @property
    def is_expired(self):
        """Check if code has expired"""
        return datetime.utcnow() >= self.expires_at

    def verify(self, provided_code: str) -> bool:
        """Verify the provided code"""
#         self.attempts += 1  # moved to increment only on failed attempts

        if self.is_valid and self.code == provided_code.strip():
            self.is_used = True
            return True
        return False

    @property
    def can_retry(self) -> bool:
        """Check if user can still attempt verification"""
        return self.attempts < self.max_attempts and not self.is_expired and self.is_active