"""
DCA 전용 스케줄러

DCA 알고리즘을 백그라운드에서 주기적으로 실행하는 스케줄러입니다.
"""

import asyncio
import logging
from app.domain.constants import DcaConstants

from app.application.usecase.dca_usecase import DcaUsecase
from app.domain.models.dca import DcaResult
from app.domain.enums import ActionTaken
from app.domain.models.status import MarketName

logger = logging.getLogger(__name__)


class DcaScheduler:
    """DCA 전용 백그라운드 스케줄러"""

    def __init__(
        self,
        dca_usecase: DcaUsecase,
        interval_seconds: float = DcaConstants.DEFAULT_SCHEDULER_INTERVAL_SECONDS,
        enabled: bool = True,
    ) -> None:
        self.dca_usecase = dca_usecase
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """스케줄러 시작"""
        if self._running:
            logger.warning("DCA scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_dca_loop())
        logger.info(f"DCA scheduler started: {self.interval_seconds}s interval")

    async def stop(self) -> None:
        """스케줄러 중지"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DCA scheduler stopped")

    async def _process_market(self, market: MarketName) -> None:
        """단일 시장에 대한 DCA 사이클 처리"""
        try:
            result = await self.dca_usecase.execute_dca_cycle(market)
            await self._handle_cycle_result(market, result)
        except Exception as e:
            logger.error(
                f"Unexpected error executing DCA cycle for {market}: {e}",
                exc_info=True,
            )

    async def _run_dca_loop(self) -> None:
        """DCA 실행 루프"""
        logger.info("DCA algorithm loop started")
        while self._running and self.enabled:
            try:
                active_markets = await self.dca_usecase.get_active_markets()
                if not active_markets:
                    logger.info("No active DCA markets")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                for market in active_markets:
                    await self._process_market(market)
            except Exception as e:
                logger.error(f"Error in DCA loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)
        logger.info("DCA algorithm loop ended")

    async def _handle_cycle_result(self, market: MarketName, result: DcaResult) -> None:
        """사이클 실행 결과 처리"""
        if result.success:
            if result.action_taken != ActionTaken.HOLD:
                logger.info(
                    f"{market} DCA 실행: {result.action_taken.value} - {result.message}"
                )
            else:
                logger.debug(f"{market}: {result.message}")
        else:
            logger.error(f"{market} DCA 실행 실패: {result.message}")

    async def get_status(self) -> dict[str, bool | float | str | list[MarketName]]:
        """스케줄러 상태 반환"""
        active_markets = []
        if self._running:
            active_markets = await self.dca_usecase.get_active_markets()

        return {
            "running": self._running,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "active_markets": active_markets,
        }
