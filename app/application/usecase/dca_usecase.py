import logging
from decimal import Decimal
from typing import Any

from app.domain.enums import TradingAction
from app.domain.exceptions import ConfigSaveError, StateSaveError
from app.domain.models.account import Account
from app.domain.models.dca import (
    DcaConfig,
    DcaResult,
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
    ) -> None:
        self.account_repository = account_repository
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.dca_repository = dca_repository
        self.notification_repo = notification_repo

    def _ticker_to_market_data(self, ticker: Ticker, market: MarketName) -> MarketData:
        """Ticker 객체를 MarketData로 변환"""
        return MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

    async def start_dca(
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
        DCA 시작

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
        # 이미 실행 중인지 확인
        existing_state = await self.dca_repository.get_state(market)
        if existing_state and existing_state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.START,
                message=f"{market} DCA가 이미 실행 중입니다.",
            )

        # 설정 생성
        config_kwargs: dict[str, Any] = {
            "initial_buy_amount": initial_buy_amount,
            "target_profit_rate": target_profit_rate,
            "price_drop_threshold": price_drop_threshold,
            "max_buy_rounds": max_buy_rounds,
        }

        # 시간 기반 매수 설정이 지정된 경우 적용
        if time_based_buy_interval_hours is not None:
            config_kwargs["time_based_buy_interval_hours"] = (
                time_based_buy_interval_hours
            )
            # 별도 지정이 없으면 활성화 처리
            if enable_time_based_buying is None:
                enable_time_based_buying = True

        if enable_time_based_buying is not None:
            config_kwargs["enable_time_based_buying"] = enable_time_based_buying

        if add_buy_multiplier is not None:
            config_kwargs["add_buy_multiplier"] = add_buy_multiplier

        config = DcaConfig(**config_kwargs)

        # 알고리즘 인스턴스 생성 (초기 상태 설정용)
        algorithm = DcaService(config)

        # 상태를 첫 매수 대기 상태로 설정 (cycle_id 자동 생성)
        algorithm.state.reset_cycle(market)

        # 설정 저장
        config_saved = await self.dca_repository.save_config(market, config)
        if not config_saved:
            raise ConfigSaveError()

        # 초기 상태 저장
        state_saved = await self.dca_repository.save_state(market, algorithm.state)
        if not state_saved:
            raise StateSaveError()

        logger.info(
            f"DCA 시작: {market}, 초기금액: {initial_buy_amount:,.0f}원, "
            f"목표수익률: {target_profit_rate:.1%}"
        )

        await self.notification_repo.send_info_notification(
            title="DCA 시작",
            message=f"**{market}** 마켓의 DCA를 시작합니다.",
            fields=[
                ("초기 매수 금액", f"{initial_buy_amount:,.0f} KRW", True),
                ("목표 수익률", f"{target_profit_rate:.1%}", True),
            ],
        )

        return DcaResult(
            success=True,
            action_taken=ActionTaken.START,
            message=f"{market} DCA가 시작되었습니다.",
            current_state=algorithm.state,
        )

    async def stop_dca(
        self, market: MarketName, *, force_sell: bool = False
    ) -> DcaResult:
        """
        DCA 종료

        Args:
            market: 거래 시장
            force_sell: 강제 매도 여부

        Returns:
            DcaResult: 종료 결과
        """
        # 실행 중인 알고리즘 확인
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state or not state.is_active:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.STOP,
                message=f"{market} DCA가 실행 중이 아닙니다.",
            )

        # 임시 알고리즘 인스턴스 생성
        algorithm = DcaService(config)
        algorithm.state = state

        # 강제 매도인 경우 현재 보유량 전량 매도
        if force_sell and algorithm.state.is_active:
            # 계좌 정보 조회
            account = await self.account_repository.get_account_balance()

            # 시장 데이터 조회
            ticker = await self.ticker_repository.get_ticker(market)
            market_data = self._ticker_to_market_data(ticker, market)

            # 보유 수량 확인
            target_balance = None
            target_currency = market.split("-")[1]

            for balance in account.balances:
                if balance.currency == target_currency:
                    target_balance = balance
                    break

            if target_balance and target_balance.balance > 0:
                # 전량 매도 실행
                sell_result = await algorithm.execute_sell(
                    market_data, target_balance.balance
                )

                if sell_result.success:
                    logger.info(f"강제 매도 완료: {market}")
                else:
                    logger.warning(f"강제 매도 실패: {sell_result.message}")

        # 데이터 삭제
        await self.dca_repository.clear_market_data(market)

        action_msg = "강제 종료" if force_sell else "정상 종료"

        logger.info(f"DCA {action_msg}: {market}")

        await self.notification_repo.send_info_notification(
            title=f"DCA {action_msg}",
            message=f"**{market}** 마켓의 DCA를 종료했습니다.",
        )

        return DcaResult(
            success=True,
            action_taken=ActionTaken.STOP,
            message=f"{market} DCA가 {action_msg}되었습니다.",
            current_state=algorithm.state,
        )

    async def execute_dca_cycle(self, market: MarketName) -> DcaResult:
        """
        DCA 사이클 실행 (스케줄러에서 호출)

        Args:
            market: 거래 시장

        Returns:
            DcaResult: 사이클 실행 결과
        """
        # 설정 및 상태 조회
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=f"{market} DCA가 실행 중이 아닙니다.",
            )

        # 알고리즘 인스턴스 생성
        algorithm = DcaService(config)
        algorithm.state = state

        try:
            # 계좌 정보 조회
            account = await self.account_repository.get_account_balance()

            # 시장 데이터 조회
            ticker = await self.ticker_repository.get_ticker(market)
            market_data = self._ticker_to_market_data(ticker, market)

            # 신호 분석
            signal = await algorithm.analyze_signal(account, market_data)

            # 액션에 따른 처리
            if signal.action == TradingAction.BUY:
                return await self._handle_buy_signal(
                    algorithm, market, account, market_data, signal
                )
            elif signal.action == TradingAction.SELL:
                return await self._handle_sell_signal(algorithm, market)
            else:  # HOLD
                return DcaResult(
                    success=True,
                    action_taken=ActionTaken.HOLD,
                    message=signal.reason,
                    current_state=algorithm.state,
                )

        except Exception as e:
            logger.error(f"DCA 사이클 실행 실패: {market}, 오류: {e}")
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=f"DCA 사이클 실행 중 오류 발생: {str(e)}",
                current_state=algorithm.state,
            )

    async def get_active_markets(self) -> list[MarketName]:
        """활성 상태인 마켓 목록 조회"""
        return await self.dca_repository.get_active_markets()

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

    async def _handle_buy_signal(
        self,
        algorithm: DcaService,
        market: MarketName,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
    ) -> DcaResult:
        """매수 신호 처리"""
        # 매수 금액 계산
        buy_amount = await algorithm.calculate_buy_amount(
            account,
            signal,
            Decimal("5000"),  # 최소 주문 금액
        )

        if buy_amount <= 0:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message="매수 조건 미충족 (자금 부족 또는 기타 제약)",
                current_state=algorithm.state,
            )

        # 실제 주문 실행 (시장가 매수)
        from decimal import Decimal as _D

        order_request = OrderRequest.create_market_buy(market, _D(str(buy_amount)))
        order_result = await self.order_repository.place_order(order_request)

        if not order_result.success:
            # 주문 실패 시 상태 변경 없이 실패 반환
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=order_result.error_message or "주문 실패",
                current_state=algorithm.state,
            )

        # 주문 성공 시 상태 업데이트
        result = await algorithm.execute_buy(market_data, buy_amount)

        # 상태 저장
        await self.dca_repository.save_state(market, algorithm.state)

        return result

    async def _handle_sell_signal(
        self,
        algorithm: DcaService,
        market: MarketName,
    ) -> DcaResult:
        """매도 신호 처리"""
        # 계좌 정보 조회
        account = await self.account_repository.get_account_balance()

        # 시장 데이터 조회
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = self._ticker_to_market_data(ticker, market)

        # 매도 수량 계산 (더미 신호 생성)
        sell_signal = TradingSignal(
            action=TradingAction.SELL, confidence=Decimal("1.0"), reason="DCA 매도 신호"
        )
        sell_volume = await algorithm.calculate_sell_amount(
            account, market_data, sell_signal
        )

        if sell_volume <= 0:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message="매도 수량 없음",
                current_state=algorithm.state,
            )

        # 실제 주문 실행 (시장가 매도)
        order_request = OrderRequest.create_market_sell(market, sell_volume)
        order_result = await self.order_repository.place_order(order_request)

        if not order_result.success:
            return DcaResult(
                success=False,
                action_taken=ActionTaken.HOLD,
                message=order_result.error_message or "주문 실패",
                current_state=algorithm.state,
            )

        # 주문 성공 시 상태 업데이트
        result = await algorithm.execute_sell(market_data, sell_volume)

        # 상태 저장
        await self.dca_repository.save_state(market, algorithm.state)

        # 수익 실현 알림 (성공적인 매도의 경우)
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
