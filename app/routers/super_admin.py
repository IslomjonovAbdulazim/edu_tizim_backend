from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import *
from ..services import PaymentService
from ..utils import hash_password, APIResponse, paginate, get_current_user_data
from ..dependencies import get_current_user
from .. import schemas

router = APIRouter()


def get_super_admin_user(current_user: dict = Depends(get_current_user)):
    """Require super admin role"""
    if current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


@router.get("/dashboard")
def super_admin_dashboard(
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Super admin dashboard with system overview"""
    # System statistics
    total_centers = db.query(LearningCenter).count()
    active_centers = db.query(LearningCenter).filter(LearningCenter.is_active == True).count()

    total_students = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    ).count()

    total_teachers = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.role_in_center == UserRole.TEACHER,
        LearningCenterProfile.is_active == True
    ).count()

    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0

    # Recent centers
    recent_centers = db.query(LearningCenter).order_by(
        desc(LearningCenter.created_at)
    ).limit(5).all()

    # Centers expiring soon (within 7 days)
    expiring_centers = db.query(LearningCenter).filter(
        LearningCenter.is_active == True,
        LearningCenter.days_remaining <= 7,
        LearningCenter.days_remaining > 0
    ).all()

    return APIResponse.success({
        "stats": {
            "total_centers": total_centers,
            "active_centers": active_centers,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_revenue": float(total_revenue)
        },
        "recent_centers": [{
            "id": c.id,
            "title": c.title,
            "days_remaining": c.days_remaining,
            "is_active": c.is_active,
            "created_at": c.created_at
        } for c in recent_centers],
        "expiring_centers": [{
            "id": c.id,
            "title": c.title,
            "days_remaining": c.days_remaining,
            "owner_id": c.owner_id
        } for c in expiring_centers]
    })


# Learning Centers Management
@router.post("/centers")
def create_learning_center(
        center_data: schemas.LearningCenterCreate,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Create new learning center and admin user"""
    # Check if admin email already exists
    existing_admin = db.query(User).filter(User.email == center_data.owner_email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already exists"
        )

    try:
        # Create admin user first
        admin_user = User(
            email=center_data.owner_email,
            password_hash=hash_password(center_data.owner_password),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Create learning center
        center = LearningCenter(
            title=center_data.title,
            logo=center_data.logo,
            student_limit=center_data.student_limit,
            owner_id=admin_user.id,
            days_remaining=30,  # Give 30 days trial
            is_active=True
        )
        db.add(center)
        db.commit()
        db.refresh(center)

        # Create admin profile in the center
        admin_profile = LearningCenterProfile(
            user_id=admin_user.id,
            center_id=center.id,
            full_name="Admin User",  # Default name
            role_in_center=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_profile)
        db.commit()

        return APIResponse.success({
            "center_id": center.id,
            "admin_user_id": admin_user.id,
            "message": "Learning center and admin created successfully"
        })

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create center: {str(e)}"
        )


@router.get("/centers")
def get_all_centers(
        page: int = 1,
        size: int = 20,
        search: str = None,
        status_filter: str = None,  # "active", "inactive", "expiring"
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Get all learning centers with pagination and filtering"""
    query = db.query(LearningCenter)

    if search:
        query = query.filter(LearningCenter.title.ilike(f"%{search}%"))

    if status_filter == "active":
        query = query.filter(
            LearningCenter.is_active == True,
            LearningCenter.days_remaining > 0
        )
    elif status_filter == "inactive":
        query = query.filter(LearningCenter.is_active == False)
    elif status_filter == "expiring":
        query = query.filter(
            LearningCenter.is_active == True,
            LearningCenter.days_remaining <= 7,
            LearningCenter.days_remaining > 0
        )

    query = query.order_by(desc(LearningCenter.created_at))
    result = paginate(query, page, size)

    # Add additional stats for each center
    centers_with_stats = []
    for center in result["items"]:
        student_count = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.center_id == center.id,
            LearningCenterProfile.role_in_center == UserRole.STUDENT,
            LearningCenterProfile.is_active == True
        ).count()

        centers_with_stats.append({
            "id": center.id,
            "title": center.title,
            "logo": center.logo,
            "days_remaining": center.days_remaining,
            "student_limit": center.student_limit,
            "student_count": student_count,
            "is_active": center.is_active,
            "owner_id": center.owner_id,
            "created_at": center.created_at
        })

    return APIResponse.paginated(centers_with_stats, result["total"], result["page"], result["size"])


@router.get("/centers/{center_id}")
def get_center_details(
        center_id: int,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Get detailed center information"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    # Get detailed stats
    total_students = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    ).count()

    total_teachers = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER,
        LearningCenterProfile.is_active == True
    ).count()

    total_courses = db.query(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True
    ).count()

    total_lessons = db.query(Lesson).join(Module).join(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True,
        Module.is_active == True,
        Lesson.is_active == True
    ).count()

    # Payment history
    payment_history = db.query(Payment).filter(
        Payment.center_id == center_id
    ).order_by(desc(Payment.created_at)).limit(10).all()

    return APIResponse.success({
        "center": {
            "id": center.id,
            "title": center.title,
            "logo": center.logo,
            "days_remaining": center.days_remaining,
            "student_limit": center.student_limit,
            "is_active": center.is_active,
            "owner_id": center.owner_id,
            "created_at": center.created_at
        },
        "stats": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_courses": total_courses,
            "total_lessons": total_lessons
        },
        "recent_payments": [{
            "id": p.id,
            "amount": p.amount,
            "days_added": p.days_added,
            "description": p.description,
            "created_at": p.created_at
        } for p in payment_history]
    })


# Payment Management
@router.post("/payments")
def add_payment(
        payment_data: schemas.PaymentCreate,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Add payment and extend center subscription"""
    # Verify center exists
    center = db.query(LearningCenter).filter(
        LearningCenter.id == payment_data.center_id
    ).first()

    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    payment = PaymentService.add_payment(
        db,
        payment_data,
        current_user["user"].id
    )

    return APIResponse.success({
        "payment_id": payment.id,
        "message": f"Payment processed successfully. Added {payment.days_added} days.",
        "new_days_remaining": center.days_remaining + payment.days_added
    })


@router.get("/payments")
def get_all_payments(
        center_id: int = None,
        page: int = 1,
        size: int = 20,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Get payment history with filtering"""
    query = db.query(Payment)

    if center_id:
        query = query.filter(Payment.center_id == center_id)

    query = query.order_by(Payment.created_at.desc())
    result = paginate(query, page, size)

    # Add center info to payments
    payments_with_center = []
    for payment in result["items"]:
        center = db.query(LearningCenter).filter(
            LearningCenter.id == payment.center_id
        ).first()

        payments_with_center.append({
            "id": payment.id,
            "center_id": payment.center_id,
            "center_title": center.title if center else "Unknown",
            "amount": payment.amount,
            "days_added": payment.days_added,
            "description": payment.description,
            "created_at": payment.created_at
        })

    return APIResponse.paginated(payments_with_center, result["total"], result["page"], result["size"])


# Center Status Management
@router.patch("/centers/{center_id}/status")
def toggle_center_status(
        center_id: int,
        status_data: dict,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Activate/deactivate learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    center.is_active = status_data.get("is_active", center.is_active)

    # If reactivating, ensure they have remaining days
    if center.is_active and center.days_remaining <= 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot activate center with 0 days remaining. Add payment first."
        )

    db.commit()

    return APIResponse.success({
        "message": f"Center {'activated' if center.is_active else 'deactivated'} successfully",
        "center_id": center.id,
        "is_active": center.is_active
    })


@router.patch("/centers/{center_id}/extend")
def extend_center_trial(
        center_id: int,
        extend_data: dict,  # {"days": 30, "reason": "Trial extension"}
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Extend center subscription without payment (admin override)"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    days_to_add = extend_data.get("days", 0)
    reason = extend_data.get("reason", "Admin extension")

    if days_to_add <= 0:
        raise HTTPException(status_code=400, detail="Days must be greater than 0")

    # Add free extension
    center.days_remaining = max(0, center.days_remaining) + days_to_add
    center.is_active = True

    # Record as $0 payment for tracking
    payment = Payment(
        center_id=center_id,
        amount=0.0,
        days_added=days_to_add,
        description=f"Admin Extension: {reason}",
        created_by=current_user["user"].id
    )
    db.add(payment)

    db.commit()

    return APIResponse.success({
        "message": f"Extended center by {days_to_add} days",
        "new_days_remaining": center.days_remaining
    })


@router.delete("/centers/{center_id}")
def delete_center(
        center_id: int,
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    # Soft delete by deactivating
    center.is_active = False
    db.commit()

    return APIResponse.success({"message": "Center deleted successfully"})


# System Analytics
@router.get("/analytics/revenue")
def get_revenue_analytics(
        period: str = "monthly",  # "weekly", "monthly", "yearly"
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Get revenue analytics by period"""
    from datetime import datetime, timedelta

    if period == "weekly":
        start_date = datetime.now() - timedelta(weeks=12)
        date_format = "%Y-W%U"
    elif period == "yearly":
        start_date = datetime.now() - timedelta(days=365 * 3)
        date_format = "%Y"
    else:  # monthly
        start_date = datetime.now() - timedelta(days=365)
        date_format = "%Y-%m"

    payments = db.query(Payment).filter(
        Payment.created_at >= start_date
    ).all()

    revenue_by_period = {}
    for payment in payments:
        period_key = payment.created_at.strftime(date_format)
        if period_key not in revenue_by_period:
            revenue_by_period[period_key] = 0
        revenue_by_period[period_key] += payment.amount

    return APIResponse.success({
        "period": period,
        "revenue_data": [
            {"period": period, "revenue": revenue}
            for period, revenue in sorted(revenue_by_period.items())
        ],
        "total_revenue": sum(revenue_by_period.values())
    })


@router.get("/analytics/centers")
def get_center_analytics(
        current_user: dict = Depends(get_super_admin_user),
        db: Session = Depends(get_db)
):
    """Get center growth and usage analytics"""
    from datetime import datetime, timedelta

    # Center growth over time
    centers_by_month = db.query(
        func.date_trunc('month', LearningCenter.created_at).label('month'),
        func.count(LearningCenter.id).label('count')
    ).group_by('month').order_by('month').all()

    # Active vs inactive centers
    active_count = db.query(LearningCenter).filter(
        LearningCenter.is_active == True
    ).count()

    inactive_count = db.query(LearningCenter).filter(
        LearningCenter.is_active == False
    ).count()

    # Student distribution
    student_distribution = db.query(
        LearningCenter.title,
        func.count(LearningCenterProfile.id).label('student_count')
    ).join(
        LearningCenterProfile, LearningCenter.id == LearningCenterProfile.center_id
    ).filter(
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    ).group_by(LearningCenter.id, LearningCenter.title).all()

    return APIResponse.success({
        "center_growth": [
            {"month": str(row.month), "count": row.count}
            for row in centers_by_month
        ],
        "status_distribution": {
            "active": active_count,
            "inactive": inactive_count
        },
        "student_distribution": [
            {"center": row.title, "students": row.student_count}
            for row in student_distribution
        ]
    })