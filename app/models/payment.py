from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Numeric, Text, Date
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime, date


class Payment(BaseModel):
    __tablename__ = "payments"

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="payments")

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)  # Payment amount (e.g., 1500000.00)
    currency = Column(String(3), default="UZS", nullable=False)  # Always UZS (Uzbek Som)
    days_added = Column(Integer, nullable=False)  # Days of service this payment provides

    # Payment information
    payment_date = Column(Date, nullable=False, default=date.today)
    payment_method = Column(String(50), default="manual")  # manual, bank_transfer, card, etc.
    reference_number = Column(String(100))  # Transaction/receipt reference

    # Status
    status = Column(String(20), default="completed", nullable=False)  # pending, completed, cancelled, refunded
    is_processed = Column(Boolean, default=True, nullable=False)  # Has this payment been applied to account?

    # Additional details
    notes = Column(Text)  # Admin notes about this payment
    processed_by = Column(String(100))  # Who entered/processed this payment
    processed_at = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"Payment({self.learning_center.name}, {self.amount:,} UZS, {self.days_added} days)"

    @property
    def days_per_som(self):
        """Calculate how many days per som this payment provides"""
        if self.amount == 0:
            return 0
        return round(float(self.days_added / self.amount), 6)  # Very small number for UZS

    @property
    def is_recent(self):
        """Check if payment was made in last 30 days"""
        if not self.payment_date:
            return False
        days_ago = (date.today() - self.payment_date).days
        return days_ago <= 30

    def mark_as_processed(self, processed_by: str = "system"):
        """Mark payment as processed and applied to account"""
        self.is_processed = True
        self.processed_by = processed_by
        self.processed_at = datetime.utcnow()

    def cancel_payment(self, reason: str = None):
        """Cancel/void this payment"""
        self.status = "cancelled"
        if reason:
            self.notes = f"{self.notes or ''}\nCancelled: {reason}".strip()

    def refund_payment(self, reason: str = None):
        """Mark payment as refunded"""
        self.status = "refunded"
        if reason:
            self.notes = f"{self.notes or ''}\nRefunded: {reason}".strip()