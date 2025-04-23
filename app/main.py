import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.infrastructure.container import Container
from app.presentation.api.routes import account

# 환경 변수 로드
load_dotenv()

app = FastAPI()

# 컨테이너 초기화
container = Container()
container.config.from_dict({
    "upbit": {
        "access_key": os.getenv("UPBIT_ACCESS_KEY"),
        "secret_key": os.getenv("UPBIT_SECRET_KEY")
    }
})

# FastAPI 앱에 컨테이너 연결
app.container = container

# 라우터 등록
app.include_router(account.router)

# 컨테이너 와이어링
container.wire(modules=[account]) 