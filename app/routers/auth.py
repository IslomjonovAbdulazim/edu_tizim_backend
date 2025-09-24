from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from ..database import get_db
from ..services import auth_service
from ..models import LearningCenter
from ..config import settings


router = APIRouter()


class SendCodeRequest(BaseModel):
    phone: str
    learning_center_id: int


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    learning_center_id: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SuperAdminLoginRequest(BaseModel):
    email: str
    password: str


class LearningCenterResponse(BaseModel):
    id: int
    name: str
    logo: str = None
    
    class Config:
        from_attributes = True


@router.post("/send-code")
async def send_verification_code(request: SendCodeRequest, db: Session = Depends(get_db)):
    """Send verification code to phone number"""
    success = await auth_service.send_verification_code(
        request.phone, 
        request.learning_center_id,
        db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )
    
    return {"message": "Verification code sent successfully"}


@router.post("/verify-login", response_model=TokenResponse)
async def verify_and_login(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """Verify code and login user"""
    user, access_token, refresh_token = auth_service.verify_code_and_login(
        request.phone,
        request.code,
        request.learning_center_id,
        db
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "phone": user.phone,
            "name": user.name,
            "role": user.role,
            "learning_center_id": user.learning_center_id,
            "coins": user.coins
        }
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    access_token = auth_service.refresh_access_token(request.refresh_token, db)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/learning-centers", response_model=List[LearningCenterResponse])
async def get_learning_centers(db: Session = Depends(get_db)):
    """Get all active learning centers for dropdown selection"""
    # CACHING DISABLED - Always fetch from database
    centers = db.query(LearningCenter).filter(
        LearningCenter.is_active == True,
        LearningCenter.deleted_at.is_(None)
    ).all()
    
    # Convert to dict
    centers_dict = [
        {
            "id": c.id,
            "name": c.name,
            "logo": c.logo
        }
        for c in centers
    ]
    
    return centers_dict


@router.post("/super-admin/login", response_model=dict)
async def super_admin_login(request: SuperAdminLoginRequest):
    """Super admin login with email and password"""
    if (request.email != settings.SUPER_ADMIN_EMAIL or 
        request.password != settings.SUPER_ADMIN_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid super admin credentials"
        )
    
    # Generate token for super admin (user_id = 0 for super admin)
    access_token = auth_service._create_access_token(0)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": 0,
            "email": request.email,
            "role": "super_admin"
        }
    }