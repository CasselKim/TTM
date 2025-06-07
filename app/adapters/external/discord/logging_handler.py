import asyncio
import logging
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.adapters.external.discord.adapter import DiscordAdapter


class DiscordLoggingHandler(logging.Handler):
    """Discord로 에러 로그를 전송하는 로깅 핸들러"""

    def __init__(self, discord_adapter: "DiscordAdapter", level: int = logging.ERROR):
        """
        Discord 로깅 핸들러 초기화

        Args:
            discord_adapter: Discord 어댑터 인스턴스
            level: 로그 레벨 (기본값: ERROR)
        """
        super().__init__(level)
        self.discord_adapter = discord_adapter
        self._loop: asyncio.AbstractEventLoop | None = None

    def emit(self, record: logging.LogRecord) -> None:
        """로그 레코드를 Discord로 전송"""
        try:
            # 현재 이벤트 루프 가져오기
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # 이벤트 루프가 없으면 새로 생성하지 않고 무시
                return

            # 비동기로 Discord 전송
            asyncio.create_task(self._send_to_discord(record))
        except Exception:
            # 핸들러에서 예외 발생 시 무한루프 방지
            self.handleError(record)

    async def _send_to_discord(self, record: logging.LogRecord) -> None:
        """비동기로 Discord에 로그 전송"""
        try:
            # Discord 봇이 준비될 때까지 대기
            await self.discord_adapter.wait_until_ready()

            # 에러 메시지 포맷팅
            error_type = record.levelname
            error_message = record.getMessage()

            # 스택 트레이스가 있으면 추가
            details = None
            if record.exc_info:
                details = "".join(traceback.format_exception(*record.exc_info))
                # Discord 필드 길이 제한 (1024자)
                if len(details) > 1000:
                    details = details[:1000] + "..."

            # Discord로 에러 알림 전송
            await self.discord_adapter.send_error_notification(
                error_type=error_type,
                error_message=error_message,
                details=details,
            )
        except Exception as e:
            # Discord 전송 실패 시 로컬 로그에만 기록
            # 무한루프 방지를 위해 다른 핸들러 사용
            print(f"Discord 로그 전송 실패: {e}")
