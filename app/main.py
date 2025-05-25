import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.adapters.primary.api.routes import account, ticker
from app.container import Container
from common.logging import setup_logging

# 환경 변수 로드
load_dotenv()

# 로깅 초기화
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/app.log"),
)

app = FastAPI()

# 컨테이너 초기화
container = Container()
container.config.from_dict(
    {
        "upbit": {
            "access_key": os.getenv("UPBIT_ACCESS_KEY"),
            "secret_key": os.getenv("UPBIT_SECRET_KEY"),
        }
    }
)

# FastAPI 앱에 컨테이너 연결
app.container = container  # type: ignore

# 라우터 등록
app.include_router(account.router)
app.include_router(ticker.router)

# 컨테이너 와이어링
container.wire(modules=[account, ticker])
