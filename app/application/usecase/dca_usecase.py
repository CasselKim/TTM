import logging
from decimal import Decimal
from typing import Any

from app.domain.enums import TradingAction
from app.domain.models.dca import BuyType
from app.domain.exceptions import ConfigSaveError, StateSaveError
from app.domain.models.dca import (
    DcaConfig,
    DcaResult,
    DcaState,
)

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

    async def start(
        self,
        market: MarketName,
        initial_buy_amount: int,
        target_profit_rate: Decimal = Decimal("0.10"),
        price_drop_threshold: Decimal = Decimal("-0.025"),
        max_buy_rounds: int = 8,
        *,
        time_based_buy_interval_hours: int = 72,
        enable_time_based_buying: bool = True,
        add_buy_multiplier: Decimal = Decimal("1.5"),
        force_stop_loss_rate: Decimal = Decimal("-0.25"),
        max_investment_ratio: Decimal = Decimal("1"),
        min_buy_interval_minutes: int = 30,
        max_cycle_days: int = 45,
    ) -> DcaResult:
        """
        DCA 시작 및 초기 매수 실행
        """
        existing_state = await self.dca_repository.get_state(market)
        if existing_state and existing_state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.START,
                message=f"{market} DCA가 이미 실행 중입니다.",
                current_state=None,
            )

        config = DcaConfig(
            initial_buy_amount=initial_buy_amount,
            target_profit_rate=target_profit_rate,
            price_drop_threshold=price_drop_threshold,
            max_buy_rounds=max_buy_rounds,
            add_buy_multiplier=add_buy_multiplier,
            force_stop_loss_rate=force_stop_loss_rate,
            max_investment_ratio=max_investment_ratio,
            min_buy_interval_minutes=min_buy_interval_minutes,
            max_cycle_days=max_cycle_days,
            time_based_buy_interval_hours=time_based_buy_interval_hours,
            enable_time_based_buying=enable_time_based_buying,
        )
        state = DcaState(market=market)
        state.reset_cycle(market)

        config_saved = await self.dca_repository.save_config(
            market=market, config=config
        )
        if not config_saved:
            logger.error(f"설정 저장 실패: market={market}")
            raise ConfigSaveError()

        state_saved = await self.dca_repository.save_state(market=market, state=state)
        if not state_saved:
            logger.error(f"상태 저장 실패: market={market}")
            raise StateSaveError()

        ticker = await self.ticker_repository.get_ticker(market)
        market_data = MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

        order_request = OrderRequest.create_market_buy(
            market=market,
            total_krw=Decimal(initial_buy_amount),
        )
        order_result = await self.order_repository.place_order(order_request)
        if not order_result.success:
            logger.error(f"초기 매수 실패: order_result={order_result}")
            await self.dca_repository.clear_market_data(market)
            return DcaResult(
                success=False,
                action_taken=ActionTaken.START,
                message=f"초기 매수 실패: {order_result.error_message}",
                current_state=None,
            )

        await self.dca_service.execute_buy(
            market_data=market_data,
            buy_amount=initial_buy_amount,
            config=config,
            state=state,
            buy_type=BuyType.INITIAL,
            reason="초기 매수",
        )
        await self.dca_repository.save_state(market=market, state=state)
        await self.dca_repository.save_config(market=market, config=config)

        await self.notification_repo.send_info_notification(
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

    async def stop(self, market: MarketName, *, force_sell: bool = False) -> DcaResult:
        """DCA 종료"""
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)
        if not config or not state:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.STOP,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=None,
            )
        if not state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.STOP,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=state,
            )

        account = await self.account_repository.get_account_balance()
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

        target_currency = market.split("-")[1]
        target_balance = next(
            (b for b in account.balances if b.currency == target_currency), None
        )
        if target_balance and target_balance.balance > 0:
            order_request = OrderRequest.create_market_sell(
                market, target_balance.balance
            )
            order_result = await self.order_repository.place_order(order_request)
            if order_result.success:
                sell_result = await self.dca_service.execute_sell(
                    market_data, target_balance.balance, state
                )
                profit_rate = sell_result.profit_rate or Decimal("0")
                profit_amount = sell_result.profit_loss_amount_krw or Decimal("0")
                logger.info(
                    "DCA 종료 매도 완료: %s, 수량: %s", market, target_balance.balance
                )
                await self.notification_repo.send_info_notification(
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
                logger.warning("DCA 종료 매도 실패: %s", order_result.error_message)

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
        """DCA 사이클 실행"""
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)
        if not config or not state:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=None,
            )

        account = await self.account_repository.get_account_balance()
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

        signal = await self.dca_service.analyze_signal(
            account=account,
            market_data=market_data,
            config=config,
            state=state,
        )

        if signal.action == TradingAction.BUY:
            min_order_amount = Decimal("5000")
            buy_amount = await self.dca_service.calculate_buy_amount(
                account=account,
                signal=signal,
                min_order_amount=min_order_amount,
                config=config,
                state=state,
            )
            if buy_amount <= 0:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message="매수 조건 미충족 (자금 부족 또는 기타 제약)",
                    current_state=state,
                )
            order_request = OrderRequest.create_market_buy(
                market=market,
                total_krw=Decimal(buy_amount),
            )
            order_result = await self.order_repository.place_order(order_request)
            if not order_result.success:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message=order_result.error_message or "주문 실패",
                    current_state=state,
                )
            result = await self.dca_service.execute_buy(
                market_data=market_data,
                buy_amount=buy_amount,
                config=config,
                state=state,
                buy_type=BuyType.PRICE_DROP,
                reason=getattr(signal, "reason", None),
            )
            await self.dca_repository.save_state(market=market, state=state)
            return result

        if signal.action == TradingAction.SELL:
            sell_signal = TradingSignal(
                action=TradingAction.SELL,
                confidence=Decimal("1.0"),
                reason="DCA 매도 신호",
            )
            sell_volume = await self.dca_service.calculate_sell_amount(
                account=account,
                market_data=market_data,
                signal=sell_signal,
                state=state,
            )
            if sell_volume <= 0:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message="매도 수량 없음",
                    current_state=state,
                )
            order_request = OrderRequest.create_market_sell(
                market=market,
                volume=sell_volume,
            )
            order_result = await self.order_repository.place_order(order_request)
            if not order_result.success:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message=order_result.error_message or "주문 실패",
                    current_state=state,
                )
            result = await self.dca_service.execute_sell(
                market_data=market_data,
                sell_volume=sell_volume,
                state=state,
            )
            await self.dca_repository.save_state(market=market, state=state)
            if result.success and result.profit_rate and result.profit_rate > 0:
                await self.notification_repo.send_info_notification(
                    title="🎉 DCA 수익 실현",
                    message=f"**{market}** 수익률 {result.profit_rate:.2%} 달성",
                    fields=[
                        ("매도가", f"{result.trade_price:,.0f} KRW", True),
                        ("매도 수량", f"{result.trade_volume:.8f}", True),
                        ("실현손익", f"{result.profit_loss_amount_krw:,.0f} KRW", True),
                    ],
                )
            return result

        return DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=signal.reason,
            current_state=state,
        )

    async def get_active_dca_summary(self) -> list[dict[str, Any]]:
        """진행중인 DCA 요약 정보 조회"""
        active_markets = await self.dca_repository.get_active_markets()
        dca_summaries: list[dict[str, Any]] = []

        for market in active_markets:
            try:
                market_status = await self.get_dca_market_status(market)
                config = await self.dca_repository.get_config(market)

                if not market_status or not config:
                    continue

                symbol = market.split("-")[1] if "-" in market else market

                dca_summaries.append(
                    {
                        "market": market,
                        "symbol": symbol,
                        "current_round": market_status.current_round,
                        "max_rounds": config.max_buy_rounds,
                        "total_investment": float(market_status.total_investment),
                        "total_volume": (
                            float(market_status.total_volume)
                            if isinstance(
                                getattr(market_status, "total_volume", None),
                                (int, float, Decimal),
                            )
                            else 0.0
                        ),
                        "average_price": float(market_status.average_price),
                        "current_profit_rate": float(market_status.current_profit_rate)
                        if market_status.current_profit_rate
                        else 0.0,
                        "cycle_id": market_status.cycle_id
                        if hasattr(market_status, "cycle_id")
                        else "unknown",
                    }
                )

            except ValueError as e:
                logger.warning("DCA 요약 조회 실패 (%s): %s", market, e)

        return dca_summaries

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
                    reason=buy_round.reason,
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
