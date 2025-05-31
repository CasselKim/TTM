"""로깅 설정"""

import logging
import os
from logging.handlers import RotatingFileHandler

# 로깅 상수
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5  # 백업 파일 개수
LOG_ENCODING = "utf-8"  # 로그 파일 인코딩


def setup_logging(service_name: str = "TTM") -> None:
    """로깅 설정 초기화"""

    # 로그 디렉토리 생성
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 로거 생성
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 중복 핸들러 방지
    if logger.hasHandlers():
        return

    # 포매터 생성
    formatter = logging.Formatter(
        f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s"
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (회전)
    file_handler = RotatingFileHandler(
        filename=f"{log_dir}/{service_name.lower()}.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding=LOG_ENCODING,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)

    logging.info(f"Logging configured with service: {service_name}")
