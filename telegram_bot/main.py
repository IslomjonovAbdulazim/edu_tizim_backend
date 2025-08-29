import asyncio
import logging
import sys
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext import CallbackQueryHandler

# Load environment variables
load_dotenv()

from telegram_bot.config import bot_settings, BotConfig
from telegram_bot.handlers.auth import AuthHandler
from telegram_bot.handlers.verification import VerificationHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, bot_settings.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


class LanguageLearningBot:
    def __init__(self):
        self.application = None
        self.auth_handler = AuthHandler()
        self.verification_handler = VerificationHandler()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        await self.auth_handler.handle_start(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "🎓 *Language Learning Center Bot*\n\n"
            "*Available Commands:*\n"
            "/start - Start the registration process\n"
            "/help - Show this help message\n"
            "/status - Check your account status\n\n"
            "*How to use:*\n"
            "1️⃣ Share your phone number\n"
            "2️⃣ Enter the verification code you receive\n"
            "3️⃣ Access your learning dashboard\n\n"
            "*Features:*\n"
            "📊 Track your learning progress\n"
            "🎯 Take interactive quizzes\n"
            "🏆 Compete on leaderboards\n"
            "🎖 Earn badges and achievements\n"
            "📚 Access course materials\n\n"
            "Need help? Contact your learning center administrator."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command"""
        await self.auth_handler.handle_status(update, context)

    async def handle_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number sharing"""
        await self.auth_handler.handle_phone_number(update, context)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (verification codes, phone numbers, menu selections)"""
        text = update.message.text

        # Handle menu selections
        if text in ["📊 My Progress", "🎯 Take Quiz", "🏆 Leaderboard", "🎖 My Badges", "👤 Profile", "ℹ️ Help"]:
            await self._handle_menu_selection(update, context, text)
        else:
            # Handle verification codes and phone numbers
            await self.verification_handler.handle_text_message(update, context)

    async def _handle_menu_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selection: str):
        """Handle main menu selections"""
        if selection == "📊 My Progress":
            # TODO: API Call - Get user progress
            # Expected API: GET /api/v1/users/{user_id}/progress
            await update.message.reply_text(
                "📊 **Your Learning Progress**\n\n"
                "🔧 This feature is being developed.\n"
                "Soon you'll be able to view:\n\n"
                "📚 Completed lessons\n"
                "🎯 Quiz scores\n"
                "📈 Learning streaks\n"
                "⭐ Total points earned\n"
                "🏆 Rank progress"
            )

        elif selection == "🎯 Take Quiz":
            # TODO: API Call - Get available quizzes
            # Expected API: GET /api/v1/users/{user_id}/available-quizzes
            await update.message.reply_text(
                "🎯 **Take a Quiz**\n\n"
                "🔧 Quiz feature is being developed.\n"
                "Soon you'll be able to:\n\n"
                "📝 Take lesson quizzes\n"
                "🔄 Practice weak words\n"
                "🎲 Random word challenges\n"
                "⚡ Quick review sessions"
            )

        elif selection == "🏆 Leaderboard":
            # TODO: API Call - Get leaderboard data
            # Expected API: GET /api/v1/leaderboard?type=global_all_time&limit=10
            await update.message.reply_text(
                "🏆 **Leaderboard**\n\n"
                "🔧 Leaderboard is being developed.\n"
                "Soon you'll see:\n\n"
                "🌍 Global rankings\n"
                "👥 Group rankings\n"
                "📊 Daily top performers\n"
                "📈 Your rank progress"
            )

        elif selection == "🎖 My Badges":
            # TODO: API Call - Get user badges
            # Expected API: GET /api/v1/users/{user_id}/badges
            await update.message.reply_text(
                "🎖 **Your Badges & Achievements**\n\n"
                "🔧 Badge system is being developed.\n"
                "Soon you'll earn badges for:\n\n"
                "🥇 Daily first place\n"
                "💯 Perfect lesson scores\n"
                "📈 Rank improvements\n"
                "🎯 WeakList completions"
            )

        elif selection == "👤 Profile":
            # TODO: API Call - Get user profile
            # Expected API: GET /api/v1/users/{user_id}
            user = update.effective_user
            await update.message.reply_text(
                f"👤 **Your Profile**\n\n"
                f"📱 Telegram: @{user.username or 'Not set'}\n"
                f"🆔 ID: `{user.id}`\n"
                f"👤 Name: {user.full_name}\n\n"
                f"🔧 Profile management is being developed.\n"
                f"Soon you'll be able to update your information.",
                parse_mode='Markdown'
            )

        elif selection == "ℹ️ Help":
            await self.help_command(update, context)

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data.startswith("request_code_"):
            await self.verification_handler.handle_request_new_code(update, context)
        elif callback_data == "cancel_verification":
            await self.verification_handler.handle_cancel_verification(update, context)
        elif callback_data.startswith("lang_"):
            await self._handle_language_selection(update, context, callback_data)
        else:
            await query.edit_message_text(
                "🤔 Unknown action. Please try again or use /start."
            )

    async def _handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle language selection"""
        language_map = {
            "lang_uz": ("🇺🇿", "O'zbek"),
            "lang_en": ("🇺🇸", "English"),
            "lang_ru": ("🇷🇺", "Русский")
        }

        if callback_data in language_map:
            flag, lang_name = language_map[callback_data]

            # TODO: API Call - Update user language preference
            # Expected API: PATCH /api/v1/users/{user_id}
            # Body: {"language": callback_data.replace("lang_", "")}

            await update.callback_query.edit_message_text(
                f"{flag} Language set to {lang_name}\n\n"
                f"🔧 Multi-language support is being developed.\n"
                f"The interface will be available in your language soon!"
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again.\n\n"
                "If the problem persists, please contact support or try /start to restart."
            )

    def setup_handlers(self):
        """Set up all bot handlers"""
        app = self.application

        # Command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("status", self.status_command))

        # Message handlers
        app.add_handler(MessageHandler(filters.CONTACT, self.handle_phone_number))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))

        # Callback query handler
        app.add_handler(CallbackQueryHandler(self.handle_callback_query))

        # Error handler
        app.add_error_handler(self.error_handler)

    async def post_init(self, application: Application):
        """Post initialization hook"""
        logger.info("🤖 Language Learning Bot initialized successfully!")
        logger.info(f"🔗 API Base URL: {bot_settings.API_BASE_URL}")

        # Set bot commands menu
        commands = [
            ("start", "🚀 Start registration or login"),
            ("help", "ℹ️ Show help and instructions"),
            ("status", "📊 Check your account status")
        ]

        try:
            await application.bot.set_my_commands(commands)
            logger.info("✅ Bot commands menu set successfully")
        except Exception as e:
            logger.error(f"❌ Failed to set bot commands: {e}")

        # Log bot info
        try:
            bot_info = await application.bot.get_me()
            logger.info(f"🤖 Bot: @{bot_info.username} ({bot_info.first_name})")
        except Exception as e:
            logger.error(f"❌ Failed to get bot info: {e}")

    def run(self):
        """Run the bot"""
        # Get BOT_TOKEN from environment
        bot_token = os.getenv("BOT_TOKEN")

        if not bot_token:
            logger.error("❌ BOT_TOKEN not found in environment variables!")
            logger.error("Please add BOT_TOKEN to your .env file")
            sys.exit(1)

        logger.info(f"🔑 Bot token loaded from environment: {bot_token[:10]}...")

        # Create application
        self.application = (
            Application.builder()
            .token(bot_token)
            .post_init(self.post_init)
            .build()
        )

        # Setup handlers
        self.setup_handlers()

        # Get environment config
        config = BotConfig.get_config("development" if bot_settings.DEBUG_MODE else "production")

        try:
            if config["use_webhook"]:
                # Run with webhook (production)
                logger.info("🌐 Starting bot with webhook mode")
                logger.info(f"📍 Webhook URL: {bot_settings.WEBHOOK_URL}")

                self.application.run_webhook(
                    listen=bot_settings.WEBHOOK_HOST,
                    port=bot_settings.WEBHOOK_PORT,
                    url_path=bot_settings.WEBHOOK_PATH,
                    webhook_url=bot_settings.WEBHOOK_URL
                )
            else:
                # Run with polling (development)
                logger.info("🔄 Starting bot with polling mode")
                logger.info(f"⏱ Polling timeout: {config['polling_timeout']}s")

                self.application.run_polling(
                    timeout=config["polling_timeout"],
                    drop_pending_updates=True
                )

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            sys.exit(1)


def main():
    """Main function to run the bot"""
    logger.info("🚀 Starting Language Learning Bot...")

    try:
        bot = LanguageLearningBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()