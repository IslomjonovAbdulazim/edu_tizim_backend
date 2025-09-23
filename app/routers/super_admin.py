from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_db
from ..dependencies import get_super_admin_user
from ..models import LearningCenter
from ..services import storage_service, cache_service


router = APIRouter()


class CreateLearningCenterRequest(BaseModel):
    name: str
    phone: str
    student_limit: int
    teacher_limit: int
    group_limit: int
    is_paid: bool = True


class UpdateLearningCenterRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    student_limit: Optional[int] = None
    teacher_limit: Optional[int] = None
    group_limit: Optional[int] = None
    is_paid: Optional[bool] = None


class LearningCenterResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str]
    phone: str
    student_limit: int
    teacher_limit: int
    group_limit: int
    is_active: bool
    is_paid: bool
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/learning-centers", response_model=LearningCenterResponse)
async def create_learning_center(
    request: CreateLearningCenterRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new learning center"""
    center = LearningCenter(
        name=request.name,
        phone=request.phone,
        student_limit=request.student_limit,
        teacher_limit=request.teacher_limit,
        group_limit=request.group_limit,
        is_paid=request.is_paid
    )
    
    db.add(center)
    db.commit()
    db.refresh(center)
    
    # Invalidate learning centers cache
    await cache_service.invalidate_learning_centers()
    
    return center


@router.get("/learning-centers", response_model=List[LearningCenterResponse])
async def list_learning_centers(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all learning centers"""
    centers = db.query(LearningCenter).filter(
        LearningCenter.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()
    
    return centers


@router.post("/learning-centers/{center_id}/logo")
async def upload_center_logo(
    center_id: int,
    file: UploadFile = File(...),
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Upload logo for learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning center not found"
        )
    
    # Save logo file
    logo_path = await storage_service.save_logo(file, center_id)
    
    # Update center with logo path
    center.logo = logo_path
    db.commit()
    
    return {"message": "Logo uploaded successfully", "path": logo_path}


@router.put("/learning-centers/{center_id}", response_model=LearningCenterResponse)
async def update_learning_center(
    center_id: int,
    request: UpdateLearningCenterRequest,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update learning center details"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning center not found"
        )
    
    # Update fields if provided
    for field, value in request.dict(exclude_unset=True).items():
        setattr(center, field, value)
    
    db.commit()
    db.refresh(center)
    
    # Invalidate caches
    await cache_service.invalidate_learning_centers()
    
    return center


@router.post("/learning-centers/{center_id}/toggle-payment")
async def toggle_payment_status(
    center_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle payment status for learning center"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning center not found"
        )
    
    center.is_paid = not center.is_paid
    db.commit()
    
    # Invalidate caches
    await cache_service.invalidate_learning_centers()
    
    return {
        "message": f"Payment status {'enabled' if center.is_paid else 'disabled'}",
        "is_paid": center.is_paid
    }


@router.delete("/learning-centers/{center_id}")
async def deactivate_learning_center(
    center_id: int,
    current_user = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate learning center (soft delete)"""
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning center not found"
        )
    
    center.is_active = False
    db.commit()
    
    return {"message": "Learning center deactivated successfully"}