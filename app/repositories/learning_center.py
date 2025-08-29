from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from decimal import Decimal
from app.models import LearningCenter, Branch, Payment
from app.repositories.base import BaseRepository


class LearningCenterRepository(BaseRepository[LearningCenter]):
    def __init__(self, db: Session):
        super().__init__(LearningCenter, db)

    def get_by_phone(self, phone_number: str) -> Optional[LearningCenter]:
        """Get learning center by phone number"""
        return self.db.query(LearningCenter).filter(
            LearningCenter.phone_number == phone_number
        ).first()

    def get_active_centers(self) -> List[LearningCenter]:
        """Get all active learning centers"""
        return self.db.query(LearningCenter).filter(
            LearningCenter.is_active == True
        ).all()

    def get_expired_centers(self) -> List[LearningCenter]:
        """Get learning centers with expired subscriptions"""
        return self.db.query(LearningCenter).filter(
            LearningCenter.remaining_days <= 0
        ).all()

    def get_expiring_soon(self, days: int = 7) -> List[LearningCenter]:
        """Get learning centers expiring within specified days"""
        return self.db.query(LearningCenter).filter(
            and_(
                LearningCenter.remaining_days > 0,
                LearningCenter.remaining_days <= days
            )
        ).all()

    def add_payment_days(self, center_id: int, days: int, amount: Decimal) -> Optional[LearningCenter]:
        """Add days to learning center subscription"""
        center = self.get(center_id)
        if center:
            center.remaining_days += days
            center.total_paid += amount
            if center.remaining_days > 0:
                center.is_active = True
            self.db.commit()
            self.db.refresh(center)
        return center

    def deduct_day(self, center_id: int) -> Optional[LearningCenter]:
        """Deduct one day from subscription (for daily cron job)"""
        center = self.get(center_id)
        if center and center.remaining_days > 0:
            center.remaining_days -= 1
            if center.remaining_days <= 0:
                center.is_active = False
            self.db.commit()
            self.db.refresh(center)
        return center

    def block_center(self, center_id: int) -> Optional[LearningCenter]:
        """Block learning center (set inactive)"""
        center = self.get(center_id)
        if center:
            center.is_active = False
            self.db.commit()
            self.db.refresh(center)
        return center


class BranchRepository(BaseRepository[Branch]):
    def __init__(self, db: Session):
        super().__init__(Branch, db)

    def get_by_center(self, learning_center_id: int) -> List[Branch]:
        """Get all branches for learning center"""
        return self.db.query(Branch).filter(
            Branch.learning_center_id == learning_center_id
        ).all()

    def get_active_by_center(self, learning_center_id: int) -> List[Branch]:
        """Get active branches for learning center"""
        return self.db.query(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Branch.is_active == True
            )
        ).all()

    def get_by_coordinates(self, lat_min: float, lat_max: float,
                          lng_min: float, lng_max: float) -> List[Branch]:
        """Get branches within coordinate bounds"""
        return self.db.query(Branch).filter(
            and_(
                Branch.latitude.between(lat_min, lat_max),
                Branch.longitude.between(lng_min, lng_max),
                Branch.is_active == True
            )
        ).all()

    def deactivate_branch(self, branch_id: int) -> Optional[Branch]:
        """Deactivate branch"""
        branch = self.get(branch_id)
        if branch:
            branch.is_active = False
            self.db.commit()
            self.db.refresh(branch)
        return branch


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: Session):
        super().__init__(Payment, db)

    def get_by_center(self, learning_center_id: int) -> List[Payment]:
        """Get all payments for learning center"""
        return self.db.query(Payment).filter(
            Payment.learning_center_id == learning_center_id
        ).order_by(Payment.payment_date.desc()).all()

    def get_recent_payments(self, learning_center_id: int, days: int = 30) -> List[Payment]:
        """Get recent payments for learning center"""
        cutoff_date = date.today() - timedelta(days=days)
        return self.db.query(Payment).filter(
            and_(
                Payment.learning_center_id == learning_center_id,
                Payment.payment_date >= cutoff_date
            )
        ).order_by(Payment.payment_date.desc()).all()

    def get_payments_by_status(self, status: str) -> List[Payment]:
        """Get payments by status"""
        return self.db.query(Payment).filter(Payment.status == status).all()

    def get_total_paid(self, learning_center_id: int) -> Decimal:
        """Get total amount paid by learning center"""
        result = self.db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.learning_center_id == learning_center_id,
                Payment.status == "completed"
            )
        ).scalar()
        return result or Decimal('0.00')

    def cancel_payment(self, payment_id: int, reason: str = None) -> Optional[Payment]:
        """Cancel a payment"""
        payment = self.get(payment_id)
        if payment:
            payment.status = "cancelled"
            if reason:
                payment.notes = f"{payment.notes or ''}\nCancelled: {reason}".strip()
            self.db.commit()
            self.db.refresh(payment)
        return payment