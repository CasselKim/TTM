import logging
import traceback
from typing import TYPE_CHECKING, Callable, Awaitable, Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from app.adapters.external.discord.adapter import DiscordAdapter

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """전역 예외 처리 미들웨어"""

    def __init__(self, app: Any, discord_adapter: "DiscordAdapter") -> None:
        """
        예외 처리 미들웨어 초기화

        Args:
            app: FastAPI 애플리케이션
            discord_adapter: Discord 어댑터
        """
        super().__init__(app)
        self.discord_adapter = discord_adapter

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """요청 처리 및 예외 캐치"""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 에러 로깅
            logger.exception(f"처리되지 않은 예외 발생: {e}")

            # Discord 알림 전송
            try:
                await self.discord_adapter.send_error_notification(
                    error_type="HTTP Exception",
                    error_message=f"[{request.method}] {request.url}: {str(e)}",
                    details=traceback.format_exc(),
                )
            except Exception as discord_error:
                logger.error(f"Discord 에러 알림 전송 실패: {discord_error}")

            # 클라이언트에게 일반적인 에러 응답 반환
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "서버에서 오류가 발생했습니다. 관리자에게 문의해주세요.",
                },
            )
