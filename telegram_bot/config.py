import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TelegramBotSettings(BaseSettings):
    # Bot Configuration - Load from environment
    BOT_TOKEN: Optional[str] = None  # Will be loaded from .env
    BOT_USERNAME: Optional[str] = None

    # Webhook Configuration (for production)
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: Optional[str] = "/webhook"
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8443

    # API Configuration
    API_BASE_URL: str = "http://localhost:8000"
    API_VERSION: str = "v1"

    # Verification Settings
    VERIFICATION_CODE_LENGTH: int = 6
    VERIFICATION_CODE_EXPIRES_MINUTES: int = 10
    MAX_VERIFICATION_ATTEMPTS: int = 3

    # Rate Limiting
    MAX_REQUESTS_PER_HOUR: int = 5
    MAX_REQUESTS_PER_DAY: int = 10

    # Message Templates
    WELCOME_MESSAGE: str = (
        "🎓 Welcome to Language Learning Center!\n\n"
        "To get started, please share your phone number by clicking the button below."
    )

    VERIFICATION_MESSAGE: str = (
        "📱 Your verification code is: `{code}`\n\n"
        "This code will expire in {minutes} minutes.\n"
        "Please enter this code to complete your registration."
    )

    SUCCESS_LOGIN_MESSAGE: str = (
        "✅ Successfully logged in!\n\n"
        "Welcome back, {name}! You can now access your learning dashboard."
    )

    # Error Messages
    ERROR_INVALID_CODE: str = "❌ Invalid verification code. Please try again."
    ERROR_CODE_EXPIRED: str = "⏰ Verification code has expired. Please request a new one."
    ERROR_MAX_ATTEMPTS: str = "🚫 Maximum verification attempts reached. Please request a new code."
    ERROR_RATE_LIMITED: str = "⚠️ Too many requests. Please wait before requesting another code."
    ERROR_USER_NOT_FOUND: str = "👤 User not found. Please contact your learning center administrator."
    ERROR_GENERAL: str = "❌ Something went wrong. Please try again later."

    # Button Texts
    BUTTON_SHARE_PHONE: str = "📱 Share Phone Number"
    BUTTON_REQUEST_CODE: str = "🔄 Request New Code"
    BUTTON_CANCEL: str = "❌ Cancel"
    BUTTON_HELP: str = "ℹ️ Help"

    # Development/Testing
    DEBUG_MODE: bool = False
    LOG_LEVEL: str = "INFO"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override BOT_TOKEN with environment variable if not provided
        if not self.BOT_TOKEN:
            self.BOT_TOKEN = os.getenv("BOT_TOKEN")

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_prefix = "TELEGRAM_"


# Bot settings instance
bot_settings = TelegramBotSettings()


# API endpoints
class APIEndpoints:
    @staticmethod
    def _base_url() -> str:
        return f"{bot_settings.API_BASE_URL}/api/{bot_settings.API_VERSION}"

    @staticmethod
    def request_verification_code() -> str:
        return f"{APIEndpoints._base_url()}/auth/request-verification-code"

    @staticmethod
    def verify_code() -> str:
        return f"{APIEndpoints._base_url()}/auth/verify-code"

    @staticmethod
    def user_profile(user_id: int) -> str:
        return f"{APIEndpoints._base_url()}/users/{user_id}"

    @staticmethod
    def user_by_telegram_id(telegram_id: int) -> str:
        return f"{APIEndpoints._base_url()}/users/by-telegram/{telegram_id}"

    @staticmethod
    def student_progress(student_id: int) -> str:
        return f"{APIEndpoints._base_url()}/students/{student_id}/progress"

    @staticmethod
    def leaderboard(leaderboard_type: str = "global_all_time", limit: int = 10) -> str:
        return f"{APIEndpoints._base_url()}/leaderboard?type={leaderboard_type}&limit={limit}"

    @staticmethod
    def user_badges(user_id: int) -> str:
        return f"{APIEndpoints._base_url()}/users/{user_id}/badges"

    @staticmethod
    def available_quizzes(user_id: int) -> str:
        return f"{APIEndpoints._base_url()}/users/{user_id}/available-quizzes"

    @staticmethod
    def verification_status(telegram_id: int, phone_number: str) -> str:
        return f"{APIEndpoints._base_url()}/auth/verification-status?telegram_id={telegram_id}&phone_number={phone_number}"

    @staticmethod
    def rate_limit_status(telegram_id: int) -> str:
        return f"{APIEndpoints._base_url()}/auth/rate-limit-status?telegram_id={telegram_id}"


# Telegram bot configuration for different environments
class BotConfig:
    DEVELOPMENT = {
        "use_webhook": False,
        "polling_timeout": 10,
        "log_level": "DEBUG"
    }

    PRODUCTION = {
        "use_webhook": True,
        "polling_timeout": 0,
        "log_level": "INFO"
    }

    @staticmethod
    def get_config(environment: str = "development") -> dict:
        if environment.lower() == "production":
            return BotConfig.PRODUCTION
        return BotConfig.DEVELOPMENT


# Bot status messages
class BotMessages:
    """Centralized bot messages for consistency"""

    STARTUP_MESSAGES = {
        "bot_starting": "🚀 Starting Language Learning Bot...",
        "bot_initialized": "🤖 Bot initialized successfully!",
        "token_loaded": "🔑 Bot token loaded from environment",
        "webhook_mode": "🌐 Starting bot with webhook mode",
        "polling_mode": "🔄 Starting bot with polling mode",
        "commands_set": "✅ Bot commands menu set successfully"
    }

    ERROR_MESSAGES = {
        "no_token": "❌ BOT_TOKEN not found in environment variables!",
        "token_help": "Please add BOT_TOKEN to your .env file",
        "startup_failed": "❌ Failed to start bot",
        "commands_failed": "❌ Failed to set bot commands",
        "critical_error": "💥 Critical error"
    }

    FEATURE_DEVELOPMENT = {
        "progress": "🔧 Progress tracking is being developed.",
        "quiz": "🔧 Quiz feature is being developed.",
        "leaderboard": "🔧 Leaderboard is being developed.",
        "badges": "🔧 Badge system is being developed.",
        "profile": "🔧 Profile management is being developed.",
        "multilang": "🔧 Multi-language support is being developed."
    }


# Validation functions
def validate_bot_token(token: str) -> bool:
    """Validate Telegram bot token format"""
    import re
    if not token:
        return False
    # Telegram bot token format: number:alphanumeric_string
    pattern = r'^\d+:[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, token))


def get_bot_info() -> dict:
    """Get bot configuration info for logging"""
    return {
        "api_base": bot_settings.API_BASE_URL,
        "debug_mode": bot_settings.DEBUG_MODE,
        "log_level": bot_settings.LOG_LEVEL,
        "verification_expires": bot_settings.VERIFICATION_CODE_EXPIRES_MINUTES,
        "max_attempts": bot_settings.MAX_VERIFICATION_ATTEMPTS,
        "rate_limit_hour": bot_settings.MAX_REQUESTS_PER_HOUR,
        "rate_limit_day": bot_settings.MAX_REQUESTS_PER_DAY
    }


# Export commonly used items
__all__ = [
    'bot_settings',
    'APIEndpoints',
    'BotConfig',
    'BotMessages',
    'validate_bot_token',
    'get_bot_info'
]