import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.adapters.internal.background.infinite_buying_scheduler import (
    InfiniteBuyingScheduler,
)
from app.container import Container
from common.logging import setup_logging
from resources.discord.handlers import (
    DiscordDebugLoggingHandler,
    DiscordLoggingHandler,
)
from resources.discord.middleware import ExceptionHandlingMiddleware

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
            "channel_id": int(os.getenv("DISCORD_HISTORY_CHANNEL_ID", "0")),
            "alert_channel_id": int(
                os.getenv(
                    "DISCORD_ALERT_CHANNEL_ID",
                    os.getenv("DISCORD_HISTORY_CHANNEL_ID", "0"),
                )
            ),
            "log_channel_id": int(
                os.getenv(
                    "DISCORD_LOG_CHANNEL_ID",
                    os.getenv("DISCORD_HISTORY_CHANNEL_ID", "0"),
                )
            ),
            "command_prefix": "!",  # Add command_prefix if it's used in bot
        },
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bot_task = None
    infinite_buying_scheduler = None
    discord_bot = container.discord_bot()

    # Startup
    if discord_bot.bot_token:
        # 커맨드 어댑터 가져오기 및 커맨드 설정
        command_adapter = container.command_adapter()
        await command_adapter.setup_all_commands()

        # 봇 실행
        bot_task = asyncio.create_task(discord_bot.start_bot())
        await discord_bot.wait_until_ready()

        # 로깅 핸들러 추가
        logging.getLogger().addHandler(DiscordLoggingHandler(discord_bot))
        logging.getLogger().addHandler(DiscordDebugLoggingHandler(discord_bot))

        # 시작 알림
        notification_adapter = container.notification_adapter()
        await notification_adapter.send_info_notification(
            title="TTM Bot 시작", message="TTM 자동매매 봇이 시작되었습니다."
        )

    # 무한매수법 스케줄러 시작
    if os.getenv("ENABLE_INFINITE_BUYING_SCHEDULER", "true").lower() == "true":
        infinite_buying_usecase = container.infinite_buying_usecase()

        infinite_buying_scheduler = InfiniteBuyingScheduler(
            infinite_buying_usecase=infinite_buying_usecase,
            interval_seconds=float(os.getenv("INFINITE_BUYING_INTERVAL_SECONDS", "30")),
            enabled=True,
        )
        await infinite_buying_scheduler.start()

    yield

    # Shutdown
    # 무한매수법 스케줄러 종료
    if infinite_buying_scheduler:
        await infinite_buying_scheduler.stop()

    if discord_bot.bot_token:
        # 종료 알림
        notification_adapter = container.notification_adapter()
        await notification_adapter.send_info_notification(
            title="TTM Bot 종료", message="TTM 자동매매 봇이 종료되었습니다."
        )
        await discord_bot.close()

    if bot_task and not bot_task.done():
        bot_task.cancel()


app = FastAPI(lifespan=lifespan)

# FastAPI 앱에 컨테이너 연결
app.container = container  # type: ignore

# 예외 처리 미들웨어 추가
if container.discord_bot().bot_token:
    app.add_middleware(ExceptionHandlingMiddleware, discord_bot=container.discord_bot())


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """서비스 상태 확인을 위한 health check endpoint"""
    return {"status": "healthy", "service": "TTM Trading Bot"}
