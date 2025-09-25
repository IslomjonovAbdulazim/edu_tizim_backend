from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App Configuration
    PROJECT_NAME: str = "Language Learning Center API"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Super Admin Credentials
    SUPER_ADMIN_EMAIL: str
    SUPER_ADMIN_PASSWORD: str
    
    # Storage Configuration
    STORAGE_PATH: str = "/tmp/persistent_storage"
    
    # Eskiz SMS Configuration
    ESKIZ_URL: str
    ESKIZ_EMAIL: str
    ESKIZ_PASSWORD: str
    ESKIZ_WEBHOOK_URL: str
    ESKIZ_FROM: str = "4546"
    TEST_VERIFICATION_CODE: str = "1234"
    
    # Narakeet TTS Configuration
    NARAKEET: str
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()