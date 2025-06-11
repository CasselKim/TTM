import logging
import traceback
from typing import TYPE_CHECKING, Callable, Awaitable, Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from common.utils.timezone import now_kst

from common.discord.models import Embed, EmbedField

from common.discord.bot import DiscordBot

if TYPE_CHECKING:
    from common.discord.bot import DiscordBot

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """전역 예외 처리 미들웨어"""

    def __init__(self, app: Any, discord_bot: "DiscordBot") -> None:
        """
        예외 처리 미들웨어 초기화

        Args:
            app: FastAPI 애플리케이션
            discord_bot: Discord 봇
        """
        super().__init__(app)
        self.discord_bot = discord_bot

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """요청 처리 및 예외 캐치"""
        try:
            return await call_next(request)
        except Exception as e:
            # 에러 로깅
            logger.exception(f"처리되지 않은 예외 발생: {e}")

            # Discord 알림 전송
            try:
                details = traceback.format_exc()
                embed = Embed(
                    title="🚨 HTTP Exception",
                    description=f"**[{request.method}]** `{request.url}`",
                    color=0xFF0000,
                    timestamp=now_kst(),
                    fields=[
                        EmbedField(name="Error", value=str(e), inline=False),
                        EmbedField(
                            name="Traceback",
                            value=f"```py\n{details[:900]}...\n```",  # 길이 제한
                            inline=False,
                        ),
                    ],
                )
                await self.discord_bot.send_embed(embed, channel_type="alert")
            except Exception as discord_error:
                logger.error(f"Discord 에러 알림 전송 실패: {discord_error}")

            # 클라이언트에게 일반적인 에러 응답 반환
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred.",
                },
            )
