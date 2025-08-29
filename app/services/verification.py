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
    VerificationCodeResponse
)
from app.services.base import BaseService


class VerificationService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def send_verification_code(self, request: SendVerificationRequest) -> Dict[str, Any]:
        """Send verification code to user via Telegram"""
        # Check if phone is temporarily blocked
        if self.repos.verification.is_phone_blocked(request.phone_number):
            return self._format_error_response("Phone number temporarily blocked due to too many failed attempts")

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

        # Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))

        try:
            # Create verification code record
            verification_code = self.repos.verification.create_verification_code(
                telegram_id=request.telegram_id,
                phone_number=request.phone_number,
                code=code,
                expires_in_minutes=10
            )

            # TODO: Send code via Telegram Bot API
            # This would typically integrate with your Telegram bot
            # For now, we'll simulate successful sending
            success = self._send_telegram_message(request.telegram_id, code)

            if success:
                response = SendVerificationResponse(
                    success=True,
                    message="Verification code sent successfully",
                    expires_at=verification_code.expires_at,
                    attempts_remaining=verification_code.max_attempts
                )
            else:
                # If sending fails, mark code as expired
                self.repos.verification.expire_previous_codes(request.telegram_id, request.phone_number)
                response = SendVerificationResponse(
                    success=False,
                    message="Failed to send verification code. Please try again.",
                    expires_at=verification_code.expires_at,
                    attempts_remaining=0
                )

            return self._format_success_response(response)

        except Exception as e:
            return self._format_error_response(f"Failed to send verification code: {str(e)}")

    def verify_code(self, request: VerifyCodeRequest) -> Dict[str, Any]:
        """Verify provided code"""
        try:
            success, verification_code = self.repos.verification.verify_code(
                request.telegram_id,
                request.phone_number,
                request.code
            )

            if not verification_code:
                return self._format_error_response("No verification code found or code expired")

            attempts_remaining = max(0, verification_code.max_attempts - verification_code.verification_attempts)

            if success:
                # Find and verify the user
                user = self.repos.user.get_by_telegram_id(request.telegram_id)
                if user and user.phone_number == request.phone_number:
                    # Verify the user account
                    self.repos.user.verify_user(user.id)

                response = VerifyCodeResponse(
                    success=True,
                    message="Phone number verified successfully",
                    user_verified=True,
                    attempts_remaining=attempts_remaining
                )
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

            return self._format_success_response(response)

        except Exception as e:
            return self._format_error_response(f"Verification failed: {str(e)}")

    def get_verification_status(self, telegram_id: int, phone_number: str) -> Dict[str, Any]:
        """Get current verification status"""
        stats = self.repos.verification.get_verification_stats(telegram_id, phone_number)

        return self._format_success_response({
            "has_valid_code": stats["has_valid_code"],
            "attempts_remaining": stats["attempts_remaining"],
            "expires_at": stats["expires_at"],
            "recent_attempts": stats["recent_attempts"],
            "total_codes_sent": stats["total_codes_sent"],
            "successful_verifications": stats["successful_verifications"]
        })

    def resend_verification_code(self, telegram_id: int, phone_number: str) -> Dict[str, Any]:
        """Resend verification code (convenience method)"""
        request = SendVerificationRequest(
            telegram_id=telegram_id,
            phone_number=phone_number
        )
        return self.send_verification_code(request)

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

        # Get recent codes for this telegram ID
        recent_codes = self.repos.verification.get_recent_codes(telegram_id, hours=24)
        codes_data = [VerificationCodeResponse.from_orm(code) for code in recent_codes]

        return self._format_success_response({
            "telegram_id": telegram_id,
            "recent_codes": codes_data,
            "total_recent": len(codes_data)
        })

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

        # Get statistics from database
        from app.models import VerificationCode
        from datetime import datetime, timedelta

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

            # Compose message
            message = f"""🔐 **Verification Code**

Your verification code is: `{code}`

This code will expire in 10 minutes.

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

        # TODO: Implement actual bot connection test
        # This would typically call getMe endpoint of Telegram Bot API

        return self._format_success_response({
            "bot_connected": True,  # Placeholder
            "bot_username": "your_bot_username",  # Placeholder
            "message": "Telegram bot connection successful"
        })

    def validate_phone_format(self, phone_number: str) -> Dict[str, Any]:
        """Validate phone number format"""
        import re

        # Basic phone validation - adjust pattern for your needs
        # This pattern accepts various international formats
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,15}$'

        is_valid = bool(re.match(phone_pattern, phone_number.strip()))

        if is_valid:
            # Clean phone number (remove spaces, dashes, etc.)
            cleaned = ''.join(filter(str.isdigit, phone_number))
            if phone_number.startswith('+'):
                cleaned = '+' + cleaned

            return self._format_success_response({
                "is_valid": True,
                "original": phone_number,
                "cleaned": cleaned
            }, "Phone number format is valid")
        else:
            return self._format_error_response("Invalid phone number format")

    def get_rate_limit_status(self, telegram_id: int) -> Dict[str, Any]:
        """Check current rate limit status for telegram ID"""
        can_send, next_allowed = self.repos.verification.can_send_new_code(telegram_id, "", cooldown_minutes=1)

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