from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Language Learning Center API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Settings
    DATABASE_URL: str

    # Super Admin Settings
    SUPER_ADMIN_EMAIL: str = "superadmin@system.com"
    SUPER_ADMIN_PASSWORD: str

    # File Upload Settings
    UPLOAD_DIR: str = "storage"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".gif", ".mp3", ".mp4", ".wav", ".pdf"]

    # Badge System Settings
    POINTS_PER_WORD: int = 10
    POINTS_PER_LESSON: int = 50
    POINTS_PER_MODULE: int = 200

    # Weeklist Algorithm Settings
    MAX_WEEKLY_WORDS: int = 50
    DIFFICULTY_MULTIPLIER: float = 1.2

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()