from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import *
from ..services import PaymentService
from ..utils import hash_password, APIResponse, paginate
from .. import schemas
from typing import List

router = APIRouter()


# Learning Centers Management
@router.post("/centers", response_model=schemas.LearningCenter)
def create_learning_center(
        center_data: schemas.LearningCenterCreate,
        db: Session = Depends(get_db)
):
    """Create new learning center and admin user"""
    # Check if owner exists
    owner = db.query(User).filter(User.id == center_data.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner user not found"
        )

    center = LearningCenter(**center_data.dict())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.get("/centers")
def get_all_centers(
        page: int = 1,
        size: int = 20,
        db: Session = Depends(get_db)
):
    """Get all learning centers with pagination"""
    query = db.query(LearningCenter)
    result = paginate(query, page, size)
    return APIResponse.success(result)


@router.get("/centers/{center_id}")
def get_center_details(center_id: int, db: Session = Depends(get_db)):
    """Get detailed center information"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    # Get stats
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

    return APIResponse.success({
        "center": center,
        "stats": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_courses": total_courses,
            "student_limit": center.student_limit,
            "days_remaining": center.days_remaining
        }
    })


# Admin User Management
@router.post("/admins")
def create_admin_user(
        admin_data: dict,
        db: Session = Depends(get_db)
):
    """Create new learning center admin"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == admin_data["email"]).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create admin user
    admin_user = User(
        email=admin_data["email"],
        password_hash=hash_password(admin_data["password"]),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    return APIResponse.success({"user_id": admin_user.id, "email": admin_user.email})


# Payment Management
@router.post("/payments")
def add_payment(
        payment_data: schemas.PaymentCreate,
        db: Session = Depends(get_db)
):
    """Add payment and extend center subscription"""
    payment = PaymentService.add_payment(db, payment_data, 1)  # Super admin ID = 1
    return APIResponse.success({"payment_id": payment.id})


@router.get("/payments")
def get_all_payments(
        center_id: int = None,
        page: int = 1,
        size: int = 20,
        db: Session = Depends(get_db)
):
    """Get payment history"""
    query = db.query(Payment)
    if center_id:
        query = query.filter(Payment.center_id == center_id)

    query = query.order_by(Payment.created_at.desc())
    result = paginate(query, page, size)
    return APIResponse.success(result)


# System Stats
@router.get("/stats")
def get_system_stats(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    total_centers = db.query(LearningCenter).count()
    active_centers = db.query(LearningCenter).filter(LearningCenter.is_active == True).count()
    total_students = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.role_in_center == UserRole.STUDENT
    ).count()

    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0

    return APIResponse.success({
        "total_centers": total_centers,
        "active_centers": active_centers,
        "total_students": total_students,
        "total_revenue": float(total_revenue)
    })


# Center Status Management
@router.patch("/centers/{center_id}/status")
def toggle_center_status(
        center_id: int,
        status_data: dict,
        db: Session = Depends(get_db)
):
    """Activate/deactivate learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    center.is_active = status_data.get("is_active", center.is_active)
    db.commit()

    return APIResponse.success({"message": f"Center {'activated' if center.is_active else 'deactivated'}"})


@router.delete("/centers/{center_id}")
def delete_center(center_id: int, db: Session = Depends(get_db)):
    """Soft delete learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    center.is_active = False
    db.commit()

    return APIResponse.success({"message": "Center deleted successfully"})