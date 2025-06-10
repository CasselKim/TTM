import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.adapters.internal.dca_scheduler import (
    DcaScheduler,
)
from app.container import Container
from common.logging import setup_logging
from common.discord.handlers import (
    DiscordDebugLoggingHandler,
    DiscordLoggingHandler,
)
from common.discord.middleware import ExceptionHandlingMiddleware

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
    dca_scheduler = None
    discord_bot = container.discord_bot()

    # Startup
    if discord_bot.bot_token:
        # 봇 실행
        logging.info("Discord 봇을 시작합니다.")
        bot_task = asyncio.create_task(discord_bot.start_bot())

        try:
            # 봇 로그인이 시작될 때까지 잠시 대기
            await asyncio.sleep(0.1)

            # 봇이 준비될 때까지 최대 60초 대기
            logging.info("봇이 준비될 때까지 최대 60초 대기")
            await asyncio.wait_for(discord_bot.wait_until_ready(), timeout=60.0)
            logging.info("봇이 준비되었습니다.")
        except asyncio.TimeoutError:
            logging.critical(
                "Discord 봇이 60초 내에 준비되지 않았습니다. Task를 취소합니다."
            )
            bot_task.cancel()
            raise  # Lifespan을 중단하고 애플리케이션 시작 실패 처리

        # 커맨드 어댑터 가져오기 및 커맨드 설정
        logging.info("커맨드 어댑터 가져오기 및 커맨드 설정")
        command_adapter = container.command_adapter()
        logging.info("커맨드 어댑터 설정 완료")
        await discord_bot.setup_commands(command_adapter)
        logging.info("모든 커맨드 설정 완료")

        # 봇 태스크가 예외와 함께 종료되었는지 확인
        if bot_task.done():
            logging.info("봇 태스크가 완료되었습니다.")
            if exc := bot_task.exception():
                logging.critical(f"Discord 봇 Task가 예외와 함께 종료되었습니다: {exc}")
                raise exc
            logging.info(
                "Discord 봇 Task가 정상적으로 완료되었습니다 (예상치 못한 동작)."
            )

        # 로깅 핸들러 추가
        logging.getLogger().addHandler(DiscordLoggingHandler(discord_bot))
        logging.getLogger().addHandler(DiscordDebugLoggingHandler(discord_bot))

        # 시작 알림
        notification_adapter = container.notification_adapter()
        await notification_adapter.send_info_notification(
            title="TTM Bot 시작", message="TTM 자동매매 봇이 시작되었습니다."
        )

    # DCA 스케줄러 시작
    if os.getenv("ENABLE_DCA_SCHEDULER", "true").lower() == "true":
        dca_usecase = container.dca_usecase()

        dca_scheduler = DcaScheduler(
            dca_usecase=dca_usecase,
            interval_seconds=float(os.getenv("DCA_INTERVAL_SECONDS", "30")),
            enabled=True,
        )
        await dca_scheduler.start()

    yield

    # Shutdown
    # DCA 스케줄러 종료
    if dca_scheduler:
        await dca_scheduler.stop()

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
