"""Application configuration management."""

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    # Option 1: Full URL (기존 방식)
    database_url: str | None = None
    # Option 2: 분리된 설정 (팀 협업용)
    oracle_dsn: str | None = None  # 예: 192.168.0.1:1521/FREEPDB1
    oracle_user: str | None = None
    oracle_password: str | None = None

    # Application
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def get_database_url(self) -> str:
        """데이터베이스 연결 URL을 반환합니다.
        
        우선순위:
        1. DATABASE_URL이 설정되어 있으면 그대로 사용
        2. ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD가 모두 있으면 조합
        3. 그 외의 경우 ValueError 발생
        """
        if self.database_url:
            return self.database_url
        
        if self.oracle_dsn and self.oracle_user and self.oracle_password:
            # 비밀번호에 특수문자가 있을 수 있으므로 URL 인코딩
            encoded_password = quote_plus(self.oracle_password)
            encoded_user = quote_plus(self.oracle_user)
            return f"oracle+oracledb://{encoded_user}:{encoded_password}@{self.oracle_dsn}"
        
        raise ValueError(
            "데이터베이스 연결 정보가 설정되지 않았습니다. "
            "DATABASE_URL 또는 (ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD)를 설정하세요."
        )


# Global settings instance
settings = Settings()

