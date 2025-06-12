import logging
from decimal import Decimal
from typing import Any

from app.domain.enums import TradingAction
from app.domain.exceptions import ConfigSaveError, StateSaveError
from app.domain.models.account import Account
from app.domain.models.dca import (
    DcaConfig,
    DcaResult,
    DcaState,
)
from app.domain.models.ticker import Ticker
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.dca_repository import DcaRepository
from app.domain.repositories.notification_repository import NotificationRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.services.dca_service import DcaService
from app.domain.enums import ActionTaken, DcaStatus
from app.domain.models.status import (
    BuyingRoundInfo,
    DcaMarketStatus,
    MarketName,
)
from app.domain.models.order import OrderRequest
from app.domain.constants import (
    DCA_DEFAULT_TARGET_PROFIT_RATE,
    DCA_DEFAULT_PRICE_DROP_THRESHOLD,
    DCA_DEFAULT_MAX_BUY_ROUNDS,
)

logger = logging.getLogger(__name__)


class DcaUsecase:
    def __init__(
        self,
        account_repository: AccountRepository,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
        dca_repository: DcaRepository,
        notification_repo: NotificationRepository,
        dca_service: DcaService,
    ) -> None:
        self.account_repository = account_repository
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.dca_repository = dca_repository
        self.notification_repo = notification_repo
        self.dca_service = dca_service

    async def _get_account_and_market_data(
        self, market: MarketName
    ) -> tuple[Account, MarketData]:
        """계좌 정보와 시장 데이터를 조회합니다."""
        account = await self.account_repository.get_account_balance()
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = self._ticker_to_market_data(ticker, market)
        return account, market_data

    async def _create_dca_instance(
        self, market: MarketName
    ) -> tuple[DcaConfig, DcaState] | None:
        """설정과 상태를 로드합니다."""
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state:
            return None

        return config, state

    def _create_error_result(
        self, action: ActionTaken, message: str, state: DcaState | None = None
    ) -> DcaResult:
        return DcaResult(
            success=False,
            action_taken=action,
            message=message,
            current_state=state,
        )

    async def _send_dca_notification(
        self,
        title: str,
        message: str,
        fields: list[tuple[str, str, bool]] | None = None,
    ) -> None:
        """DCA 관련 알림을 발송합니다."""
        await self.notification_repo.send_info_notification(
            title=title,
            message=message,
            fields=fields or [],
        )

    def _ticker_to_market_data(self, ticker: Ticker, market: MarketName) -> MarketData:
        """Ticker 객체를 MarketData로 변환"""
        return MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

    async def start(
        self,
        market: MarketName,
        initial_buy_amount: int,
        target_profit_rate: Decimal = DCA_DEFAULT_TARGET_PROFIT_RATE,
        price_drop_threshold: Decimal = DCA_DEFAULT_PRICE_DROP_THRESHOLD,
        max_buy_rounds: int = DCA_DEFAULT_MAX_BUY_ROUNDS,
        *,
        time_based_buy_interval_hours: int | None = None,
        enable_time_based_buying: bool | None = None,
        add_buy_multiplier: Decimal | None = None,
    ) -> DcaResult:
        """
        DCA 시작 및 초기 매수 실행

        Args:
            market: 거래 시장 (예: "KRW-BTC")
            initial_buy_amount: 초기 매수 금액
            target_profit_rate: 목표 수익률 (기본 10%)
            price_drop_threshold: 추가 매수 트리거 하락률 (기본 -5%)
            max_buy_rounds: 최대 매수 회차 (기본 10회)
            time_based_buy_interval_hours: 시간 기반 매수 간격 (시간 단위)
            enable_time_based_buying: 시간 기반 매수 활성화 여부
            add_buy_multiplier: 추가 매수 곱수 (기본 1.1)

        Returns:
            DcaResult: 시작 결과
        """
        existing_state = await self.dca_repository.get_state(market)
        if existing_state and existing_state.is_active:
            return self._create_error_result(
                ActionTaken.START, f"{market} DCA가 이미 실행 중입니다."
            )

        config_kwargs: dict[str, Any] = {
            "initial_buy_amount": initial_buy_amount,
            "target_profit_rate": target_profit_rate,
            "price_drop_threshold": price_drop_threshold,
            "max_buy_rounds": max_buy_rounds,
        }

        if time_based_buy_interval_hours is not None:
            config_kwargs["time_based_buy_interval_hours"] = (
                time_based_buy_interval_hours
            )
            if enable_time_based_buying is None:
                enable_time_based_buying = True

        if enable_time_based_buying is not None:
            config_kwargs["enable_time_based_buying"] = enable_time_based_buying

        if add_buy_multiplier is not None:
            config_kwargs["add_buy_multiplier"] = add_buy_multiplier

        config = DcaConfig(**config_kwargs)
        state = DcaState(market=market)
        state.reset_cycle(market)

        config_saved = await self.dca_repository.save_config(market, config)
        if not config_saved:
            raise ConfigSaveError()

        state_saved = await self.dca_repository.save_state(market, state)
        if not state_saved:
            raise StateSaveError()

        try:
            account, market_data = await self._get_account_and_market_data(market)

            order_request = OrderRequest.create_market_buy(
                market, Decimal(str(initial_buy_amount))
            )
            order_result = await self.order_repository.place_order(order_request)

            if not order_result.success:
                await self.dca_repository.clear_market_data(market)
                return self._create_error_result(
                    ActionTaken.START, f"초기 매수 실패: {order_result.error_message}"
                )

            await self.dca_service.execute_buy(
                market_data, initial_buy_amount, config, state
            )
            await self.dca_repository.save_state(market, state)

            logger.info(
                f"DCA 시작 및 초기 매수 완료: {market}, 금액: {initial_buy_amount:,.0f}원"
            )

            await self._send_dca_notification(
                title="DCA 시작",
                message=f"**{market}** 마켓의 DCA를 시작하고 초기 매수를 완료했습니다.",
                fields=[
                    ("초기 매수 금액", f"{initial_buy_amount:,.0f} KRW", True),
                    ("목표 수익률", f"{target_profit_rate:.1%}", True),
                    ("매수가", f"{market_data.current_price:,.0f} KRW", True),
                ],
            )

            return DcaResult(
                success=True,
                action_taken=ActionTaken.START,
                message=f"{market} DCA가 시작되고 초기 매수가 완료되었습니다.",
                current_state=state,
            )

        except Exception as e:
            await self.dca_repository.clear_market_data(market)
            logger.error(f"DCA 시작 중 오류: {market}, {e}")
            return self._create_error_result(
                ActionTaken.START, f"DCA 시작 중 오류 발생: {str(e)}"
            )

    async def stop(self, market: MarketName, *, force_sell: bool = False) -> DcaResult:
        """DCA 종료 및 보유 포지션 정리"""
        dca_data = await self._create_dca_instance(market)
        if not dca_data:
            return self._create_error_result(
                ActionTaken.STOP, f"{market} DCA가 실행 중이 아닙니다."
            )

        config, state = dca_data
        if not state.is_active:
            return self._create_error_result(
                ActionTaken.STOP, f"{market} DCA가 실행 중이 아닙니다."
            )

        try:
            account, market_data = await self._get_account_and_market_data(market)

            # 대상 통화 잔고 조회 (인라인화)
            target_currency = market.split("-")[1]
            target_balance = None
            for balance in account.balances:
                if balance.currency == target_currency:
                    target_balance = balance
                    break

            if target_balance and target_balance.balance > 0:
                order_request = OrderRequest.create_market_sell(
                    market, target_balance.balance
                )
                order_result = await self.order_repository.place_order(order_request)

                if order_result.success:
                    sell_result = await self.dca_service.execute_sell(
                        market_data, target_balance.balance, state
                    )

                    logger.info(
                        f"DCA 종료 매도 완료: {market}, 수량: {target_balance.balance}"
                    )

                    profit_rate = (
                        sell_result.profit_rate
                        if sell_result.profit_rate
                        else Decimal("0")
                    )
                    profit_amount = (
                        sell_result.profit_loss_amount_krw
                        if sell_result.profit_loss_amount_krw
                        else Decimal("0")
                    )

                    await self._send_dca_notification(
                        title="DCA 종료",
                        message=f"**{market}** 마켓의 DCA를 종료하고 보유 포지션을 매도했습니다.",
                        fields=[
                            ("매도 수량", f"{target_balance.balance:.8f}", True),
                            ("매도가", f"{market_data.current_price:,.0f} KRW", True),
                            ("수익률", f"{profit_rate:.2%}", True),
                            ("손익", f"{profit_amount:,.0f} KRW", True),
                        ],
                    )
                else:
                    logger.warning(f"DCA 종료 매도 실패: {order_result.error_message}")

        except Exception as e:
            logger.error(f"DCA 종료 중 매도 오류: {market}, {e}")

        await self.dca_repository.clear_market_data(market)

        action_msg = "강제 종료" if force_sell else "정상 종료"
        logger.info(f"DCA {action_msg}: {market}")

        return DcaResult(
            success=True,
            action_taken=ActionTaken.STOP,
            message=f"{market} DCA가 {action_msg}되었습니다.",
            current_state=state,
        )

    async def run(self, market: MarketName) -> DcaResult:
        """
        DCA 사이클 실행 (스케줄러에서 호출)

        Args:
            market: 거래 시장

        Returns:
            DcaResult: 사이클 실행 결과
        """
        dca_data = await self._create_dca_instance(market)
        if not dca_data:
            return self._create_error_result(
                ActionTaken.HOLD, f"{market} DCA가 실행 중이 아닙니다."
            )

        config, state = dca_data

        try:
            account, market_data = await self._get_account_and_market_data(market)
            signal = await self.dca_service.analyze_signal(
                account, market_data, config, state
            )

            if signal.action == TradingAction.BUY:
                return await self._handle_buy_signal(
                    config, state, market, account, market_data, signal
                )
            elif signal.action == TradingAction.SELL:
                return await self._handle_sell_signal(config, state, market)
            else:
                return DcaResult(
                    success=True,
                    action_taken=ActionTaken.HOLD,
                    message=signal.reason,
                    current_state=state,
                )

        except Exception as e:
            logger.error(f"DCA 사이클 실행 실패: {market}, 오류: {e}")
            return self._create_error_result(
                ActionTaken.HOLD,
                f"DCA 사이클 실행 중 오류 발생: {str(e)}",
                state,
            )

    async def _handle_buy_signal(
        self,
        config: DcaConfig,
        state: DcaState,
        market: MarketName,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
    ) -> DcaResult:
        """매수 신호 처리"""
        buy_amount = await self.dca_service.calculate_buy_amount(
            account,
            signal,
            Decimal("5000"),
            config,
            state,
        )

        if buy_amount <= 0:
            return self._create_error_result(
                ActionTaken.HOLD,
                "매수 조건 미충족 (자금 부족 또는 기타 제약)",
                state,
            )

        order_request = OrderRequest.create_market_buy(market, Decimal(str(buy_amount)))
        order_result = await self.order_repository.place_order(order_request)

        if not order_result.success:
            return self._create_error_result(
                ActionTaken.HOLD,
                order_result.error_message or "주문 실패",
                state,
            )

        result = await self.dca_service.execute_buy(
            market_data, buy_amount, config, state
        )
        await self.dca_repository.save_state(market, state)
        return result

    async def _handle_sell_signal(
        self,
        config: DcaConfig,
        state: DcaState,
        market: MarketName,
    ) -> DcaResult:
        """매도 신호 처리"""
        account, market_data = await self._get_account_and_market_data(market)

        sell_signal = TradingSignal(
            action=TradingAction.SELL, confidence=Decimal("1.0"), reason="DCA 매도 신호"
        )
        sell_volume = await self.dca_service.calculate_sell_amount(
            account, market_data, sell_signal, state
        )

        if sell_volume <= 0:
            return self._create_error_result(ActionTaken.HOLD, "매도 수량 없음", state)

        order_request = OrderRequest.create_market_sell(market, sell_volume)
        order_result = await self.order_repository.place_order(order_request)

        if not order_result.success:
            return self._create_error_result(
                ActionTaken.HOLD,
                order_result.error_message or "주문 실패",
                state,
            )

        result = await self.dca_service.execute_sell(market_data, sell_volume, state)
        await self.dca_repository.save_state(market, state)

        if result.success and result.profit_rate and result.profit_rate > 0:
            await self._send_dca_notification(
                title="🎉 DCA 수익 실현",
                message=f"**{market}** 수익률 {result.profit_rate:.2%} 달성",
                fields=[
                    ("매도가", f"{result.trade_price:,.0f} KRW", True),
                    ("매도 수량", f"{result.trade_volume:.8f}", True),
                    ("실현손익", f"{result.profit_loss_amount_krw:,.0f} KRW", True),
                ],
            )

        return result

    async def get_active_markets(self) -> list[MarketName]:
        """활성 마켓 목록 조회"""
        return await self.dca_repository.get_active_markets()

    async def get_active_dca_summary(self) -> list[dict[str, Any]]:
        """진행중인 DCA 요약 정보 조회"""
        try:
            active_markets = await self.get_active_markets()
            dca_summaries = []

            for market in active_markets:
                try:
                    market_status = await self.get_dca_market_status(market)
                    config = await self.dca_repository.get_config(market)

                    if not market_status or not config:
                        continue

                    symbol = market.split("-")[1] if "-" in market else market

                    summary = {
                        "market": market,
                        "symbol": symbol,
                        "current_round": market_status.current_round,
                        "max_rounds": config.max_buy_rounds,
                        "total_investment": float(market_status.total_investment),
                        "average_price": float(market_status.average_price),
                        "current_profit_rate": float(market_status.current_profit_rate)
                        if market_status.current_profit_rate
                        else 0.0,
                        "cycle_id": market_status.cycle_id
                        if hasattr(market_status, "cycle_id")
                        else "unknown",
                    }

                    dca_summaries.append(summary)

                except Exception as e:
                    logger.warning(f"DCA 요약 조회 실패 ({market}): {e}")
                    continue

            return dca_summaries

        except Exception as e:
            logger.exception(f"활성 DCA 요약 조회 중 오류: {e}")
            return []

    async def get_dca_market_status(self, market: MarketName) -> DcaMarketStatus:
        """특정 마켓의 DCA 상세 상태 조회"""
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state:
            raise ValueError(f"마켓 {market}의 DCA 설정 또는 상태를 찾을 수 없습니다.")

        # 현재가 조회
        try:
            ticker = await self.ticker_repository.get_ticker(market)
            current_price = ticker.trade_price
        except Exception as e:
            logger.warning(f"현재가 조회 실패 ({market}): {e}")
            current_price = None

        # 매수 회차 정보는 DcaState의 buying_rounds를 사용
        buying_rounds = []
        for buy_round in state.buying_rounds:
            buying_rounds.append(
                BuyingRoundInfo(
                    round_number=buy_round.round_number,
                    buy_price=buy_round.buy_price,
                    buy_amount=Decimal(str(buy_round.buy_amount)),
                    buy_volume=buy_round.buy_volume,
                    timestamp=buy_round.timestamp,
                )
            )

        # 수익률 계산
        current_profit_rate = None
        current_value = None
        profit_loss_amount = None

        if current_price and state.total_volume > 0:
            current_value = state.total_volume * current_price
            # int → Decimal 형 변환 후 연산(타입 오류 방지)
            total_inv_dec = Decimal(str(state.total_investment))
            profit_loss_amount = current_value - total_inv_dec

            if total_inv_dec > 0:
                current_profit_rate = (profit_loss_amount / total_inv_dec) * 100

        return DcaMarketStatus(
            market=market,
            status=DcaStatus.ACTIVE if state.is_active else DcaStatus.INACTIVE,
            phase=state.phase,
            cycle_id=state.cycle_id,
            current_round=state.current_round,
            total_investment=state.total_investment,
            total_volume=state.total_volume,
            average_price=state.average_price,
            target_sell_price=state.target_sell_price,
            last_buy_price=state.last_buy_price,
            last_buy_time=state.last_buy_time,
            cycle_start_time=state.cycle_start_time,
            current_price=current_price,
            current_profit_rate=current_profit_rate,
            current_value=current_value,
            profit_loss_amount=profit_loss_amount,
            buying_rounds=buying_rounds,
            statistics=None,
            recent_history=[],
        )
