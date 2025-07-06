import logging
from decimal import Decimal

from app.domain.enums import TradingAction
from app.domain.models.dca import BuyType
from app.domain.models.dca import (
    DcaResult,
    DcaState,
)

from app.domain.models.trading import MarketData
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.dca_repository import DcaRepository
from app.domain.repositories.notification_repository import NotificationRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.services.dca_service import DcaService
from app.domain.enums import ActionTaken
from app.domain.models.status import MarketName
from app.domain.models.order import OrderRequest
from app.domain.models.dca import DcaConfig

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
        state: DcaState,
        config: DcaConfig,
    ) -> DcaResult:
        """DCA 시작"""

        # 1. 기존 실행 여부 확인
        existing_state = await self.dca_repository.get_state(state.market)
        if existing_state and existing_state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.START,
                message=f"{state.market} DCA가 이미 실행 중입니다.",
                current_state=None,
            )

        # 2. 상태 초기화
        state = DcaState(market=state.market)

        # 3. 설정 저장
        await self.dca_repository.save_config(state.market, config)
        await self.dca_repository.save_state(state.market, state)

        # 4. 알림 전송
        await self.notification_repo.send_info_notification(
            title="DCA 시작",
            message=f"**{state.market}** 마켓의 DCA를 시작했습니다.",
            fields=[
                ("목표 수익률", f"{config.target_profit_rate:.1%}", True),
            ],
        )

        # 5. 결과 반환
        return DcaResult(
            success=True,
            action_taken=ActionTaken.START,
            message=f"{state.market} DCA가 시작되었습니다.",
            current_state=state,
        )

    async def stop(self, market: MarketName, *, force_sell: bool = False) -> DcaResult:
        """DCA 종료"""

        # 1. 설정 및 상태 조회
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state or not state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.STOP,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=state,
            )

        # 강제 매도 X → 매도 없이 종료
        if not force_sell:
            await self.dca_repository.clear_market_data(market)

            await self.notification_repo.send_info_notification(
                title="DCA 종료",
                message=f"**{market}** 마켓의 DCA를 종료했습니다. (매도 없음)",
            )

            return DcaResult(
                success=True,
                action_taken=ActionTaken.STOP,
                message=f"{market} DCA가 종료되었습니다. (매도 없음)",
                current_state=state,
            )

        # 2. 계좌 및 시세 조회
        account = await self.account_repository.get_account_balance()
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

        target_balance = account.get_balance(market.split("-")[1])

        sell_volume: Decimal = (
            target_balance.balance if target_balance else Decimal("0")
        )

        # 3. 매도 주문 생성 (잔고가 0원 이상이어야 시도)
        if sell_volume > Decimal("0"):
            order_request = OrderRequest.create_market_sell(market, sell_volume)
            order_result = await self.order_repository.place_order(order_request)

            if not order_result.success:
                # 매도 실패하더라도 DCA는 종료 처리
                await self.dca_repository.clear_market_data(market)
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.STOP,
                    message=f"{market} DCA 종료, 매도 실패: {order_result.error_message}",
                    current_state=state,
                )

            # 4. 매도 실행 및 결과 계산
            sell_result = await self.dca_service.execute_sell(
                market_data=market_data,
                sell_volume=sell_volume,
                state=state,
            )

            # 5. 알림 전송 (매도 완료)
            await self.notification_repo.send_info_notification(
                title="DCA 강제 종료",
                message=f"**{market}** 마켓의 DCA를 종료하고 보유 포지션을 매도했습니다.",
                fields=[
                    ("매도 수량", f"{sell_volume:.8f}", True),
                    ("매도가", f"{market_data.current_price:,.0f} KRW", True),
                    ("수익률", f"{sell_result.profit_rate:.2%}", True),
                    (
                        "손익",
                        f"{sell_result.profit_loss_amount_krw:,.0f} KRW",
                        True,
                    ),
                ],
            )
        else:
            # 매도할 잔고가 없는 경우 알림만 전송
            await self.notification_repo.send_info_notification(
                title="DCA 강제 종료",
                message=f"**{market}** 마켓의 DCA를 종료했습니다. 보유 포지션 없음.",
            )

        # 6. 상태 초기화
        await self.dca_repository.clear_market_data(market)

        return DcaResult(
            success=True,
            action_taken=ActionTaken.STOP,
            message=f"{market} DCA가 종료되었습니다. (강제 매도: {sell_volume > Decimal('0')})",
            current_state=state,
        )

    async def update(self, market: MarketName, new_config: DcaConfig) -> DcaResult:
        """DCA 설정 변경"""

        # 1. 기존 설정 및 상태 조회
        existing_config = await self.dca_repository.get_config(market)
        existing_state = await self.dca_repository.get_state(market)

        if not existing_config or not existing_state:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=None,
            )

        # 2. 새 설정 저장
        await self.dca_repository.save_config(market, new_config)

        # 3. 알림 전송
        await self.notification_repo.send_info_notification(
            title="DCA 설정 변경",
            message=f"**{market}** 마켓의 DCA 설정이 변경되었습니다.",
            fields=[
                ("목표 수익률", f"{new_config.target_profit_rate:.1%}", True),
                ("추가 매수 배수", f"{new_config.add_buy_multiplier:.1f}", True),
                (
                    "Smart DCA",
                    "활성화" if new_config.enable_smart_dca else "비활성화",
                    True,
                ),
            ],
        )

        # 4. 결과 반환
        return DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다.",
            current_state=existing_state,
        )

    async def run(self, market: MarketName) -> DcaResult:
        """DCA 사이클 실행"""

        # 1. 설정 조회
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)
        if not config or not state:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=f"{market} DCA가 실행 중이 아닙니다.",
                current_state=None,
            )

        # 2. 계좌 조회
        account = await self.account_repository.get_account_balance()
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

        # 3. 신호 분석
        signal = await self.dca_service.analyze_signal(
            account=account,
            market_data=market_data,
            config=config,
            state=state,
        )

        # 4. 매매 실행
        if signal.action == TradingAction.BUY:
            # 4-1. 매수 금액 계산
            buy_amount = await self.dca_service.calculate_buy_amount(
                account=account,
                signal=signal,
                config=config,
                state=state,
                market_data=market_data,
            )
            if buy_amount <= 0:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message="매수 조건 미충족 (자금 부족 또는 기타 제약)",
                    current_state=state,
                )

            # 4-2. 매수 주문 생성
            order_request = OrderRequest.create_market_buy(market, Decimal(buy_amount))
            order_result = await self.order_repository.place_order(order_request)
            if not order_result.success:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message=order_result.error_message or "주문 실패",
                    current_state=state,
                )

            # 4-3. 매수 실행
            result = await self.dca_service.execute_buy(
                market_data=market_data,
                buy_amount=buy_amount,
                config=config,
                state=state,
                buy_type=BuyType.PRICE_DROP,
                reason=getattr(signal, "reason", None),
            )
        elif signal.action == TradingAction.SELL:
            # 4-1. 매도 수량 계산
            sell_volume = await self.dca_service.calculate_sell_amount(
                account=account,
                market_data=market_data,
                signal=signal,
                state=state,
            )
            if sell_volume <= 0:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message="매도 수량 없음",
                    current_state=state,
                )

            # 4-2. 매도 주문 생성
            order_request = OrderRequest.create_market_sell(market, sell_volume)
            order_result = await self.order_repository.place_order(order_request)
            if not order_result.success:
                return DcaResult(
                    success=False,
                    action_taken=ActionTaken.HOLD,
                    message=order_result.error_message or "주문 실패",
                    current_state=state,
                )

            # 4-3. 매도 실행
            result = await self.dca_service.execute_sell(
                market_data=market_data,
                sell_volume=sell_volume,
                state=state,
            )
        else:
            result = DcaResult(
                success=True,
                action_taken=ActionTaken.HOLD,
                message=signal.reason,
                current_state=state,
            )

        # 6. 상태 저장
        await self.dca_repository.save_state(market, state)

        # 7. 결과 반환
        return result
