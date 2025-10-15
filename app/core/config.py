"""
Configuration management for AI News Agent
"""

import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Project info
    PROJECT_NAME: str = "AI News Agent"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered news agent that delivers daily summaries via WhatsApp"
    API_V1_STR: str = "/api/v1"

    # Server settings
    SERVER_NAME: str = "localhost"
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"
    OLLAMA_MAX_TOKENS: int = 500
    OLLAMA_TEMPERATURE: float = 0.3

    # Twilio settings (Optional - for WhatsApp delivery)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    WHATSAPP_RECIPIENT_NUMBER: Optional[str] = None

    # RSS Feed settings
    RSS_FETCH_TIMEOUT: int = 30
    RSS_MAX_ARTICLES_PER_FEED: int = 10
    RSS_CACHE_TTL: int = 3600  # 1 hour

    # News categories and their RSS feeds
    NEWS_CATEGORIES: dict = {
        "technology": [
            "https://rss.cnn.com/rss/edition_technology.rss",
            "https://feeds.feedburner.com/TechCrunch",
            "https://www.theverge.com/rss/index.xml",
        ],
        "business": [
            "https://rss.cnn.com/rss/edition_business.rss",
            "https://feeds.feedburner.com/businessinsider",
            "https://www.ft.com/rss/home/uk",
        ],
        "science": [
            "https://rss.cnn.com/rss/edition_space.rss",
            "https://www.sciencenews.org/feed",
            "https://www.nature.com/nature.rss",
        ],
        "world": [
            "https://rss.cnn.com/rss/edition_world.rss",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
    }

    # Scheduling settings (IST - Asia/Calcutta timezone)
    MORNING_DELIVERY_HOUR: int = 8  # 8 AM IST
    EVENING_DELIVERY_HOUR: int = 18  # 6 PM IST
    DELIVERY_TIMEZONE: str = "Asia/Calcutta"

    # Message settings
    MAX_SUMMARY_LENGTH: int = 200
    MAX_ARTICLES_PER_MESSAGE: int = 5
    MESSAGE_LANGUAGE: str = "english"

    # Database settings (optional)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = "redis://localhost:6379"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Monitoring
    SENTRY_DSN: Optional[str] = None

    # Development settings
    DEBUG: bool = False


# Create global settings instance
settings = Settings()