from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db, RedisService
from ..dependencies import get_current_user
from ..models import *
from ..services import AuthService
from ..utils import APIResponse, format_phone, \
    validate_phone, generate_verification_code, create_access_token, send_telegram_message, verify_password
from .. import schemas

router = APIRouter()


@router.post("/login")
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login for admin/teacher/super-admin with email/password"""
    if not user_data.email or not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password required"
        )

    user = AuthService.get_user_by_email(db, user_data.email)
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students must use phone login"
        )

    # Get user's center (for admin/teacher)
    center_id = None
    if user.role in [UserRole.ADMIN, UserRole.TEACHER]:
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.user_id == user.id,
            LearningCenterProfile.is_active == True
        ).first()
        if profile:
            center_id = profile.center_id

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "center_id": center_id,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 2592000,
        "center_id": center_id,
        "role": user.role.value
    }


@router.post("/student/request-code")
def request_verification_code(
        phone_data: schemas.VerificationRequest,
        db: Session = Depends(get_db)
):
    """Request SMS/Telegram verification code for student"""
    phone = format_phone(phone_data.phone)

    if not validate_phone(phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )

    user = AuthService.get_user_by_phone(db, phone)
    if not user or user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found with this phone number"
        )

    # Generate and store verification code in Redis
    code = generate_verification_code()

    # Store with 5 minutes expiration
    if not RedisService.store_verification_code(phone, code, 300):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code. Please try again."
        )

    # Send via Telegram if available
    success = False
    if user.telegram_id:
        message = f"🔐 Your verification code: {code}\n\nValid for 5 minutes."
        success = send_telegram_message(user.telegram_id, message)

    if not success:
        # Clean up Redis if sending failed
        RedisService.delete_verification_code(phone)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please check your Telegram ID."
        )

    return APIResponse.success({
        "message": "Verification code sent to your Telegram",
        "phone": phone,
        "expires_in": 300
    })


@router.post("/student/verify")
def verify_student_code(
        verification_data: schemas.VerificationCode,
        db: Session = Depends(get_db)
):
    """Verify code and login student"""
    phone = format_phone(verification_data.phone)
    code = verification_data.code.strip()

    if not phone or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone and code are required"
        )

    # Check verification code from Redis
    stored_code = RedisService.get_verification_code(phone)
    if not stored_code or stored_code != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code"
        )

    # Remove used code
    RedisService.delete_verification_code(phone)

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
        data={
            "user_id": user.id,
            "center_id": center_id,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 2592000,
        "center_id": center_id,
        "role": user.role.value
    }


@router.post("/student/telegram-login")
def telegram_direct_login(
        telegram_data: schemas.PhoneLogin,
        db: Session = Depends(get_db)
):
    """Direct login with phone and telegram_id (for Telegram bot integration)"""
    phone = format_phone(telegram_data.phone)

    if not validate_phone(phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )

    if not telegram_data.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required"
        )

    user = AuthService.verify_phone_telegram(db, phone, telegram_data.telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or Telegram ID"
        )

    # Get student's learning center
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.is_active == True
    ).first()

    center_id = profile.center_id if profile else None

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "center_id": center_id,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 2592000,
        "center_id": center_id,
        "role": user.role.value
    }


@router.post("/refresh")
def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token (simple implementation)"""
    access_token = create_access_token(
        data={
            "user_id": current_user["user"].id,
            "center_id": current_user["center_id"],
            "role": current_user["role"]
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 2592000,
        "center_id": current_user["center_id"],
        "role": current_user["role"]
    }


@router.post("/logout")
def logout():
    """Logout endpoint (client-side token removal)"""
    return APIResponse.success({"message": "Logged out successfully"})


@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return APIResponse.success({
        "user": {
            "id": current_user["user"].id,
            "email": current_user["user"].email,
            "phone": current_user["user"].phone,
            "role": current_user["role"],
            "avatar": current_user["user"].avatar
        },
        "profile": {
            "id": current_user["profile"].id,
            "full_name": current_user["profile"].full_name,
            "center_id": current_user["center_id"]
        } if current_user["profile"] else None,
        "center": {
            "id": current_user["center"].id,
            "title": current_user["center"].title,
            "days_remaining": current_user["center"].days_remaining
        } if current_user["center"] else None
    })