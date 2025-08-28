import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext import CallbackQueryHandler

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
        """Handle text messages (verification codes, etc.)"""
        await self.verification_handler.handle_text_message(update, context)

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("request_code_"):
            await self.verification_handler.handle_request_new_code(update, context)
        elif query.data == "cancel_verification":
            await self.verification_handler.handle_cancel_verification(update, context)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
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
        logger.info("Bot initialized successfully")

        # Set bot commands
        commands = [
            ("start", "Start registration process"),
            ("help", "Show help information"),
            ("status", "Check account status")
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        """Run the bot"""
        if not bot_settings.BOT_TOKEN:
            logger.error("BOT_TOKEN not provided")
            sys.exit(1)

        # Create application
        self.application = (
            Application.builder()
            .token(bot_settings.BOT_TOKEN)
            .post_init(self.post_init)
            .build()
        )

        # Setup handlers
        self.setup_handlers()

        # Get environment config
        config = BotConfig.get_config("development" if bot_settings.DEBUG_MODE else "production")

        if config["use_webhook"]:
            # Run with webhook (production)
            logger.info("Starting bot with webhook")
            self.application.run_webhook(
                listen=bot_settings.WEBHOOK_HOST,
                port=bot_settings.WEBHOOK_PORT,
                url_path=bot_settings.WEBHOOK_PATH,
                webhook_url=bot_settings.WEBHOOK_URL
            )
        else:
            # Run with polling (development)
            logger.info("Starting bot with polling")
            self.application.run_polling(
                timeout=config["polling_timeout"],
                drop_pending_updates=True
            )


def main():
    """Main function to run the bot"""
    bot = LanguageLearningBot()
    bot.run()


if __name__ == '__main__':
    main()