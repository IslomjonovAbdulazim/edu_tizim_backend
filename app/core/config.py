from __future__ import annotations
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    PROJECT_NAME: str = "LLC Management API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # FastAPI docs
    DOCS_URL: str | None = "/docs"
    REDOC_URL: str | None = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_ALLOW_METHODS: List[str] = ["*"]

    # Example database URL (if you want to expose it here)
    DATABASE_URL: str | None = None


settings = Settings()
