from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.models.payment import Payment
from app.models.learning_center import LearningCenter
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)

    def get_by_learning_center(self, db: Session, learning_center_id: int,
                               skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get payments by learning center"""
        return db.query(Payment).filter(
            Payment.learning_center_id == learning_center_id
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()

    def get_recent_payments(self, db: Session, days: int = 30,
                            skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get recent payments"""
        cutoff_date = date.today() - timedelta(days=days)

        return db.query(Payment).filter(
            Payment.payment_date >= cutoff_date
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()

    def get_by_status(self, db: Session, status: str,
                      skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get payments by status"""
        return db.query(Payment).filter(
            Payment.status == status
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()

    def get_by_payment_method(self, db: Session, payment_method: str,
                              skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get payments by payment method"""
        return db.query(Payment).filter(
            Payment.payment_method == payment_method
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()

    def search_payments(self, db: Session, filters: Dict[str, Any],
                        skip: int = 0, limit: int = 100) -> List[Payment]:
        """Search payments with multiple filters"""
        query = db.query(Payment).options(joinedload(Payment.learning_center))

        # Learning center filter
        if filters.get("learning_center_id"):
            query = query.filter(Payment.learning_center_id == filters["learning_center_id"])

        # Status filter
        if filters.get("status"):
            query = query.filter(Payment.status == filters["status"])

        # Payment method filter
        if filters.get("payment_method"):
            query = query.filter(Payment.payment_method == filters["payment_method"])

        # Date range filters
        if filters.get("date_from"):
            query = query.filter(Payment.payment_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(Payment.payment_date <= filters["date_to"])

        # Amount range filters
        if filters.get("amount_min"):
            query = query.filter(Payment.amount >= filters["amount_min"])
        if filters.get("amount_max"):
            query = query.filter(Payment.amount <= filters["amount_max"])

        # Reference number search
        if filters.get("reference_number"):
            query = query.filter(Payment.reference_number.ilike(f"%{filters['reference_number']}%"))

        # Processed by filter
        if filters.get("processed_by"):
            query = query.filter(Payment.processed_by.ilike(f"%{filters['processed_by']}%"))

        return query.order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()

    def get_payment_totals(self, db: Session, learning_center_id: Optional[int] = None,
                           date_from: Optional[date] = None,
                           date_to: Optional[date] = None) -> Dict[str, Any]:
        """Get payment totals with optional filters"""
        query = db.query(
            func.count(Payment.id).label('total_payments'),
            func.sum(Payment.amount).label('total_amount'),
            func.sum(Payment.days_added).label('total_days'),
            func.avg(Payment.amount).label('avg_payment'),
            func.avg(Payment.days_added).label('avg_days')
        ).filter(Payment.status == "completed")

        if learning_center_id:
            query = query.filter(Payment.learning_center_id == learning_center_id)

        if date_from:
            query = query.filter(Payment.payment_date >= date_from)

        if date_to:
            query = query.filter(Payment.payment_date <= date_to)

        result = query.first()

        return {
            "total_payments": result.total_payments or 0,
            "total_amount": float(result.total_amount or 0),
            "total_days_sold": result.total_days or 0,
            "average_payment": float(result.avg_payment or 0),
            "average_days_per_payment": float(result.avg_days or 0)
        }

    def get_monthly_revenue(self, db: Session, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly revenue breakdown"""
        # Calculate start date
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)  # Approximate

        # Group by year-month
        monthly_data = db.query(
            func.to_char(Payment.payment_date, 'YYYY-MM').label('month'),
            func.sum(Payment.amount).label('revenue'),
            func.count(Payment.id).label('payment_count'),
            func.sum(Payment.days_added).label('days_sold'),
            func.count(func.distinct(Payment.learning_center_id)).label('paying_centers')
        ).filter(
            and_(
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
                Payment.status == "completed"
            )
        ).group_by(
            func.to_char(Payment.payment_date, 'YYYY-MM')
        ).order_by('month').all()

        return [
            {
                "month": row.month,
                "revenue": float(row.revenue or 0),
                "payment_count": row.payment_count or 0,
                "days_sold": row.days_sold or 0,
                "paying_centers": row.paying_centers or 0
            }
            for row in monthly_data
        ]

    def get_top_paying_centers(self, db: Session, limit: int = 10,
                               date_from: Optional[date] = None,
                               date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get top paying learning centers"""
        query = db.query(
            Payment.learning_center_id,
            LearningCenter.name.label('center_name'),
            func.sum(Payment.amount).label('total_paid'),
            func.count(Payment.id).label('payment_count'),
            func.sum(Payment.days_added).label('total_days'),
            func.max(Payment.payment_date).label('last_payment')
        ).join(LearningCenter).filter(Payment.status == "completed")

        if date_from:
            query = query.filter(Payment.payment_date >= date_from)
        if date_to:
            query = query.filter(Payment.payment_date <= date_to)

        results = query.group_by(
            Payment.learning_center_id, LearningCenter.name
        ).order_by(desc('total_paid')).limit(limit).all()

        return [
            {
                "learning_center_id": row.learning_center_id,
                "center_name": row.center_name,
                "total_paid": float(row.total_paid),
                "payment_count": row.payment_count,
                "total_days_purchased": row.total_days,
                "last_payment_date": row.last_payment
            }
            for row in results
        ]

    def get_payment_methods_breakdown(self, db: Session,
                                      date_from: Optional[date] = None,
                                      date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get breakdown by payment methods"""
        query = db.query(
            Payment.payment_method,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('total_amount'),
            func.avg(Payment.amount).label('avg_amount')
        ).filter(Payment.status == "completed")

        if date_from:
            query = query.filter(Payment.payment_date >= date_from)
        if date_to:
            query = query.filter(Payment.payment_date <= date_to)

        results = query.group_by(Payment.payment_method).order_by(desc('total_amount')).all()

        return [
            {
                "payment_method": row.payment_method,
                "transaction_count": row.count,
                "total_amount": float(row.total_amount),
                "average_amount": float(row.avg_amount)
            }
            for row in results
        ]

    def get_pending_payments(self, db: Session) -> List[Payment]:
        """Get all pending payments that need processing"""
        return db.query(Payment).filter(
            Payment.status == "pending"
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(Payment.payment_date).all()

    def get_refund_candidates(self, db: Session, days: int = 30) -> List[Payment]:
        """Get payments that might need refunds (recent large payments from inactive centers)"""
        cutoff_date = date.today() - timedelta(days=days)

        return db.query(Payment).join(LearningCenter).filter(
            and_(
                Payment.payment_date >= cutoff_date,
                Payment.amount >= 2000000,  # Large payments (2M+ UZS)
                Payment.status == "completed",
                LearningCenter.is_active == False
            )
        ).options(
            joinedload(Payment.learning_center)
        ).order_by(desc(Payment.amount)).all()

    def mark_as_processed(self, db: Session, payment_id: int,
                          processed_by: str = "system") -> Optional[Payment]:
        """Mark payment as processed"""
        payment = self.get(db, payment_id)
        if payment:
            payment.mark_as_processed(processed_by)
            db.commit()
            db.refresh(payment)
        return payment

    def bulk_update_status(self, db: Session, payment_ids: List[int],
                           new_status: str) -> int:
        """Update status for multiple payments"""
        updated_count = db.query(Payment).filter(
            Payment.id.in_(payment_ids)
        ).update({"status": new_status})

        db.commit()
        return updated_count

    def get_payment_analytics(self, db: Session, days: int = 90) -> Dict[str, Any]:
        """Get comprehensive payment analytics"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Basic totals
        totals = self.get_payment_totals(db, date_from=start_date, date_to=end_date)

        # Growth comparison (previous period)
        prev_start = start_date - timedelta(days=days)
        prev_totals = self.get_payment_totals(db, date_from=prev_start, date_to=start_date)

        # Calculate growth
        revenue_growth = 0
        if prev_totals["total_amount"] > 0:
            revenue_growth = ((totals["total_amount"] - prev_totals["total_amount"]) /
                              prev_totals["total_amount"]) * 100

        # Top centers and methods
        top_centers = self.get_top_paying_centers(db, limit=5, date_from=start_date)
        payment_methods = self.get_payment_methods_breakdown(db, date_from=start_date)

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "current_period": totals,
            "previous_period": prev_totals,
            "growth": {
                "revenue_growth_percentage": round(revenue_growth, 2),
                "payment_count_change": totals["total_payments"] - prev_totals["total_payments"]
            },
            "top_paying_centers": top_centers,
            "payment_methods_breakdown": payment_methods,
            "monthly_trend": self.get_monthly_revenue(db, months=6)
        }