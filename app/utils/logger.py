# app/utils/logger.py

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")


def setup_logger() -> None:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        # 이미 설정된 경우 중복 설정 방지
        return

    root_logger.setLevel(logging.INFO)

    # 콘솔 출력 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # 파일 출력 핸들러
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# 모듈 import 시점에 한 번만 로깅 설정 적용
setup_logger()
