import asyncio
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.adapters.primary.api.routes import account, order, ticker
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
        },
        "discord": {
            "bot_token": os.getenv("DISCORD_BOT_TOKEN", ""),
            "channel_id": int(os.getenv("DISCORD_CHANNEL_ID", "0")),
        },
    }
)

# FastAPI 앱에 컨테이너 연결
app.container = container  # type: ignore

# 라우터 등록
app.include_router(account.router)
app.include_router(ticker.router)
app.include_router(order.router)

# 컨테이너 와이어링
container.wire(modules=[account, ticker, order])


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 Discord Bot 실행"""
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        discord_adapter = container.discord_adapter()

        # Discord Bot 커맨드 등록
        from app.adapters.secondary.discord.bot_commands import setup_bot_commands

        setup_bot_commands(
            bot_adapter=discord_adapter,
            account_usecase=container.account_usecase(),
            ticker_usecase=container.ticker_usecase(),
        )

        # Discord Bot을 백그라운드 태스크로 실행
        asyncio.create_task(discord_adapter.start())
        # 봇이 준비될 때까지 대기
        await discord_adapter.wait_until_ready()

        # 시작 알림 전송
        await discord_adapter.send_info_notification(
            title="봇 시작",
            message="TTM Trading Bot이 성공적으로 시작되었습니다.",
            fields=[
                ("환경", os.getenv("ENV", "Production"), True),
                ("로그 레벨", os.getenv("LOG_LEVEL", "INFO"), True),
            ],
        )


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 Discord Bot 정리"""
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        discord_adapter = container.discord_adapter()
        await discord_adapter.close()
