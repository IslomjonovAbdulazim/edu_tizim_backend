from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import *
from ..services import AuthService
from ..utils import create_access_token, verify_password, send_telegram_message, generate_verification_code

router = APIRouter()

# Store verification codes temporarily (use Redis in production)
verification_codes = {}


@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login for admin/teacher with email/password"""
    if not user_data.email or not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password required"
        )

    user = AuthService.get_user_by_email(db, user_data.email)
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )

    # Get user's learning center (for admin/teacher)
    center_id = None
    if user.role in [UserRole.ADMIN, UserRole.TEACHER]:
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.user_id == user.id,
            LearningCenterProfile.is_active == True
        ).first()
        if profile:
            center_id = profile.center_id

    access_token = create_access_token(
        data={"user_id": user.id, "center_id": center_id}
    )

    return schemas.Token(
        access_token=access_token,
        refresh_token=access_token,  # Same for MVP
        token_type="bearer"
    )


@router.post("/student/request-code")
def request_verification_code(phone_data: dict, db: Session = Depends(get_db)):
    """Request verification code for student login"""
    phone = phone_data.get("phone")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number required"
        )

    user = AuthService.get_user_by_phone(db, phone)
    if not user or user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    if not user.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID not registered"
        )

    # Generate verification code
    code = generate_verification_code()
    verification_codes[phone] = code

    # Send via Telegram
    message = f"Your verification code is: {code}"
    if send_telegram_message(user.telegram_id, message):
        return {"message": "Verification code sent"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )


@router.post("/student/verify", response_model=schemas.Token)
def verify_student_code(
        verification_data: dict,
        db: Session = Depends(get_db)
):
    """Verify code and login student"""
    phone = verification_data.get("phone")
    code = verification_data.get("code")

    if not phone or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone and code required"
        )

    # Check verification code
    if verification_codes.get(phone) != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )

    # Remove used code
    del verification_codes[phone]

    user = AuthService.get_user_by_phone(db, phone)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get student's learning center
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.is_active == True
    ).first()

    center_id = profile.center_id if profile else None

    access_token = create_access_token(
        data={"user_id": user.id, "center_id": center_id}
    )

    return schemas.Token(
        access_token=access_token,
        refresh_token=access_token,
        token_type="bearer"
    )


@router.post("/student/telegram-login", response_model=schemas.Token)
def telegram_login(
        telegram_data: schemas.PhoneVerification,
        db: Session = Depends(get_db)
):
    """Direct login with phone and telegram_id"""
    user = AuthService.verify_phone_telegram(
        db, telegram_data.phone, telegram_data.telegram_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or telegram ID"
        )

    # Get student's learning center
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.is_active == True
    ).first()

    center_id = profile.center_id if profile else None

    access_token = create_access_token(
        data={"user_id": user.id, "center_id": center_id}
    )

    return schemas.Token(
        access_token=access_token,
        refresh_token=access_token,
        token_type="bearer"
    )