from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.models.learning_center import LearningCenter, Branch, Payment
from app.repositories.base import BaseRepository


class LearningCenterRepository(BaseRepository):
    """Learning center repository for business management"""

    def __init__(self, db: Session):
        super().__init__(db, LearningCenter)

    # Basic queries
    def get_by_phone(self, phone_number: str) -> Optional[LearningCenter]:
        """Get learning center by phone number"""
        return self.get_by_field("phone_number", phone_number)

    def get_by_brand_name(self, brand_name: str) -> Optional[LearningCenter]:
        """Get learning center by brand name"""
        return self.get_by_field("brand_name", brand_name)

    # Subscription management
    def get_active_centers(self) -> List[LearningCenter]:
        """Get all active learning centers"""
        return self.db.query(LearningCenter).filter(
            and_(
                LearningCenter.is_active == True,
                LearningCenter.remaining_days > 0
            )
        ).all()

    def get_expired_centers(self) -> List[LearningCenter]:
        """Get learning centers with expired subscriptions"""
        return self.db.query(LearningCenter).filter(
            and_(
                LearningCenter.is_active == True,
                LearningCenter.remaining_days <= 0
            )
        ).all()

    def get_expiring_soon(self, days: int = 7) -> List[LearningCenter]:
        """Get learning centers expiring within specified days"""
        return self.db.query(LearningCenter).filter(
            and_(
                LearningCenter.is_active == True,
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
            # Reactivate if was expired
            if not center.is_active and center.remaining_days > 0:
                center.is_active = True
            self._commit()
            self.db.refresh(center)
        return center

    def deduct_day(self, center_id: int) -> Optional[LearningCenter]:
        """Deduct one day from subscription (daily cron job)"""
        center = self.get(center_id)
        if center and center.remaining_days > 0:
            center.remaining_days -= 1
            # Block if expired
            if center.remaining_days <= 0:
                center.is_active = False
            self._commit()
            self.db.refresh(center)
        return center

    def block_center(self, center_id: int) -> Optional[LearningCenter]:
        """Block learning center (expired subscription)"""
        center = self.get(center_id)
        if center:
            center.is_active = False
            self._commit()
            self.db.refresh(center)
        return center

    def unblock_center(self, center_id: int) -> Optional[LearningCenter]:
        """Unblock learning center"""
        center = self.db.query(LearningCenter).filter(
            LearningCenter.id == center_id
        ).first()
        if center and center.remaining_days > 0:
            center.is_active = True
            self._commit()
            self.db.refresh(center)
        return center

    # Statistics and analytics
    def get_subscription_summary(self, center_id: int) -> Dict[str, Any]:
        """Get subscription summary for center"""
        center = self.get(center_id)
        if not center:
            return {}

        # Calculate expiry date
        expiry_date = None
        if center.remaining_days > 0:
            expiry_date = date.today() + timedelta(days=center.remaining_days)

        return {
            "center_id": center.id,
            "brand_name": center.brand_name,
            "remaining_days": center.remaining_days,
            "is_active": center.is_active,
            "is_expired": center.remaining_days <= 0,
            "expiry_date": expiry_date,
            "total_paid": float(center.total_paid),
            "max_students": center.max_students,
            "max_branches": center.max_branches
        }

    def get_revenue_stats(self, center_id: int = None, days: int = 30) -> Dict[str, Any]:
        """Get revenue statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(Payment).join(LearningCenter)
        if center_id:
            query = query.filter(Payment.learning_center_id == center_id)

        recent_payments = query.filter(Payment.created_at >= cutoff_date).all()

        return {
            "total_revenue": sum(float(p.amount) for p in recent_payments),
            "payment_count": len(recent_payments),
            "average_payment": sum(float(p.amount) for p in recent_payments) / len(
                recent_payments) if recent_payments else 0,
            "total_days_sold": sum(p.days_added for p in recent_payments)
        }

    # Capacity management
    def check_student_capacity(self, center_id: int, current_students: int) -> bool:
        """Check if center can accept more students"""
        center = self.get(center_id)
        return center and current_students < center.max_students

    def check_branch_capacity(self, center_id: int, current_branches: int) -> bool:
        """Check if center can create more branches"""
        center = self.get(center_id)
        return center and current_branches < center.max_branches

    def update_limits(self, center_id: int, max_students: int = None, max_branches: int = None) -> Optional[
        LearningCenter]:
        """Update center limits"""
        center = self.get(center_id)
        if center:
            if max_students is not None:
                center.max_students = max_students
            if max_branches is not None:
                center.max_branches = max_branches
            self._commit()
            self.db.refresh(center)
        return center


class BranchRepository(BaseRepository):
    """Branch repository for location management"""

    def __init__(self, db: Session):
        super().__init__(db, Branch)

    def get_by_center(self, learning_center_id: int) -> List[Branch]:
        """Get all branches for learning center"""
        return self.filter_by(learning_center_id=learning_center_id)

    def get_active_by_center(self, learning_center_id: int) -> List[Branch]:
        """Get active branches for learning center"""
        return self.db.query(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Branch.is_active == True
            )
        ).all()

    def search_branches(self, learning_center_id: int, query: str) -> List[Branch]:
        """Search branches by title or description"""
        return self.db.query(Branch).filter(
            and_(
                Branch.learning_center_id == learning_center_id,
                Branch.is_active == True,
                or_(
                    Branch.title.ilike(f"%{query}%"),
                    Branch.description.ilike(f"%{query}%")
                )
            )
        ).all()

    def get_by_coordinates(self, min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> List[Branch]:
        """Get branches within coordinate bounds"""
        return self.db.query(Branch).filter(
            and_(
                Branch.is_active == True,
                Branch.latitude.between(min_lat, max_lat),
                Branch.longitude.between(min_lng, max_lng)
            )
        ).all()

    def get_branches_with_coordinates(self) -> List[Branch]:
        """Get all branches that have coordinates set"""
        return self.db.query(Branch).filter(
            and_(
                Branch.is_active == True,
                Branch.latitude.isnot(None),
                Branch.longitude.isnot(None)
            )
        ).all()

    def deactivate_branch(self, branch_id: int) -> Optional[Branch]:
        """Deactivate branch"""
        return self.soft_delete(branch_id)

    def get_branch_stats(self, branch_id: int) -> Dict[str, Any]:
        """Get branch statistics"""
        branch = self.get(branch_id)
        if not branch:
            return {}

        # Get related counts (would need to import Group model)
        # For now, return basic info
        return {
            "branch_id": branch.id,
            "title": branch.title,
            "learning_center_id": branch.learning_center_id,
            "has_location": branch.latitude is not None and branch.longitude is not None,
            "coordinates": {
                "latitude": float(branch.latitude) if branch.latitude else None,
                "longitude": float(branch.longitude) if branch.longitude else None
            } if branch.latitude and branch.longitude else None
        }


class PaymentRepository(BaseRepository):
    """Payment repository for financial management"""

    def __init__(self, db: Session):
        super().__init__(db, Payment)

    def get_by_center(self, learning_center_id: int) -> List[Payment]:
        """Get all payments for learning center"""
        return self.db.query(Payment).filter(
            Payment.learning_center_id == learning_center_id
        ).order_by(desc(Payment.payment_date)).all()

    def get_recent_payments(self, learning_center_id: int = None, days: int = 30) -> List[Payment]:
        """Get recent payments"""
        cutoff_date = date.today() - timedelta(days=days)

        query = self.db.query(Payment).filter(Payment.payment_date >= cutoff_date)
        if learning_center_id:
            query = query.filter(Payment.learning_center_id == learning_center_id)

        return query.order_by(desc(Payment.payment_date)).all()

    def get_by_status(self, status: str, learning_center_id: int = None) -> List[Payment]:
        """Get payments by status"""
        query = self.db.query(Payment).filter(Payment.status == status)
        if learning_center_id:
            query = query.filter(Payment.learning_center_id == learning_center_id)

        return query.order_by(desc(Payment.payment_date)).all()

    def get_pending_payments(self) -> List[Payment]:
        """Get all pending payments"""
        return self.get_by_status("pending")

    def mark_payment_completed(self, payment_id: int) -> Optional[Payment]:
        """Mark payment as completed"""
        return self.update(payment_id, {"status": "completed"})

    def mark_payment_failed(self, payment_id: int, reason: str = None) -> Optional[Payment]:
        """Mark payment as failed"""
        update_data = {"status": "failed"}
        if reason:
            update_data["notes"] = reason
        return self.update(payment_id, update_data)

    def get_payment_summary(self, learning_center_id: int = None, start_date: date = None, end_date: date = None) -> \
    Dict[str, Any]:
        """Get payment summary with statistics"""
        query = self.db.query(Payment)

        if learning_center_id:
            query = query.filter(Payment.learning_center_id == learning_center_id)

        if start_date:
            query = query.filter(Payment.payment_date >= start_date)

        if end_date:
            query = query.filter(Payment.payment_date <= end_date)

        payments = query.all()

        # Calculate statistics
        total_amount = sum(float(p.amount) for p in payments)
        total_days = sum(p.days_added for p in payments)
        completed_payments = [p for p in payments if p.status == "completed"]

        return {
            "total_payments": len(payments),
            "total_amount": total_amount,
            "total_days_sold": total_days,
            "completed_payments": len(completed_payments),
            "completed_amount": sum(float(p.amount) for p in completed_payments),
            "pending_payments": len([p for p in payments if p.status == "pending"]),
            "failed_payments": len([p for p in payments if p.status == "failed"]),
            "average_payment": total_amount / len(payments) if payments else 0,
            "average_days_per_payment": total_days / len(payments) if payments else 0
        }

    def get_monthly_revenue(self, learning_center_id: int = None, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly revenue data"""
        # Get payments from last N months
        start_date = date.today().replace(day=1) - timedelta(days=months * 31)

        query = self.db.query(Payment).filter(
            and_(
                Payment.payment_date >= start_date,
                Payment.status == "completed"
            )
        )

        if learning_center_id:
            query = query.filter(Payment.learning_center_id == learning_center_id)

        payments = query.all()

        # Group by month
        monthly_data = {}
        for payment in payments:
            month_key = payment.payment_date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "revenue": 0,
                    "payment_count": 0,
                    "days_sold": 0
                }

            monthly_data[month_key]["revenue"] += float(payment.amount)
            monthly_data[month_key]["payment_count"] += 1
            monthly_data[month_key]["days_sold"] += payment.days_added

        # Sort by month and return as list
        return sorted(monthly_data.values(), key=lambda x: x["month"])

    def create_payment_with_days(self, learning_center_id: int, amount: Decimal, days_added: int,
                                 notes: str = None) -> Payment:
        """Create payment and automatically add days to center"""
        # Create payment
        payment_data = {
            "learning_center_id": learning_center_id,
            "amount": amount,
            "days_added": days_added,
            "payment_date": date.today(),
            "status": "completed"
        }
        if notes:
            payment_data["notes"] = notes

        payment = self.create(payment_data)

        # Add days to learning center
        center_repo = LearningCenterRepository(self.db)
        center_repo.add_payment_days(learning_center_id, days_added, amount)

        return payment