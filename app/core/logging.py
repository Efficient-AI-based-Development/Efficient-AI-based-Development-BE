"""Logging configuration."""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging.

    로깅 설정:
    - Console 출력: 모든 로그를 표준 출력으로 전송
    - 로그 레벨: settings.log_level에서 설정
    - 포맷: 타임스탬프, 로그 레벨, 모듈명, 메시지
    - UTF-8 인코딩 사용
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # SQLAlchemy 쿼리 로깅 (디버그 모드에서만)
    if settings.debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
