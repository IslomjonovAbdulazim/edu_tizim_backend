import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import httpx
from telegram_bot.config import bot_settings, APIEndpoints
from telegram_bot.utils.keyboards import get_main_keyboard, get_phone_request_keyboard
from telegram_bot.utils.helpers import format_phone_number, is_valid_phone

logger = logging.getLogger(__name__)


class AuthHandler:
    def __init__(self):
        self.api_base = bot_settings.API_BASE_URL

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        telegram_id = user.id

        try:
            # TODO: API Call - Check if user exists by telegram_id
            # Expected API: GET /api/v1/users/by-telegram/{telegram_id}
            # Response: {"success": true, "data": {"id": 1, "full_name": "John", "phone_number": "+998901234567", "is_verified": true}}
            # OR: {"success": false, "message": "User not found"}

            # For now, simulate API call
            user_exists = False  # This should come from API
            user_data = None  # This should come from API

            if user_exists and user_data:
                # User exists, check verification status
                if user_data.get('is_verified'):
                    await update.message.reply_text(
                        f"🎓 Welcome back, {user_data.get('full_name', 'Student')}!\n\n"
                        f"Your account is verified and ready to use.\n"
                        f"Phone: {user_data.get('phone_number')}\n\n"
                        f"Use the menu below to access your learning dashboard:",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    # User exists but not verified, check for pending codes
                    await self._check_verification_status(update, context, user_data)
            else:
                # New user, request phone number
                await self._request_phone_number(update, context)

        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            await update.message.reply_text(
                "❌ Something went wrong. Please try again later."
            )

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        telegram_id = user.id

        try:
            # TODO: API Call - Get user status
            # Expected API: GET /api/v1/users/by-telegram/{telegram_id}
            # Response: User data with verification status

            # For now, simulate
            user_exists = False

            if not user_exists:
                await update.message.reply_text(
                    "👤 *Account Status: Not Registered*\n\n"
                    "You haven't registered yet. Use /start to begin registration.",
                    parse_mode='Markdown'
                )
                return

            # TODO: Get actual user data from API
            user_data = {}  # From API

            status_text = f"👤 *Account Status*\n\n"
            status_text += f"📱 Telegram ID: `{telegram_id}`\n"
            status_text += f"👨‍💼 Name: {user_data.get('full_name', 'Not set')}\n"
            status_text += f"📞 Phone: {user_data.get('phone_number', 'Not set')}\n"
            status_text += f"✅ Verified: {'Yes' if user_data.get('is_verified') else 'No'}\n"
            status_text += f"🏢 Learning Center: {user_data.get('learning_center_name', 'Not assigned')}\n"
            status_text += f"🏫 Branch: {user_data.get('branch_name', 'Not assigned')}\n"

            await update.message.reply_text(status_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in handle_status: {e}")
            await update.message.reply_text("❌ Could not retrieve status. Please try again.")

    async def handle_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number sharing"""
        if not update.message.contact:
            await update.message.reply_text(
                "❌ Please share your phone number using the button below.",
                reply_markup=get_phone_request_keyboard()
            )
            return

        phone_number = update.message.contact.phone_number
        telegram_id = update.effective_user.id

        # Format phone number
        formatted_phone = format_phone_number(phone_number)

        if not is_valid_phone(formatted_phone):
            await update.message.reply_text(
                "❌ Invalid phone number format. Please try again.",
                reply_markup=get_phone_request_keyboard()
            )
            return

        try:
            # TODO: API Call - Request verification code
            # Expected API: POST /api/v1/auth/request-verification-code
            # Body: {"telegram_id": telegram_id, "phone_number": formatted_phone}
            # Response: {"success": true, "message": "Code sent", "expires_at": "...", "attempts_remaining": 3}

            # For now, simulate successful request
            success = True  # From API

            if success:
                await update.message.reply_text(
                    f"📱 Phone number received: `{formatted_phone}`\n\n"
                    f"🔐 A verification code has been sent to this chat.\n"
                    f"Please wait a moment...",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )

                # Simulate sending code (in real implementation, this would come from API)
                verification_code = "123456"  # This should come from API response or be sent automatically

                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🔐 **Your Verification Code**\n\n"
                         f"Code: `{verification_code}`\n\n"
                         f"⏱ This code will expire in 10 minutes.\n"
                         f"Please do not share this code with anyone.",
                    parse_mode='Markdown'
                )

            else:
                await update.message.reply_text(
                    "❌ Failed to send verification code. Please try again later.",
                    reply_markup=get_phone_request_keyboard()
                )

        except Exception as e:
            logger.error(f"Error handling phone number: {e}")
            await update.message.reply_text(
                "❌ Something went wrong. Please try again.",
                reply_markup=get_phone_request_keyboard()
            )

    async def _request_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request phone number from new user"""
        welcome_text = bot_settings.WELCOME_MESSAGE

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_phone_request_keyboard()
        )

    async def _check_verification_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Check if user has pending verification codes"""
        telegram_id = update.effective_user.id
        phone_number = user_data.get('phone_number')

        try:
            # TODO: API Call - Check verification status
            # Expected API: GET /api/v1/auth/verification-status?telegram_id={telegram_id}&phone_number={phone_number}
            # Response: {"success": true, "data": {"has_valid_code": true, "code": "123456", "expires_at": "...", "attempts_remaining": 2}}

            # For now, simulate
            has_valid_code = True  # From API
            code_data = {  # From API
                "code": "123456",
                "expires_at": "2024-01-01T12:00:00",
                "attempts_remaining": 3
            }

            if has_valid_code:
                await update.message.reply_text(
                    f"📱 Welcome back!\n\n"
                    f"You have a pending verification code.\n"
                    f"Phone: {phone_number}\n\n"
                    f"🔐 Your current verification code: `{code_data['code']}`\n"
                    f"⏱ Expires at: {code_data['expires_at']}\n"
                    f"🔄 Attempts remaining: {code_data['attempts_remaining']}\n\n"
                    f"Please enter this code to complete verification.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📱 Welcome back!\n\n"
                    f"Phone: {phone_number}\n"
                    f"❌ No verification code available.\n\n"
                    f"Please request a new verification code.",
                    reply_markup=get_phone_request_keyboard()
                )

        except Exception as e:
            logger.error(f"Error checking verification status: {e}")
            await update.message.reply_text(
                "❌ Could not check verification status. Please try /start again."
            )

    async def handle_logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle logout (clear local data)"""
        # Clear any stored context data
        context.user_data.clear()

        await update.message.reply_text(
            "👋 You have been logged out.\n\n"
            "Use /start to begin again.",
            reply_markup=ReplyKeyboardRemove()
        )