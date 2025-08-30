from typing import Dict, Any
from sqlalchemy.orm import Session
import random
import string
import requests
import os
from datetime import datetime
from app.schemas.verification import (
    SendVerificationRequest, VerifyCodeRequest, VerificationStatusRequest
)
from app.services.base import BaseService


class VerificationService(BaseService):
    """Verification service for phone verification via Telegram"""

    def __init__(self, db: Session):
        super().__init__(db)

    def send_verification_code(self, request: SendVerificationRequest) -> Dict[str, Any]:
        """Send verification code to user via Telegram"""
        try:
            # Check if user exists in learning center
            user = self.repos.user.get_by_phone_and_center(
                request.phone_number,
                request.learning_center_id
            )

            if not user:
                return self._format_error_response(
                    "Phone number not found in this learning center"
                )

            # Check if learning center is active
            if not self._check_center_active(request.learning_center_id):
                return self._format_error_response("Learning center subscription expired")

            # Check if phone is blocked
            if self.repos.verification.is_phone_blocked(request.phone_number):
                return self._format_error_response(
                    "Phone number temporarily blocked due to too many failed attempts"
                )

            # Check rate limiting
            can_send, next_allowed = self.repos.verification.can_send_new_code(
                request.telegram_id,
                request.phone_number
            )

            if not can_send:
                minutes_remaining = int((next_allowed - datetime.utcnow()).total_seconds() / 60) + 1
                return self._format_error_response(
                    f"Please wait {minutes_remaining} minute(s) before requesting a new code"
                )

            # Generate verification code
            code = self._generate_verification_code()

            # Create verification record
            verification_code = self.repos.verification.create_verification_code(
                telegram_id=request.telegram_id,
                phone_number=request.phone_number,
                code=code,
                expires_in_minutes=10
            )

            # Send code via Telegram
            if self._send_telegram_message(request.telegram_id, code):
                return self._format_success_response({
                    "message": "Verification code sent successfully",
                    "expires_at": verification_code.expires_at,
                    "attempts_remaining": verification_code.max_attempts,
                    "expires_in_minutes": 10
                })
            else:
                # Mark code as expired if sending failed
                self.repos.verification.expire_previous_codes(request.telegram_id, request.phone_number)
                return self._format_error_response("Failed to send verification code")

        except Exception as e:
            return self._format_error_response(f"Failed to send verification code: {str(e)}")

    def verify_code(self, request: VerifyCodeRequest) -> Dict[str, Any]:
        """Verify code and activate user account"""
        try:
            # Verify the code
            is_valid, verification_code = self.repos.verification.verify_code(
                request.telegram_id,
                request.phone_number,
                request.code
            )

            if not verification_code:
                return self._format_error_response("No verification code found or expired")

            attempts_remaining = max(0, verification_code.max_attempts - verification_code.attempts)

            if is_valid:
                # Find user by phone and learning center
                user = self.repos.user.get_by_phone_and_center(
                    request.phone_number,
                    request.learning_center_id
                )

                if not user:
                    return self._format_error_response("User account not found")

                # Check learning center is still active
                if not self._check_center_active(request.learning_center_id):
                    return self._format_error_response("Learning center subscription expired")

                # Link Telegram ID if not already linked
                if not user.telegram_id:
                    self.repos.user.link_telegram(user.id, request.telegram_id)
                elif user.telegram_id != request.telegram_id:
                    return self._format_error_response(
                        "Phone number is linked to a different Telegram account"
                    )

                # Verify user account
                from app.services.user import UserService
                user_service = UserService(self.db)
                result = user_service.verify_user(user.id)

                if result["success"]:
                    return self._format_success_response({
                        "message": "Phone verified successfully. Account activated.",
                        "user_verified": True,
                        "user_id": user.id,
                        "attempts_remaining": attempts_remaining
                    })
                else:
                    return self._format_error_response("Failed to verify user account")

            else:
                # Verification failed
                message = "Invalid verification code"
                if attempts_remaining <= 0:
                    message = "Maximum verification attempts exceeded. Please request a new code."

                return self._format_success_response({
                    "success": False,
                    "message": message,
                    "user_verified": False,
                    "attempts_remaining": attempts_remaining
                })

        except Exception as e:
            return self._format_error_response(f"Verification failed: {str(e)}")

    def get_verification_status(self, request: VerificationStatusRequest) -> Dict[str, Any]:
        """Get current verification status for user"""
        try:
            # Get verification statistics
            stats = self.repos.verification.get_verification_stats(
                request.telegram_id,
                request.phone_number
            )

            # Check rate limiting
            can_send, next_allowed = self.repos.verification.can_send_new_code(
                request.telegram_id,
                request.phone_number
            )

            time_remaining_minutes = 0
            if stats["expires_at"]:
                remaining = stats["expires_at"] - datetime.utcnow()
                time_remaining_minutes = max(0, int(remaining.total_seconds() / 60))

            return self._format_success_response({
                "has_valid_code": stats["has_valid_code"],
                "attempts_remaining": stats["attempts_remaining"],
                "expires_at": stats["expires_at"],
                "time_remaining_minutes": time_remaining_minutes,
                "can_request_new_code": can_send,
                "rate_limited": not can_send,
                "rate_limit_reset_at": next_allowed if not can_send else None
            })

        except Exception as e:
            return self._format_error_response(f"Failed to get verification status: {str(e)}")

    def cleanup_expired_codes(self, days_old: int = 7) -> Dict[str, Any]:
        """Clean up old verification codes (system maintenance)"""
        try:
            deleted_count = self.repos.verification.cleanup_expired_codes(days_old)
            return self._format_success_response({
                "deleted_count": deleted_count
            }, f"Cleaned up {deleted_count} expired verification codes")

        except Exception as e:
            return self._format_error_response(f"Cleanup failed: {str(e)}")

    def get_verification_analytics(self, requester_id: int, days: int = 30) -> Dict[str, Any]:
        """Get verification system analytics (admin only)"""
        if not self._check_permissions(requester_id, ["admin", "super_admin"]):
            return self._format_error_response("Admin access required")

        try:
            stats = self.repos.verification.get_system_stats(days)
            return self._format_success_response(stats)

        except Exception as e:
            return self._format_error_response(f"Failed to get analytics: {str(e)}")

    def get_suspicious_activity(self, requester_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get suspicious verification activity (admin only)"""
        if not self._check_permissions(requester_id, ["admin", "super_admin"]):
            return self._format_error_response("Admin access required")

        try:
            suspicious = self.repos.verification.get_suspicious_activity(hours)
            return self._format_success_response({
                "suspicious_activity": suspicious,
                "total_incidents": len(suspicious)
            })

        except Exception as e:
            return self._format_error_response(f"Failed to get suspicious activity: {str(e)}")

    def force_expire_codes(self, telegram_id: int, phone_number: str, requester_id: int) -> Dict[str, Any]:
        """Force expire codes for user (admin emergency action)"""
        if not self._check_permissions(requester_id, ["admin", "super_admin"]):
            return self._format_error_response("Admin access required")

        try:
            expired_count = self.repos.verification.force_expire_codes(telegram_id, phone_number)
            return self._format_success_response({
                "expired_count": expired_count
            }, f"Expired {expired_count} verification codes")

        except Exception as e:
            return self._format_error_response(f"Failed to expire codes: {str(e)}")

    def _generate_verification_code(self, length: int = 6) -> str:
        """Generate random verification code"""
        return ''.join(random.choices(string.digits, k=length))

    def _send_telegram_message(self, telegram_id: int, code: str) -> bool:
        """Send verification code via Telegram Bot API"""
        try:
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                print("ERROR: BOT_TOKEN not found in environment")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            message = f"""🔐 **Verification Code**

Your verification code is: `{code}`

This code will expire in 10 minutes.
Please do not share this code with anyone."""

            payload = {
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return result.get("ok", False)

            return False

        except Exception as e:
            print(f"ERROR: Failed to send Telegram message: {str(e)}")
            return False