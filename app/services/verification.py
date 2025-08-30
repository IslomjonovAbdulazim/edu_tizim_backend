from typing import Dict, Any
from sqlalchemy.orm import Session
import random
import string
import requests
import os
from datetime import datetime, timedelta
from app.schemas import (
    SendVerificationRequest, SendVerificationResponse,
    VerifyCodeRequest, VerifyCodeResponse,
    VerificationCodeResponse, ResendCodeRequest, VerificationStatusRequest, VerificationStatusResponse
)
from app.services.base import BaseService
from app.core.config import settings


class VerificationService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def send_verification_code(self, request: SendVerificationRequest) -> Dict[str, Any]:
        """Send verification code to user via Telegram"""
        try:
            # FIXED: Check if phone number exists in the specified learning center
            user = self.repos.user.get_by_phone_and_center(
                request.phone_number,
                request.learning_center_id
            )

            if not user:
                return self._format_error_response(
                    "Phone number not found in this learning center. Please contact your administrator."
                )

            # Check if learning center is active
            learning_center = self.repos.learning_center.get(request.learning_center_id)
            if not learning_center or not learning_center.is_active:
                return self._format_error_response(
                    "Learning center subscription expired. Please contact your administrator."
                )

            # FIXED: Check if user already has telegram_id linked
            if user.telegram_id and user.telegram_id != request.telegram_id:
                return self._format_error_response(
                    "This phone number is already linked to another Telegram account."
                )

            # Check if phone is temporarily blocked
            if self.repos.verification.is_phone_blocked(request.phone_number):
                return self._format_error_response(
                    "Phone number temporarily blocked due to too many failed attempts. Please try again later."
                )

            # Check rate limiting
            can_send, next_allowed = self.repos.verification.can_send_new_code(
                request.telegram_id,
                request.phone_number,
                cooldown_minutes=1
            )

            if not can_send:
                minutes_remaining = int((next_allowed - datetime.utcnow()).total_seconds() / 60) + 1
                return self._format_error_response(
                    f"Please wait {minutes_remaining} minute(s) before requesting a new code"
                )

            # FIXED: Generate code using configurable length
            code_length = getattr(settings, 'VERIFICATION_CODE_LENGTH', 6)
            code = self._generate_verification_code(code_length)

            # Create verification code record
            verification_code = self.repos.verification.create_verification_code(
                telegram_id=request.telegram_id,
                phone_number=request.phone_number,
                code=code,
                expires_in_minutes=10
            )

            # Send code via Telegram Bot API
            success = self._send_telegram_message(request.telegram_id, code)

            if success:
                response = SendVerificationResponse(
                    success=True,
                    message="Verification code sent successfully",
                    expires_at=verification_code.expires_at,
                    attempts_remaining=verification_code.max_attempts,
                    code_length=len(code),
                    expires_in_minutes=10
                )
                return self._format_success_response(response.dict())
            else:
                # If sending fails, mark code as expired
                self.repos.verification.expire_previous_codes(request.telegram_id, request.phone_number)
                return self._format_error_response(
                    "Failed to send verification code via Telegram. Please try again."
                )

        except Exception as e:
            return self._format_error_response(f"Failed to send verification code: {str(e)}")

    def verify_code(self, request: VerifyCodeRequest) -> Dict[str, Any]:
        """Verify provided code and link Telegram account to user"""
        try:
            # Verify the code
            success, verification_code = self.repos.verification.verify_code(
                request.telegram_id,
                request.phone_number,
                request.code
            )

            if not verification_code:
                return self._format_error_response("No verification code found or code expired")

            attempts_remaining = max(0, verification_code.max_attempts - verification_code.verification_attempts)

            if success:
                # FIXED: Find user by phone number and learning center (not by telegram_id!)
                user = self.repos.user.get_by_phone_and_center(
                    request.phone_number,
                    request.learning_center_id
                )

                if not user:
                    return self._format_error_response(
                        "User account not found. Please contact your learning center administrator."
                    )

                # Check if learning center is still active
                if not user.learning_center.is_active:
                    return self._format_error_response(
                        "Learning center subscription expired. Please contact your administrator."
                    )

                # FIXED: Link Telegram account to user if not already linked
                is_new_link = False
                if not user.telegram_id:
                    user.telegram_id = request.telegram_id
                    is_new_link = True
                elif user.telegram_id != request.telegram_id:
                    return self._format_error_response(
                        "This phone number is already linked to a different Telegram account."
                    )

                # Verify the user account
                user.is_verified = True
                self.db.commit()
                self.db.refresh(user)

                response = VerifyCodeResponse(
                    success=True,
                    message="Phone number verified successfully. Account activated.",
                    user_verified=True,
                    attempts_remaining=attempts_remaining,
                    user_id=user.id,
                    is_new_user=is_new_link
                )
                return self._format_success_response(response.dict())
            else:
                message = "Invalid verification code"
                if attempts_remaining <= 0:
                    message = "Maximum verification attempts exceeded. Please request a new code."

                response = VerifyCodeResponse(
                    success=False,
                    message=message,
                    user_verified=False,
                    attempts_remaining=attempts_remaining
                )
                return self._format_success_response(response.dict())

        except Exception as e:
            return self._format_error_response(f"Verification failed: {str(e)}")

    def get_verification_status(self, request: VerificationStatusRequest) -> Dict[str, Any]:
        """Get current verification status"""
        try:
            stats = self.repos.verification.get_verification_stats(
                request.telegram_id,
                request.phone_number
            )

            # Check rate limiting status
            can_send, next_allowed = self.repos.verification.can_send_new_code(
                request.telegram_id,
                request.phone_number
            )

            response = VerificationStatusResponse(
                has_valid_code=stats["has_valid_code"],
                attempts_remaining=stats["attempts_remaining"],
                expires_at=stats["expires_at"],
                time_remaining_minutes=0,  # Will be calculated if has_valid_code
                can_request_new_code=can_send,
                rate_limited=not can_send,
                rate_limit_reset_at=next_allowed if not can_send else None
            )

            if stats["expires_at"]:
                remaining = stats["expires_at"] - datetime.utcnow()
                response.time_remaining_minutes = max(0, int(remaining.total_seconds() / 60))

            return self._format_success_response(response.dict())

        except Exception as e:
            return self._format_error_response(f"Failed to get verification status: {str(e)}")

    def resend_verification_code(self, request: ResendCodeRequest) -> Dict[str, Any]:
        """Resend verification code (convenience method)"""
        send_request = SendVerificationRequest(
            telegram_id=request.telegram_id,
            phone_number=request.phone_number,
            learning_center_id=request.learning_center_id
        )
        return self.send_verification_code(send_request)

    def cleanup_expired_codes(self, days_old: int = 7) -> Dict[str, Any]:
        """Cleanup old verification codes (system maintenance)"""
        try:
            deleted_count = self.repos.verification.cleanup_expired_codes(days_old)
            return self._format_success_response({
                "deleted_count": deleted_count
            }, f"Cleaned up {deleted_count} expired verification codes")
        except Exception as e:
            return self._format_error_response(f"Cleanup failed: {str(e)}")

    def get_user_verification_history(self, telegram_id: int, requester_id: int) -> Dict[str, Any]:
        """Get verification history for user (admin only)"""
        requester = self.repos.user.get(requester_id)
        if not requester or not requester.has_any_role(['admin', 'super_admin']):
            return self._format_error_response("Admin access required")

        try:
            # Get recent codes for this telegram ID
            recent_codes = self.repos.verification.get_recent_codes(telegram_id, hours=24)
            codes_data = [VerificationCodeResponse.from_orm(code) for code in recent_codes]

            return self._format_success_response({
                "telegram_id": telegram_id,
                "recent_codes": codes_data,
                "total_recent": len(codes_data)
            })
        except Exception as e:
            return self._format_error_response(f"Failed to get verification history: {str(e)}")

    def force_expire_user_codes(self, telegram_id: int, phone_number: str, requester_id: int) -> Dict[str, Any]:
        """Force expire all codes for user (admin emergency action)"""
        requester = self.repos.user.get(requester_id)
        if not requester or not requester.has_any_role(['admin', 'super_admin']):
            return self._format_error_response("Admin access required")

        try:
            expired_count = self.repos.verification.expire_previous_codes(telegram_id, phone_number)
            return self._format_success_response({
                "expired_count": expired_count
            }, f"Expired {expired_count} verification codes")
        except Exception as e:
            return self._format_error_response(f"Failed to expire codes: {str(e)}")

    def get_verification_stats_summary(self, requester_id: int) -> Dict[str, Any]:
        """Get system-wide verification statistics (super admin only)"""
        requester = self.repos.user.get(requester_id)
        if not requester or not requester.has_role('super_admin'):
            return self._format_error_response("Super admin access required")

        try:
            # Get statistics from database
            from app.models import VerificationCode

            # Today's stats
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_codes = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= today
            ).count()

            today_successful = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= today,
                VerificationCode.is_used == True
            ).count()

            # This week's stats
            week_ago = today - timedelta(days=7)
            week_codes = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= week_ago
            ).count()

            week_successful = self.db.query(VerificationCode).filter(
                VerificationCode.created_at >= week_ago,
                VerificationCode.is_used == True
            ).count()

            # Active codes
            active_codes = self.db.query(VerificationCode).filter(
                VerificationCode.is_used == False,
                VerificationCode.is_expired == False,
                VerificationCode.expires_at > datetime.utcnow()
            ).count()

            stats = {
                "today": {
                    "codes_sent": today_codes,
                    "successful_verifications": today_successful,
                    "success_rate": (today_successful / today_codes * 100) if today_codes > 0 else 0
                },
                "week": {
                    "codes_sent": week_codes,
                    "successful_verifications": week_successful,
                    "success_rate": (week_successful / week_codes * 100) if week_codes > 0 else 0
                },
                "current": {
                    "active_codes": active_codes
                }
            }

            return self._format_success_response(stats)
        except Exception as e:
            return self._format_error_response(f"Failed to get verification statistics: {str(e)}")

    # FIXED: Use configurable code generation
    def _generate_verification_code(self, length: int = 6) -> str:
        """Generate verification code of specified length"""
        return ''.join(random.choices(string.digits, k=length))

    def _send_telegram_message(self, telegram_id: int, code: str) -> bool:
        """Send verification code via Telegram Bot API"""
        try:
            # Get bot token from environment
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                print("ERROR: BOT_TOKEN not found in environment variables")
                return False

            # Telegram Bot API URL
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # FIXED: Use configuration for message template
            expires_minutes = 10
            message = f"""🔐 **Verification Code**

Your verification code is: `{code}`

This code will expire in {expires_minutes} minutes.

Please do not share this code with anyone."""

            # Request payload
            payload = {
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            # Send request to Telegram API
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"SUCCESS: Verification code sent to Telegram ID {telegram_id}")
                    return True
                else:
                    print(f"ERROR: Telegram API error: {result.get('description', 'Unknown error')}")
                    return False
            else:
                print(f"ERROR: HTTP {response.status_code} - Failed to send message")
                return False

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error while sending Telegram message: {str(e)}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error while sending Telegram message: {str(e)}")
            return False

    def test_telegram_connection(self, requester_id: int) -> Dict[str, Any]:
        """Test Telegram Bot connection (admin only)"""
        requester = self.repos.user.get(requester_id)
        if not requester or not requester.has_any_role(['admin', 'super_admin']):
            return self._format_error_response("Admin access required")

        try:
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                return self._format_error_response("BOT_TOKEN not configured")

            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    return self._format_success_response({
                        "bot_connected": True,
                        "bot_username": bot_info.get("username"),
                        "bot_first_name": bot_info.get("first_name"),
                        "message": "Telegram bot connection successful"
                    })

            return self._format_error_response("Failed to connect to Telegram Bot API")

        except Exception as e:
            return self._format_error_response(f"Telegram connection test failed: {str(e)}")

    def validate_phone_format(self, phone_number: str) -> Dict[str, Any]:
        """Validate phone number format"""
        import re

        try:
            # Basic phone validation - international format required
            phone_pattern = r'^\+[1-9]\d{9,19}$'

            # Clean phone number
            cleaned = re.sub(r'[\s\-\(\)]', '', phone_number.strip())

            is_valid = bool(re.match(phone_pattern, cleaned))

            if is_valid:
                return self._format_success_response({
                    "is_valid": True,
                    "original": phone_number,
                    "cleaned": cleaned,
                    "format": "international"
                }, "Phone number format is valid")
            else:
                return self._format_error_response(
                    "Invalid phone number format. Please use international format (+1234567890)"
                )

        except Exception as e:
            return self._format_error_response(f"Phone validation failed: {str(e)}")

    def get_rate_limit_status(self, telegram_id: int, phone_number: str = "") -> Dict[str, Any]:
        """Check current rate limit status for telegram ID"""
        try:
            can_send, next_allowed = self.repos.verification.can_send_new_code(
                telegram_id,
                phone_number,
                cooldown_minutes=1
            )

            if can_send:
                return self._format_success_response({
                    "can_send": True,
                    "message": "No rate limit restrictions"
                })
            else:
                seconds_remaining = int((next_allowed - datetime.utcnow()).total_seconds())
                return self._format_success_response({
                    "can_send": False,
                    "seconds_remaining": max(0, seconds_remaining),
                    "next_allowed": next_allowed,
                    "message": f"Rate limited. Try again in {max(0, seconds_remaining)} seconds."
                })

        except Exception as e:
            return self._format_error_response(f"Failed to check rate limit: {str(e)}")