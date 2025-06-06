"""
무한매수법 전용 스케줄러

무한매수법 알고리즘을 백그라운드에서 주기적으로 실행하는 스케줄러입니다.
"""

import asyncio
import logging

from app.adapters.external.discord.adapter import DiscordAdapter
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.domain.models.infinite_buying import InfiniteBuyingResult
from app.domain.types import ActionTaken, MarketName

logger = logging.getLogger(__name__)


class InfiniteBuyingScheduler:
    """무한매수법 전용 백그라운드 스케줄러"""

    def __init__(
        self,
        infinite_buying_usecase: InfiniteBuyingUsecase,
        interval_seconds: float = 30.0,  # 기본 30초 간격 (무한매수법은 좀 더 긴 간격)
        enabled: bool = True,
        discord_adapter: DiscordAdapter | None = None,  # 알림용 Discord 어댑터
    ) -> None:
        self.infinite_buying_usecase = infinite_buying_usecase
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.discord_adapter = discord_adapter
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
            # 결과 처리 및 로깅
            await self._handle_cycle_result(market, result)

        except ConnectionError as e:
            logger.error(f"Network connection error for {market}: {e}", exc_info=True)
            # Discord 네트워크 에러 알림
            if self.discord_adapter:
                await self._send_error_notification(market, f"네트워크 연결 오류: {e}")

        except RuntimeError as e:
            logger.error(
                f"Runtime error executing infinite buying cycle for {market}: {e}",
                exc_info=True,
            )
            # Discord 런타임 에러 알림
            if self.discord_adapter:
                await self._send_error_notification(market, f"런타임 오류: {e}")

        except Exception as e:
            logger.error(
                f"Unexpected error executing infinite buying cycle for {market}: {e}",
                exc_info=True,
            )
            # Discord 일반 에러 알림
            if self.discord_adapter:
                await self._send_error_notification(market, f"시스템 오류: {e}")

    async def _run_infinite_buying_loop(self) -> None:
        """무한매수법 실행 루프"""
        logger.info("Infinite buying algorithm loop started")

        while self._running and self.enabled:
            try:
                # 현재 활성화된 모든 시장에 대해 실행
                active_markets = await self.infinite_buying_usecase.get_active_markets()

                if not active_markets:
                    # 활성화된 시장이 없으면 대기
                    logger.debug("No active infinite buying markets")
                    await asyncio.sleep(self.interval_seconds)
                    continue

                # 각 시장별로 무한매수법 사이클 실행
                for market in active_markets:
                    await self._process_market(market)

            except Exception as e:
                logger.error(f"Error in infinite buying loop: {e}", exc_info=True)

            # 다음 실행까지 대기
            await asyncio.sleep(self.interval_seconds)

        logger.info("Infinite buying algorithm loop ended")

    async def _handle_cycle_result(
        self, market: MarketName, result: InfiniteBuyingResult
    ) -> None:
        """사이클 실행 결과 처리"""
        try:
            if result.success:
                action = result.action_taken

                if action == ActionTaken.BUY:
                    # 매수 실행됨
                    logger.info(f"{market} 무한매수법 매수 실행: {result.message}")

                    # Discord 알림
                    if self.discord_adapter and result.trade_amount:
                        await self._send_buy_notification(market, result)

                elif action == ActionTaken.SELL:
                    # 매도 실행됨
                    logger.info(f"{market} 무한매수법 매도 실행: {result.message}")

                    # Discord 알림
                    if self.discord_adapter and result.trade_amount:
                        await self._send_sell_notification(market, result)

                elif action == ActionTaken.HOLD:
                    # HOLD 신호는 디버그 레벨로만 로깅
                    logger.debug(f"{market}: {result.message}")

                else:
                    # 기타 액션
                    logger.info(f"{market}: {result.message}")
            else:
                # 실행 실패
                logger.error(f"{market} 무한매수법 실행 실패: {result.message}")

                # Discord 에러 알림
                if self.discord_adapter:
                    await self._send_error_notification(market, result.message)

        except Exception as e:
            logger.error(
                f"Error handling cycle result for {market}: {e}", exc_info=True
            )

    async def _send_buy_notification(
        self, market: MarketName, result: InfiniteBuyingResult
    ) -> None:
        """매수 알림 전송"""
        try:
            if not self.discord_adapter:
                return

            state = result.current_state
            if not state or not result.trade_price or not result.trade_amount:
                return

            title = "🟢 무한매수법 매수 실행"
            message = f"**{market}** {state.current_round}회차 매수가 실행되었습니다."

            fields = [
                ("매수 가격", f"{float(result.trade_price):,.0f} 원", True),
                ("매수 금액", f"{float(result.trade_amount):,.0f} 원", True),
                ("현재 회차", f"{state.current_round}회", True),
                ("평균 단가", f"{float(state.average_price):,.0f} 원", True),
                ("총 투자액", f"{float(state.total_investment):,.0f} 원", True),
                ("목표 가격", f"{float(state.target_sell_price):,.0f} 원", True),
            ]

            await self.discord_adapter.send_info_notification(
                title=title,
                message=message,
                fields=fields,
            )

        except Exception as e:
            logger.error(f"Error sending buy notification: {e}", exc_info=True)

    async def _send_sell_notification(
        self, market: MarketName, result: InfiniteBuyingResult
    ) -> None:
        """매도 알림 전송"""
        try:
            if not self.discord_adapter:
                return

            state = result.current_state
            profit_rate = result.profit_rate

            if not result.trade_price or not result.trade_amount:
                return

            title = "🔴 무한매수법 매도 실행"
            message = f"**{market}** 사이클이 완료되어 전량 매도되었습니다."

            fields = [
                ("매도 가격", f"{float(result.trade_price):,.0f} 원", True),
                ("매도 금액", f"{float(result.trade_amount):,.0f} 원", True),
                (
                    "수익률",
                    f"{float(profit_rate):.2%}" if profit_rate else "계산 중",
                    True,
                ),
            ]

            if state:
                fields.extend(
                    [
                        ("총 회차", f"{state.current_round}회", True),
                        ("총 투자액", f"{float(state.total_investment):,.0f} 원", True),
                        ("평균 단가", f"{float(state.average_price):,.0f} 원", True),
                    ]
                )

            await self.discord_adapter.send_info_notification(
                title=title,
                message=message,
                fields=fields,
            )

        except Exception as e:
            logger.error(f"Error sending sell notification: {e}", exc_info=True)

    async def _send_error_notification(
        self, market: MarketName, error_message: str
    ) -> None:
        """에러 알림 전송"""
        try:
            if not self.discord_adapter:
                return

            await self.discord_adapter.send_error_notification(
                error_type="무한매수법 실행 오류",
                error_message=f"**{market}** 무한매수법 실행 중 오류가 발생했습니다.\n{error_message}",
            )

        except Exception as e:
            logger.error(f"Error sending error notification: {e}", exc_info=True)

    async def get_status(self) -> dict[str, bool | float | str | list[MarketName]]:
        """스케줄러 상태 반환"""
        active_markets = await self.infinite_buying_usecase.get_active_markets()
        return {
            "running": self._running,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "active_markets": active_markets,
        }
