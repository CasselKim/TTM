import logging
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.repositories.dca_repository import DcaRepository
from app.domain.constants import (
    ALGORITHM_MAX_CONFIDENCE,
    TRADING_DEFAULT_MIN_ORDER_AMOUNT,
)
from app.domain.enums import TradingAction
from app.domain.models.account import Account
from app.domain.models.dca import (
    BuyingRound,
    BuyType,
    DcaConfig,
    DcaResult,
    DcaState,
)
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.enums import ActionTaken, DcaPhase

logger = logging.getLogger(__name__)


class DcaService:
    def __init__(self, dca_repository: DcaRepository) -> None:
        self.dca_repository = dca_repository

    """
    분할 매수를 통한 평균 단가 하락 및 목표 수익률 달성 시 익절하는 전략
    """

    async def analyze_signal(
        self,
        account: Account,
        market_data: MarketData,
        config: DcaConfig,
        state: DcaState,
    ) -> TradingSignal:
        """
        DCA 신호 분석

        현재 상태에 따라 매수/매도/홀드 신호를 생성합니다.
        """
        # 초기 매수 or 비활성 상태
        if state.phase == DcaPhase.INITIAL_BUY or not state.is_active:
            if account.available_krw < config.initial_buy_amount:
                return TradingSignal(
                    action=TradingAction.HOLD,
                    confidence=ALGORITHM_MAX_CONFIDENCE,
                    reason=f"초기 매수 불가: 필요금액 {config.initial_buy_amount:,.0f}원, 보유금액 {account.available_krw:,.0f}원",
                )

            return TradingSignal(
                action=TradingAction.BUY,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason="DCA 초기 매수 신호",
            )

        # 현재 수익률 계산
        current_profit_rate = state.calculate_current_profit_rate(
            market_data.current_price
        )

        # 강제 손절 확인
        if await self._should_force_sell(current_profit_rate, config, state):
            return TradingSignal(
                action=TradingAction.SELL,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"강제 손절: 수익률 {current_profit_rate:.2%}",
            )

        # 익절 확인
        if await self._should_take_profit(current_profit_rate, config):
            return TradingSignal(
                action=TradingAction.SELL,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"목표 수익률 달성: {current_profit_rate:.2%}",
            )

        # 추가 매수 확인
        should_buy, buy_reason = await self._should_add_buy(
            account=account,
            market_data=market_data,
            config=config,
            state=state,
        )

        # 추가 매수 신호 생성
        if should_buy:
            current_price = market_data.current_price
            drop_rate = (state.average_price - current_price) / state.average_price

            return TradingSignal(
                action=TradingAction.BUY,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"{buy_reason} (평균단가: {state.average_price:,.0f}, 현재가: {current_price:,.0f}, 하락률: {drop_rate:.2%})",
            )

        # 매수/매도 신호가 없으면 홀드
        return TradingSignal(
            action=TradingAction.HOLD,
            confidence=ALGORITHM_MAX_CONFIDENCE,
            reason=f"DCA 대기 중 (평균단가: {state.average_price:,.0f}, 현재가: {market_data.current_price:,.0f}, 수익률: {current_profit_rate:.2%})",
        )

    async def calculate_buy_amount(
        self,
        account: Account,
        signal: TradingSignal,
        config: DcaConfig,
        state: DcaState,
    ) -> int:
        """
        DCA 매수 금액 계산
        """
        if signal.action != TradingAction.BUY:
            return 0

        # Decimal -> int
        available_krw_int = int(account.available_krw)

        if state.current_round == 0:
            # 초기 매수
            buy_amount = min(config.initial_buy_amount, available_krw_int)
        else:
            # 추가 매수: 이전 매수 금액의 배수
            if not state.buying_rounds:
                # 데이터 불일치 상황: current_round > 0이지만 buying_rounds가 비어있음
                # 이 경우 초기 매수 금액을 기준으로 계산
                logger.warning(
                    f"데이터 불일치 감지: current_round={state.current_round}이지만 "
                    "buying_rounds가 비어있습니다. 초기 매수 금액으로 계산합니다."
                )
                buy_amount = min(config.initial_buy_amount, available_krw_int)
            else:
                last_round = state.buying_rounds[-1]
                buy_amount = int(last_round.buy_amount * config.add_buy_multiplier)
                buy_amount = min(buy_amount, available_krw_int)

        # 최소 주문 금액 확인
        if Decimal(buy_amount) < TRADING_DEFAULT_MIN_ORDER_AMOUNT:
            return 0

        # 총 투자 한도 확인 (전체 KRW 잔액 대비)
        total_krw = sum(
            balance.balance for balance in account.balances if balance.currency == "KRW"
        )
        max_total_investment = total_krw * config.max_investment_ratio

        total_investment_decimal = Decimal(str(state.total_investment))
        if total_investment_decimal + Decimal(buy_amount) > max_total_investment:
            buy_amount = int(max_total_investment - total_investment_decimal)
            if Decimal(buy_amount) < TRADING_DEFAULT_MIN_ORDER_AMOUNT:
                return 0

        logger.info(
            f"DCA 매수 금액 계산: {state.current_round + 1}회차, "
            f"매수금액 {buy_amount}원 (사용가능: {account.available_krw:,.0f}원)"
        )

        return buy_amount

    async def calculate_sell_amount(
        self,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
        state: DcaState,
    ) -> Decimal:
        """
        DCA 매도 수량 계산 (전량 매도)
        """
        if signal.action != TradingAction.SELL:
            return Decimal("0")

        currency = market_data.market.split("-")[1]
        target_balance = account.get_balance(currency)
        if not target_balance:
            return Decimal("0")

        # 사용 가능한 전량 매도
        available_volume = target_balance.balance - target_balance.locked

        logger.info(
            f"DCA 매도 수량 계산: 전량 매도 {available_volume} "
            f"(평균단가: {state.average_price:,.0f})"
        )

        return available_volume

    async def execute_buy(
        self,
        market_data: MarketData,
        buy_amount: int,
        config: DcaConfig,
        state: DcaState,
        buy_type: BuyType | None = None,
        reason: str | None = None,
    ) -> DcaResult:
        """
        매수 실행 및 상태 업데이트
        """
        current_price = market_data.current_price
        buy_volume = (
            Decimal(str(buy_amount)) / current_price
        )  # 수수료는 실제 거래에서 적용

        # 새로운 매수 회차 생성
        new_round = BuyingRound(
            round_number=state.current_round + 1,
            buy_price=current_price,
            buy_amount=buy_amount,
            buy_volume=buy_volume,
            timestamp=datetime.now(),
            buy_type=buy_type if buy_type is not None else BuyType.PRICE_DROP,
            reason=reason,
        )

        # 상태 업데이트
        if not state.is_active:
            state.reset_cycle(market_data.market)  # 새 사이클 시작 (cycle_id 자동 생성)

        state.add_buying_round(new_round, config)
        state.phase = DcaPhase.ACCUMULATING

        result = DcaResult(
            success=True,
            action_taken=ActionTaken.BUY,
            message=f"DCA 매수 실행: {new_round.round_number}회차",
            trade_price=current_price,
            trade_amount=buy_amount,
            trade_volume=buy_volume,
            current_state=state,
            profit_rate=state.calculate_current_profit_rate(current_price),
        )

        # 상태 저장
        await self.dca_repository.save_state(state.market, state)

        logger.info(
            f"DCA 매수 실행: {new_round.round_number}회차, "
            f"매수가 {current_price:,.0f}원, 매수량 {buy_volume:.8f}, "
            f"평균단가 {state.average_price:,.0f}원"
        )

        return result

    async def execute_sell(
        self,
        market_data: MarketData,
        sell_volume: Decimal,
        state: DcaState,
    ) -> DcaResult:
        """
        매도 실행 및 상태 업데이트
        """
        current_price = market_data.current_price
        sell_amount = int(sell_volume * current_price)
        current_profit_rate = state.calculate_current_profit_rate(current_price)

        # 결과 생성
        profit_loss_amount = sell_amount - state.total_investment
        result = DcaResult(
            success=True,
            action_taken=ActionTaken.SELL,
            message=f"DCA 매도 실행: 수익률 {current_profit_rate:.2%}",
            trade_price=current_price,
            trade_amount=sell_amount,
            trade_volume=sell_volume,
            current_state=state,
            profit_rate=current_profit_rate,
            profit_loss_amount_krw=profit_loss_amount,
        )

        # 상태 리셋 (사이클 종료)
        state.phase = DcaPhase.INACTIVE
        state.current_round = 0
        state.total_investment = 0
        state.total_volume = Decimal("0")
        state.average_price = Decimal("0")
        state.buying_rounds = []

        # 상태 저장
        await self.dca_repository.save_state(state.market, state)

        logger.info(
            f"DCA 매도 실행: 매도가 {current_price:,.0f}원, "
            f"매도량 {sell_volume:.8f}, 수익률 {current_profit_rate:.2%}, "
            f"실현손익 {profit_loss_amount:,.0f}원"
        )

        return result

    async def _should_force_sell(
        self, current_profit_rate: Decimal, config: DcaConfig, state: DcaState
    ) -> bool:
        """
        강제 손절 조건 확인

        Args:
            current_profit_rate: 현재 수익률
            config: DCA 설정
            state: DCA 상태

        Returns:
            bool: 강제 손절 여부
        """
        # 최대 회차 도달 시 강제 손절
        if state.current_round >= config.max_buy_rounds:
            logger.warning(
                f"최대 회차 도달: 현재 {state.current_round}회차, "
                f"최대 {config.max_buy_rounds}회차"
            )
            return True

        # 최대 손실률 초과
        if current_profit_rate <= config.force_stop_loss_rate:
            logger.warning(
                f"최대 손실률 초과: 현재 {current_profit_rate:.2%}, "
                f"한계 {config.force_stop_loss_rate:.2%}"
            )
            return True

        return False

    async def _should_take_profit(
        self, current_profit_rate: Decimal, config: DcaConfig
    ) -> bool:
        """익절 조건 확인"""
        return current_profit_rate >= config.target_profit_rate

    async def _should_add_buy(
        self,
        account: Account,
        market_data: MarketData,
        config: DcaConfig,
        state: DcaState,
    ) -> tuple[bool, str]:
        """
        추가 매수 조건 확인

        Returns:
            tuple[bool, str]: (추가 매수 여부, 사유)
        """
        current_price = market_data.current_price

        # 사용 가능한 KRW 확인
        available_krw = account.available_krw
        if available_krw < config.initial_buy_amount:
            return False, "사용 가능한 KRW 부족"

        # 시간 기반 매수 조건
        if await self._should_time_based_buy(config, state):
            return True, "시간 기반 추가 매수"

        # 가격 하락 기반 매수 조건
        if await self._should_price_drop_buy(market_data, config, state):
            drop_rate = (state.average_price - current_price) / state.average_price
            return True, f"가격 하락 기반 추가 매수 (하락률: {drop_rate:.2%})"

        return False, "추가 매수 조건 미충족"

    async def _should_time_based_buy(self, config: DcaConfig, state: DcaState) -> bool:
        """
        시간 기반 추가 매수 조건 확인

        Returns:
            bool: 시간 기반 매수 여부
        """
        if not config.enable_time_based_buying:
            return False

        if not state.buying_rounds:
            return False

        last_buy_time = state.buying_rounds[-1].timestamp
        time_diff = datetime.now() - last_buy_time

        interval_hours: int = config.time_based_buy_interval_hours
        return time_diff >= timedelta(hours=interval_hours)

    async def _should_price_drop_buy(
        self, market_data: MarketData, config: DcaConfig, state: DcaState
    ) -> bool:
        """
        가격 하락 기반 추가 매수 조건 확인

        Args:
            market_data: 시장 데이터
            config: DCA 설정
            state: DCA 상태

        Returns:
            bool: 가격 하락 기반 매수 여부
        """
        current_price = market_data.current_price

        # 최소 매수 간격 확인
        if state.buying_rounds:
            last_buy_time = state.buying_rounds[-1].timestamp
            time_diff = datetime.now() - last_buy_time
            if time_diff < timedelta(minutes=config.min_buy_interval_minutes):
                return False

        # 평균 단가 대비 하락률 계산
        drop_rate = (state.average_price - current_price) / state.average_price

        return drop_rate >= abs(config.price_drop_threshold)
