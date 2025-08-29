import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx
from telegram_bot.config import bot_settings, APIEndpoints
from telegram_bot.utils.keyboards import get_main_keyboard, get_phone_request_keyboard
from telegram_bot.utils.helpers import is_valid_verification_code

logger = logging.getLogger(__name__)


class VerificationHandler:
    def __init__(self):
        self.api_base = bot_settings.API_BASE_URL

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (verification codes, phone numbers)"""
        text = update.message.text.strip()
        user = update.effective_user
        telegram_id = user.id

        # Check if it's a verification code (6 digits)
        if is_valid_verification_code(text):
            await self._handle_verification_code(update, context, text)

        # Check if it's a phone number
        elif self._is_phone_number(text):
            await self._handle_typed_phone_number(update, context, text)

        # Unknown message
        else:
            await update.message.reply_text(
                "🤔 I didn't understand that.\n\n"
                "📱 Share your phone number using the button below, or\n"
                "🔐 Enter your 6-digit verification code, or\n"
                "ℹ️ Use /help to see available commands."
            )

    async def _handle_verification_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Handle verification code input"""
        user = update.effective_user
        telegram_id = user.id

        try:
            # TODO: API Call - Verify code
            # Expected API: POST /api/v1/auth/verify-code
            # Body: {"telegram_id": telegram_id, "code": code, "phone_number": "user_phone_from_context_or_db"}
            # Response: {"success": true, "message": "Verified successfully", "user": {...}, "user_verified": true}
            # OR: {"success": false, "message": "Invalid code", "attempts_remaining": 2}

            # For demo, we need to get phone number (would come from context or previous API call)
            # In real implementation, you'd store this in context.user_data when phone is shared
            user_phone = context.user_data.get('phone_number', '+998901234567')  # Placeholder

            # Simulate API call
            verification_success = True  # From API
            user_data = {  # From API response
                "id": 1,
                "full_name": "John Doe",
                "phone_number": user_phone,
                "is_verified": True,
                "learning_center_name": "ABC Learning Center",
                "role": "student"
            }
            attempts_remaining = 2  # From API if failed

            if verification_success:
                # Clear any stored temporary data
                context.user_data.clear()

                success_message = bot_settings.SUCCESS_LOGIN_MESSAGE.format(
                    name=user_data.get('full_name', 'Student')
                )

                await update.message.reply_text(
                    success_message + f"\n\n"
                                      f"🏢 Learning Center: {user_data.get('learning_center_name', 'Not assigned')}\n"
                                      f"📚 Role: {user_data.get('role', 'Student').title()}",
                    reply_markup=get_main_keyboard()
                )

                # Send additional welcome info
                await update.message.reply_text(
                    "🎯 *What you can do now:*\n\n"
                    "📊 View your progress\n"
                    "📝 Take quizzes\n"
                    "🏆 Check leaderboard\n"
                    "🎖 View your badges\n"
                    "📱 Update your profile\n\n"
                    "Use the menu buttons below to get started!",
                    parse_mode='Markdown'
                )

            else:
                # Verification failed
                error_message = bot_settings.ERROR_INVALID_CODE
                if attempts_remaining <= 0:
                    error_message = bot_settings.ERROR_MAX_ATTEMPTS
                    # Offer to request new code
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Request New Code", callback_data="request_new_code")]
                    ])

                    await update.message.reply_text(
                        error_message + "\n\nWould you like to request a new verification code?",
                        reply_markup=keyboard
                    )
                else:
                    await update.message.reply_text(
                        f"{error_message}\n\n"
                        f"🔄 Attempts remaining: {attempts_remaining}\n"
                        f"Please try again."
                    )

        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            await update.message.reply_text(
                bot_settings.ERROR_GENERAL
            )

    async def _handle_typed_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
        """Handle phone number typed as text"""
        from telegram_bot.utils.helpers import format_phone_number, is_valid_phone

        formatted_phone = format_phone_number(phone)

        if not is_valid_phone(formatted_phone):
            await update.message.reply_text(
                "❌ Invalid phone number format.\n\n"
                "Please use format: +998901234567\n"
                "Or use the button below to share your contact:",
                reply_markup=get_phone_request_keyboard()
            )
            return

        # Store phone number for verification
        context.user_data['phone_number'] = formatted_phone

        try:
            # TODO: API Call - Request verification code for typed phone number
            # Expected API: POST /api/v1/auth/request-verification-code
            # Body: {"telegram_id": telegram_id, "phone_number": formatted_phone}
            # Response: {"success": true, "message": "Code sent", "expires_at": "...", "attempts_remaining": 3}

            # Simulate API call
            success = True

            if success:
                await update.message.reply_text(
                    f"📱 Phone number: `{formatted_phone}`\n\n"
                    f"🔐 Verification code sent to this chat!\n"
                    f"Please check the message above.",
                    parse_mode='Markdown'
                )

                # Auto-send verification code (simulate)
                verification_code = "654321"  # From API or generated

                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"🔐 **Your Verification Code**\n\n"
                         f"Code: `{verification_code}`\n\n"
                         f"⏱ This code will expire in 10 minutes.\n"
                         f"Please enter this code to verify your account.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to send verification code.\n"
                    "Please try again or contact support."
                )

        except Exception as e:
            logger.error(f"Error handling typed phone number: {e}")
            await update.message.reply_text(
                "❌ Something went wrong. Please try again."
            )

    async def handle_request_new_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback query for requesting new verification code"""
        query = update.callback_query
        await query.answer()

        telegram_id = update.effective_user.id

        try:
            # TODO: API Call - Get user's phone number first
            # Expected API: GET /api/v1/users/by-telegram/{telegram_id}
            # Response: {"success": true, "data": {"phone_number": "+998901234567"}}

            user_phone = context.user_data.get('phone_number', '+998901234567')  # From API or context

            # TODO: API Call - Request new verification code
            # Expected API: POST /api/v1/auth/request-verification-code
            # Body: {"telegram_id": telegram_id, "phone_number": user_phone}
            # Response: {"success": true, "message": "New code sent"} OR {"success": false, "message": "Rate limited"}

            # Simulate API call
            success = True
            rate_limited = False

            if rate_limited:
                await query.edit_message_text(
                    bot_settings.ERROR_RATE_LIMITED
                )
            elif success:
                await query.edit_message_text(
                    f"✅ New verification code has been sent!\n\n"
                    f"📱 Phone: {user_phone}\n"
                    f"🔐 Check the message above for your new code."
                )

                # Send new code
                new_code = "789012"  # From API

                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🔐 **New Verification Code**\n\n"
                         f"Code: `{new_code}`\n\n"
                         f"⏱ This code will expire in 10 minutes.\n"
                         f"Please enter this code to verify your account.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to send new code. Please try again later."
                )

        except Exception as e:
            logger.error(f"Error requesting new code: {e}")
            await query.edit_message_text(
                "❌ Something went wrong. Please try /start again."
            )

    async def handle_cancel_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback query for canceling verification"""
        query = update.callback_query
        await query.answer()

        # Clear user data
        context.user_data.clear()

        await query.edit_message_text(
            "❌ Verification cancelled.\n\n"
            "Use /start to begin registration again."
        )

    def _is_phone_number(self, text: str) -> bool:
        """Check if text looks like a phone number"""
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', text)

        # Check patterns
        patterns = [
            r'^\+998\d{9}$',  # +998xxxxxxxxx
            r'^998\d{9}$',  # 998xxxxxxxxx
            r'^\d{9}$',  # xxxxxxxxx
            r'^\+\d{10,15}$'  # International format
        ]

        return any(re.match(pattern, cleaned) for pattern in patterns)

    async def check_rate_limit(self, telegram_id: int) -> tuple[bool, int]:
        """Check if user is rate limited"""
        try:
            # TODO: API Call - Check rate limit status
            # Expected API: GET /api/v1/auth/rate-limit-status?telegram_id={telegram_id}
            # Response: {"success": true, "data": {"can_send": true, "seconds_remaining": 0}}

            can_send = True
            seconds_remaining = 0

            return can_send, seconds_remaining

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True, 0  # Allow by default if API fails