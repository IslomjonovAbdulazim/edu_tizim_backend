from typing import Dict, Any
from sqlalchemy.orm import Session
import random
import string
import requests
import os
from datetime import datetime
from app.schemas import (
    SendVerificationRequest, SendVerificationResponse,
    VerifyCodeRequest, VerifyCodeResponse,
)
from app.services.base import BaseService


class VerificationService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def send_verification_code(self, request: SendVerificationRequest) -> Dict[str, Any]:
        """Send verification code to user via Telegram"""
        try:
            # Check if phone is blocked
            if self.repos.verification.is_phone_blocked(request.phone_number):
                return self._format_error_response("Phone number temporarily blocked. Try again later.")

            # Check rate limiting
            can_send, next_allowed = self.repos.verification.can_send_code(
                request.telegram_id,
                request.phone_number
            )

            if not can_send:
                seconds_remaining = int((next_allowed - datetime.utcnow()).total_seconds()) + 1
                return self._format_error_response(
                    f"Please wait {seconds_remaining} seconds before requesting a new code"
                )

            # Generate 6-digit code
            code = ''.join(random.choices(string.digits, k=6))

            # Create verification code record
            verification_code = self.repos.verification.create_code(
                telegram_id=request.telegram_id,
                phone_number=request.phone_number,
                code=code
            )

            # Send code via Telegram Bot API
            success = self._send_telegram_message(request.telegram_id, code)

            if success:
                response = SendVerificationResponse(
                    success=True,
                    message="Verification code sent successfully",
                    expires_at=verification_code.expires_at,
                    attempts_remaining=verification_code.attempts_remaining
                )
            else:
                # Mark as expired if sending failed
                verification_code.is_expired = True
                self.db.commit()

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

            if success:
                # Find or create user
                user = self.repos.user.get_by_telegram_id(request.telegram_id)

                if not user:
                    # Create new user
                    # TODO: Get learning_center_id from phone number or other logic
                    learning_center_id = 1  # Placeholder - implement your logic here

                    user_data = {
                        "telegram_id": request.telegram_id,
                        "phone_number": request.phone_number,
                        "full_name": f"User {request.telegram_id}",  # Can be updated later
                        "learning_center_id": learning_center_id,
                        "role": "student",
                        "is_verified": True
                    }
                    user = self.repos.user.create(user_data)
                else:
                    # Update existing user
                    user.is_verified = True
                    user.phone_number = request.phone_number
                    self.db.commit()
                    self.db.refresh(user)

                response = VerifyCodeResponse(
                    success=True,
                    message="Phone number verified successfully",
                    user_verified=True,
                    attempts_remaining=verification_code.attempts_remaining,
                    user_data={
                        "id": user.id,
                        "full_name": user.full_name,
                        "phone_number": user.phone_number,
                        "role": user.role,
                        "learning_center_id": user.learning_center_id
                    }
                )
            else:
                message = "Invalid verification code"
                if verification_code.attempts_remaining <= 0:
                    message = "Maximum verification attempts exceeded. Please request a new code."

                response = VerifyCodeResponse(
                    success=False,
                    message=message,
                    user_verified=False,
                    attempts_remaining=verification_code.attempts_remaining
                )

            return self._format_success_response(response)

        except Exception as e:
            return self._format_error_response(f"Verification failed: {str(e)}")

    def get_verification_status(self, telegram_id: int, phone_number: str) -> Dict[str, Any]:
        """Get current verification status (for telegram bot)"""
        try:
            verification_code = self.repos.verification.get_valid_code(telegram_id, phone_number)
            from app.schemas.verification import VerificationStatusResponse

            if verification_code:
                response = VerificationStatusResponse(
                    has_valid_code=True,
                    code=verification_code.code,  # Return actual code for bot
                    expires_at=verification_code.expires_at,
                    attempts_remaining=verification_code.attempts_remaining
                )
            else:
                response = VerificationStatusResponse(
                    has_valid_code=False,
                    attempts_remaining=0
                )

            return self._format_success_response(response)

        except Exception as e:
            return self._format_error_response(f"Failed to get verification status: {str(e)}")

    def get_rate_limit_status(self, telegram_id: int, phone_number: str) -> Dict[str, Any]:
        """Check current rate limit status"""
        try:
            can_send, next_allowed = self.repos.verification.can_send_code(telegram_id, phone_number)
            from app.schemas.verification import RateLimitResponse

            if can_send:
                response = RateLimitResponse(
                    can_send=True,
                    message="No rate limit restrictions"
                )
            else:
                seconds_remaining = int((next_allowed - datetime.utcnow()).total_seconds())
                response = RateLimitResponse(
                    can_send=False,
                    seconds_remaining=max(0, seconds_remaining),
                    message=f"Please wait {max(0, seconds_remaining)} seconds"
                )

            return self._format_success_response(response)

        except Exception as e:
            return self._format_error_response(f"Failed to check rate limit: {str(e)}")

    def _send_telegram_message(self, telegram_id: int, code: str) -> bool:
        """Send verification code via Telegram Bot API"""
        try:
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                print("ERROR: BOT_TOKEN not found")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            message = f"🔐 **Your Verification Code**\n\n" \
                      f"Code: `{code}`\n\n" \
                      f"⏱ This code will expire in 10 minutes.\n" \
                      f"Please do not share this code with anyone."

            payload = {
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"SUCCESS: Verification code sent to {telegram_id}")
                    return True
                else:
                    print(f"ERROR: Telegram API error: {result.get('description')}")
                    return False
            else:
                print(f"ERROR: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"ERROR: Failed to send message: {e}")
            return False