import os
from typing import Optional
from pydantic_settings import BaseSettings


class TelegramBotSettings(BaseSettings):
    # Bot Configuration
    BOT_TOKEN: str
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
    def student_progress(student_id: int) -> str:
        return f"{APIEndpoints._base_url()}/students/{student_id}/progress"


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