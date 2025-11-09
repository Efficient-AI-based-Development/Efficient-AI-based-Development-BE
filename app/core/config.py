"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str

    # Application
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # OpenAI / MCP
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


# Global settings instance
settings = Settings()

