import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.container import Container
from common.logging import setup_logging

# 환경 변수 로드
load_dotenv()

# 로깅 초기화
setup_logging(service_name="TTM")

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 lifespan 관리"""
    bot_task = None

    # Startup
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        discord_adapter = container.discord_adapter()

        # Discord Bot 커맨드 등록
        from app.adapters.internal.websocket.discord_bot import setup_bot_commands

        setup_bot_commands(
            bot_adapter=discord_adapter,
            account_usecase=container.account_usecase(),
            ticker_usecase=container.ticker_usecase(),
            order_usecase=container.order_usecase(),
        )

        # Discord Bot을 백그라운드 태스크로 실행
        bot_task = asyncio.create_task(discord_adapter.start())
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

    yield

    # Shutdown
    if discord_token:
        discord_adapter = container.discord_adapter()
        await discord_adapter.close()

        # 백그라운드 태스크 정리
        if bot_task and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)

# FastAPI 앱에 컨테이너 연결
app.container = container  # type: ignore


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """서비스 상태 확인을 위한 health check endpoint"""
    return {"status": "healthy", "service": "TTM Trading Bot"}
