"""
거래 알고리즘 스케줄러

FastAPI 앱과 함께 실행되는 백그라운드 태스크로 주기적으로 거래 알고리즘을 실행합니다.
"""

import asyncio
import logging
from typing import Any

from app.application.usecase.trading_usecase import AlgorithmType, TradingUsecase
from app.domain.models.account import Currency
from app.domain.models.enums import TradingMode

logger = logging.getLogger(__name__)


class TradingScheduler:
    """거래 알고리즘 백그라운드 스케줄러"""

    def __init__(
        self,
        trading_usecase: TradingUsecase,
        interval_seconds: float = 10.0,  # 기본 10초 간격
        enabled: bool = True,
        target_currency: Currency = Currency.BTC,
        mode: TradingMode = TradingMode.SIMULATION,
    ) -> None:
        self.trading_usecase = trading_usecase
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.target_currency = target_currency
        self.mode = mode
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """스케줄러 시작"""
        if self._running:
            logger.warning("Trading scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_trading_loop())
        logger.info(
            f"Trading scheduler started: {self.interval_seconds}s interval, "
            f"{self.target_currency.value} {self.mode.value} mode"
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
        logger.info("Trading scheduler stopped")

    async def _run_trading_loop(self) -> None:
        """거래 알고리즘 실행 루프"""
        logger.info("Trading algorithm loop started")

        while self._running and self.enabled:
            try:
                # Simple 알고리즘으로 거래 실행
                result = await self.trading_usecase.execute_trading_algorithm(
                    target_currency=self.target_currency,
                    mode=self.mode,
                    algorithm_type=AlgorithmType.SIMPLE,
                )

                # 결과 로깅 (HOLD 신호가 아닌 경우에만 상세 로깅)
                if result.success:
                    if result.order_uuid:
                        # 실제 거래 실행됨
                        logger.info(
                            f"[{self.mode.value.upper()}] Trading executed: {result.message}"
                        )
                        if result.executed_amount:
                            logger.info(
                                f"[{self.mode.value.upper()}] Amount: {result.executed_amount:,.0f} KRW"
                            )
                    elif "HOLD" not in result.message:
                        # HOLD가 아닌 다른 성공 메시지
                        logger.info(f"[{self.mode.value.upper()}] {result.message}")
                    # HOLD 신호는 디버그 레벨로만 로깅
                    else:
                        logger.debug(f"[{self.mode.value.upper()}] {result.message}")
                else:
                    # 거래 실패
                    logger.error(
                        f"[{self.mode.value.upper()}] Trading failed: {result.message}"
                    )

            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)

            # 다음 실행까지 대기
            await asyncio.sleep(self.interval_seconds)

        logger.info("Trading algorithm loop ended")
