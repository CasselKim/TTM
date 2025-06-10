"""
무한매수법 전용 스케줄러

무한매수법 알고리즘을 백그라운드에서 주기적으로 실행하는 스케줄러입니다.
"""

import asyncio
import logging

from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.domain.models.infinite_buying import InfiniteBuyingResult
from app.domain.types import ActionTaken, MarketName

logger = logging.getLogger(__name__)


class InfiniteBuyingScheduler:
    """무한매수법 전용 백그라운드 스케줄러"""

    def __init__(
        self,
        infinite_buying_usecase: InfiniteBuyingUsecase,
        interval_seconds: float = 30.0,
        enabled: bool = True,
    ) -> None:
        self.infinite_buying_usecase = infinite_buying_usecase
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """스케줄러 시작"""
        if self._running:
            logger.warning("Infinite buying scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_infinite_buying_loop())
        logger.info(
            f"Infinite buying scheduler started: {self.interval_seconds}s interval"
        )

    async def stop(self) -> None:
        """스케줄러 중지"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Infinite buying scheduler stopped")

    async def _process_market(self, market: MarketName) -> None:
        """단일 시장에 대한 무한매수법 사이클 처리"""
        try:
            result = await self.infinite_buying_usecase.execute_infinite_buying_cycle(
                market
            )
            await self._handle_cycle_result(market, result)
        except Exception as e:
            logger.error(
                f"Unexpected error executing infinite buying cycle for {market}: {e}",
                exc_info=True,
            )

    async def _run_infinite_buying_loop(self) -> None:
        """무한매수법 실행 루프"""
        logger.info("Infinite buying algorithm loop started")
        while self._running and self.enabled:
            try:
                active_markets = await self.infinite_buying_usecase.get_active_markets()
                if not active_markets:
                    logger.info("No active infinite buying markets")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                for market in active_markets:
                    await self._process_market(market)
            except Exception as e:
                logger.error(f"Error in infinite buying loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)
        logger.info("Infinite buying algorithm loop ended")

    async def _handle_cycle_result(
        self, market: MarketName, result: InfiniteBuyingResult
    ) -> None:
        """사이클 실행 결과 처리"""
        if result.success:
            if result.action_taken != ActionTaken.HOLD:
                logger.info(
                    f"{market} 무한매수법 실행: {result.action_taken.value} - {result.message}"
                )
            else:
                logger.debug(f"{market}: {result.message}")
        else:
            logger.error(f"{market} 무한매수법 실행 실패: {result.message}")

    async def get_status(self) -> dict[str, bool | float | str | list[MarketName]]:
        """스케줄러 상태 반환"""
        active_markets = []
        if self._running:
            active_markets = await self.infinite_buying_usecase.get_active_markets()

        return {
            "running": self._running,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "active_markets": active_markets,
        }
