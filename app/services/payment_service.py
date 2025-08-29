from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.models.payment import Payment
from app.models.learning_center import LearningCenter
from app.schemas.payment import PaymentCreate, QuickPaymentRequest
from app.core.exceptions import ResourceNotFoundException, InvalidDataException


class PaymentService:
    """Service for handling payments and learning center account management"""

    # Standard payment packages (UZS - Uzbek Som)
    PAYMENT_PACKAGES = {
        "1month": {"days": 30, "amount": 1200000.00},  # ~$100 USD equivalent
        "3months": {"days": 90, "amount": 3000000.00},  # ~$250 USD equivalent (17% discount)
        "6months": {"days": 180, "amount": 5400000.00},  # ~$450 USD equivalent (25% discount)
        "1year": {"days": 365, "amount": 9600000.00},  # ~$800 USD equivalent (35% discount)
    }

    @staticmethod
    def create_payment(db: Session, payment_data: PaymentCreate) -> Dict[str, Any]:
        """Create a new payment and add days to learning center account"""

        # Get learning center
        center = db.query(LearningCenter).filter(
            LearningCenter.id == payment_data.learning_center_id
        ).first()

        if not center:
            raise ResourceNotFoundException("Learning Center", "Learning center not found")

        try:
            # Process payment through learning center
            payment = center.add_payment(
                amount=float(payment_data.amount),
                days_added=payment_data.days_added,
                payment_method=payment_data.payment_method,
                reference_number=payment_data.reference_number,
                notes=payment_data.notes,
                processed_by=payment_data.processed_by
            )

            # Add payment to session
            db.add(payment)
            db.commit()
            db.refresh(payment)
            db.refresh(center)

            return {
                "success": True,
                "message": f"Payment processed successfully. {payment_data.days_added} days added.",
                "payment": payment,
                "center_status": {
                    "remaining_days": center.remaining_days,
                    "expires_at": center.expires_at,
                    "is_active": center.is_active,
                    "account_status": center.account_status
                }
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Payment processing failed: {str(e)}")

    @staticmethod
    def create_quick_payment(db: Session, request: QuickPaymentRequest, processed_by: str) -> Dict[str, Any]:
        """Create payment using predefined packages"""

        if request.payment_package == "custom":
            if not request.custom_amount or not request.custom_days:
                raise InvalidDataException("Custom amount and days are required for custom package")

            amount = request.custom_amount
            days = request.custom_days
        else:
            package = PaymentService.PAYMENT_PACKAGES.get(request.payment_package)
            if not package:
                raise InvalidDataException(f"Unknown payment package: {request.payment_package}")

            amount = Decimal(str(package["amount"]))
            days = package["days"]

        # Create payment data
        payment_data = PaymentCreate(
            learning_center_id=request.learning_center_id,
            amount=amount,
            days_added=days,
            payment_method=request.payment_method,
            reference_number=request.reference_number,
            processed_by=processed_by
        )

        return PaymentService.create_payment(db, payment_data)

    @staticmethod
    def extend_trial(db: Session, learning_center_id: int, trial_days: int = 7,
                     processed_by: str = "admin") -> Dict[str, Any]:
        """Extend free trial for learning center"""

        center = db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()
        if not center:
            raise ResourceNotFoundException("Learning Center", "Learning center not found")

        try:
            # Extend trial through learning center
            payment = center.extend_trial(trial_days, processed_by)

            db.add(payment)
            db.commit()
            db.refresh(center)

            return {
                "success": True,
                "message": f"Trial extended by {trial_days} days",
                "center_status": {
                    "remaining_days": center.remaining_days,
                    "expires_at": center.expires_at,
                    "is_active": center.is_active,
                    "account_status": center.account_status
                }
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Trial extension failed: {str(e)}")

    @staticmethod
    def get_account_status(db: Session, learning_center_id: int) -> Dict[str, Any]:
        """Get comprehensive account status for learning center"""

        center = db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()
        if not center:
            raise ResourceNotFoundException("Learning Center", "Learning center not found")

        recent_payments = center.get_payment_history(limit=5)

        return {
            "learning_center_id": center.id,
            "learning_center_name": center.name,
            "is_active": center.is_active,
            "remaining_days": center.remaining_days,
            "account_status": center.account_status,
            "expires_at": center.expires_at,
            "days_until_expiration": center.days_until_expiration,
            "needs_payment_soon": center.needs_payment_soon,
            "is_expired": center.is_expired,
            "last_payment_date": center.last_payment_date,
            "total_paid": center.total_paid,
            "total_payments": center.total_payments,
            "monthly_cost": center.calculate_monthly_cost(),
            "recent_payments": recent_payments
        }

    @staticmethod
    def check_all_account_statuses(db: Session) -> Dict[str, Any]:
        """Check and update all learning center account statuses (run daily)"""

        centers = db.query(LearningCenter).all()
        updated_centers = []
        expired_today = []
        expiring_soon = []

        for center in centers:
            old_status = center.is_active

            # Deduct one day and update status
            remaining_days = center.deduct_day()

            if old_status and not center.is_active:
                expired_today.append({
                    "id": center.id,
                    "name": center.name,
                    "expired_date": date.today()
                })

            if center.needs_payment_soon and center.is_active:
                expiring_soon.append({
                    "id": center.id,
                    "name": center.name,
                    "days_left": remaining_days
                })

            updated_centers.append({
                "id": center.id,
                "name": center.name,
                "remaining_days": remaining_days,
                "is_active": center.is_active,
                "account_status": center.account_status
            })

        db.commit()

        return {
            "date_processed": date.today(),
            "total_centers": len(centers),
            "centers_updated": len(updated_centers),
            "expired_today": expired_today,
            "expiring_soon": expiring_soon,
            "active_centers": len([c for c in updated_centers if c["is_active"]]),
            "expired_centers": len([c for c in updated_centers if not c["is_active"]])
        }

    @staticmethod
    def get_payment_statistics(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get payment statistics for dashboard"""

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get payments in period
        payments = db.query(Payment).filter(
            Payment.payment_date >= start_date,
            Payment.status == "completed"
        ).all()

        if not payments:
            return {
                "period_days": days,
                "total_payments": 0,
                "total_revenue": 0,
                "total_days_sold": 0,
                "average_payment": 0,
                "average_days_per_payment": 0
            }

        total_revenue = sum(float(p.amount) for p in payments)
        total_days_sold = sum(p.days_added for p in payments)

        # Top paying centers
        center_payments = {}
        for payment in payments:
            center_id = payment.learning_center_id
            if center_id not in center_payments:
                center_payments[center_id] = {
                    "center_name": payment.learning_center.name,
                    "total_paid": 0,
                    "payment_count": 0
                }
            center_payments[center_id]["total_paid"] += float(payment.amount)
            center_payments[center_id]["payment_count"] += 1

        top_centers = sorted(
            center_payments.items(),
            key=lambda x: x[1]["total_paid"],
            reverse=True
        )[:10]

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": end_date,
            "total_payments": len(payments),
            "total_revenue": round(total_revenue, 2),
            "total_days_sold": total_days_sold,
            "average_payment": round(total_revenue / len(payments), 2),
            "average_days_per_payment": round(total_days_sold / len(payments), 1),
            "top_paying_centers": [
                {
                    "center_id": center_id,
                    "center_name": data["center_name"],
                    "total_paid": round(data["total_paid"], 2),
                    "payment_count": data["payment_count"]
                }
                for center_id, data in top_centers
            ]
        }

    @staticmethod
    def get_centers_needing_attention(db: Session) -> Dict[str, Any]:
        """Get learning centers that need payment attention"""

        all_centers = db.query(LearningCenter).all()

        expired = [c for c in all_centers if c.is_expired]
        expiring_soon = [c for c in all_centers if c.needs_payment_soon and not c.is_expired]

        return {
            "expired_centers": [
                {
                    "id": c.id,
                    "name": c.name,
                    "days_overdue": abs(c.remaining_days),
                    "last_payment_date": c.last_payment_date,
                    "total_paid": float(c.total_paid or 0)
                }
                for c in expired
            ],
            "expiring_soon": [
                {
                    "id": c.id,
                    "name": c.name,
                    "days_left": c.remaining_days,
                    "expires_at": c.expires_at,
                    "last_payment_date": c.last_payment_date
                }
                for c in expiring_soon
            ],
            "counts": {
                "expired": len(expired),
                "expiring_soon": len(expiring_soon),
                "active": len([c for c in all_centers if c.account_status == "active"]),
                "total": len(all_centers)
            }
        }

    @staticmethod
    def cancel_payment(db: Session, payment_id: int, reason: str = None) -> Dict[str, Any]:
        """Cancel a payment and adjust account accordingly"""

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ResourceNotFoundException("Payment", "Payment not found")

        if payment.status != "completed":
            raise InvalidDataException("Can only cancel completed payments")

        try:
            # Adjust learning center account
            center = payment.learning_center
            center.remaining_days = max(0, center.remaining_days - payment.days_added)
            center.total_paid = (center.total_paid or 0) - payment.amount
            center.check_and_update_status()

            # Update payment status
            payment.cancel_payment(reason)

            db.commit()

            return {
                "success": True,
                "message": f"Payment cancelled. {payment.days_added} days removed from account.",
                "center_status": PaymentService.get_account_status(db, center.id)
            }

        except Exception as e:
            db.rollback()
            raise InvalidDataException(f"Payment cancellation failed: {str(e)}")