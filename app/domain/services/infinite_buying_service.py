"""
라오어의 무한매수법 서비스

분할 매수를 통해 평균 단가를 낮추고, 목표 수익률 달성 시 전량 매도하는 투자 전략입니다.

매매 로직:
1. 초기 매수: 설정된 금액으로 첫 매수
2. 추가 매수: 평균 단가 대비 일정 비율 이상 하락 시 추가 매수 (물타기)
3. 익절: 평균 단가 대비 목표 수익률 달성 시 전량 매도
4. 손절: 강제 손절 조건 달성 시 전량 매도
5. 사이클 반복: 매도 후 새로운 사이클 시작
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.constants import AlgorithmConstants
from app.domain.enums import TradingAction
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.infinite_buying import (
    BuyingRound,
    BuyType,
    InfiniteBuyingConfig,
    InfiniteBuyingPhase,
    InfiniteBuyingResult,
    InfiniteBuyingState,
)
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.types import ActionTaken


class InfiniteBuyingService:
    """
    라오어의 무한매수법 서비스

    분할 매수를 통한 평균 단가 하락 및 목표 수익률 달성 시 익절하는 전략
    """

    def __init__(self, config: InfiniteBuyingConfig) -> None:
        self.config = config
        self.state = InfiniteBuyingState(market="")
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """
        무한매수법 신호 분석

        현재 상태에 따라 매수/매도/홀드 신호를 생성합니다.
        """
        # 초기 매수 단계 확인
        if self.state.phase == InfiniteBuyingPhase.INITIAL_BUY:
            return await self._analyze_initial_buy_signal(account)

        # 비활성 상태 확인 (이전 로직 유지)
        if not self.state.is_active:
            return await self._analyze_initial_buy_signal(account)

        # 현재 수익률 계산
        current_profit_rate = self._calculate_current_profit_rate(
            market_data.current_price
        )

        # 강제 손절 확인
        if await self._should_force_sell(current_profit_rate):
            return self._create_force_sell_signal(current_profit_rate)

        # 익절 확인
        if await self._should_take_profit(current_profit_rate):
            return self._create_profit_taking_signal(current_profit_rate)

        # 추가 매수 확인
        should_buy, buy_reason = await self._should_add_buy(account, market_data)
        if should_buy:
            return await self._create_add_buy_signal(market_data, buy_reason)

        # 홀드
        return TradingSignal(
            action=TradingAction.HOLD,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 대기 중 (평균단가: {self.state.average_price:,.0f}, 현재가: {market_data.current_price:,.0f}, 수익률: {current_profit_rate:.2%})",
        )

    async def calculate_buy_amount(
        self,
        account: Account,
        signal: TradingSignal,
        min_order_amount: Decimal,
    ) -> Decimal:
        """
        무한매수법 매수 금액 계산
        """
        if signal.action != TradingAction.BUY:
            return Decimal("0")

        available_krw = self._get_available_krw_balance(account)

        # 초기 매수인지 추가 매수인지 확인
        if self.state.current_round == 0:
            # 초기 매수
            buy_amount = min(self.config.initial_buy_amount, available_krw)
        else:
            # 추가 매수: 이전 매수 금액의 배수
            if not self.state.buying_rounds:
                # 데이터 불일치 상황: current_round > 0이지만 buying_rounds가 비어있음
                # 이 경우 초기 매수 금액을 기준으로 계산
                self.logger.warning(
                    f"데이터 불일치 감지: current_round={self.state.current_round}이지만 "
                    "buying_rounds가 비어있습니다. 초기 매수 금액으로 계산합니다."
                )
                buy_amount = min(self.config.initial_buy_amount, available_krw)
            else:
                last_round = self.state.buying_rounds[-1]
                buy_amount = last_round.buy_amount * self.config.add_buy_multiplier
                buy_amount = min(buy_amount, available_krw)

        # 최소 주문 금액 확인
        if buy_amount < min_order_amount:
            return Decimal("0")

        # 총 투자 한도 확인 (전체 KRW 잔액 대비)
        total_krw = sum(
            balance.balance
            for balance in account.balances
            if balance.currency == Currency.KRW
        )
        max_total_investment = total_krw * self.config.max_investment_ratio

        if self.state.total_investment + buy_amount > max_total_investment:
            buy_amount = max_total_investment - self.state.total_investment
            if buy_amount < min_order_amount:
                return Decimal("0")

        self.logger.info(
            f"무한매수법 매수 금액 계산: {self.state.current_round + 1}회차, "
            f"매수금액 {buy_amount:,.0f}원 (사용가능: {available_krw:,.0f}원)"
        )

        return buy_amount

    async def calculate_sell_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        무한매수법 매도 수량 계산 (전량 매도)
        """
        if signal.action != TradingAction.SELL:
            return Decimal("0")

        target_balance = self._get_target_currency_balance(account, market_data.market)
        if not target_balance:
            return Decimal("0")

        # 사용 가능한 전량 매도
        available_volume = target_balance.balance - target_balance.locked

        self.logger.info(
            f"무한매수법 매도 수량 계산: 전량 매도 {available_volume} "
            f"(평균단가: {self.state.average_price:,.0f})"
        )

        return available_volume

    async def execute_buy(
        self,
        market_data: MarketData,
        buy_amount: Decimal,
        buy_type: BuyType = BuyType.INITIAL,
    ) -> InfiniteBuyingResult:
        """
        매수 실행 및 상태 업데이트
        """
        try:
            current_price = market_data.current_price
            buy_volume = buy_amount / current_price  # 수수료는 실제 거래에서 적용

            # 새로운 매수 회차 생성
            new_round = BuyingRound(
                round_number=self.state.current_round + 1,
                buy_price=current_price,
                buy_amount=buy_amount,
                buy_volume=buy_volume,
                timestamp=datetime.now(),
                buy_type=buy_type,
            )

            # 상태 업데이트
            if not self.state.is_active:
                # 새 사이클 시작 (cycle_id 자동 생성)
                self.state.reset_cycle(market_data.market)

            self.state.add_buying_round(new_round, self.config)
            self.state.phase = InfiniteBuyingPhase.ACCUMULATING

            result = InfiniteBuyingResult(
                success=True,
                action_taken=ActionTaken.BUY,
                message=f"무한매수법 매수 실행: {new_round.round_number}회차",
                trade_price=current_price,
                trade_amount=buy_amount,
                trade_volume=buy_volume,
                current_state=self.state,
                profit_rate=self._calculate_current_profit_rate(current_price),
            )

            self.logger.info(
                f"무한매수법 매수 실행: {new_round.round_number}회차, "
                f"매수가 {current_price:,.0f}원, 매수량 {buy_volume:.8f}, "
                f"평균단가 {self.state.average_price:,.0f}원"
            )

            return result

        except Exception as e:
            self.logger.error(f"무한매수법 매수 실행 실패: {e}")
            raise

    async def execute_sell(
        self,
        market_data: MarketData,
        sell_volume: Decimal,
    ) -> InfiniteBuyingResult:
        """
        매도 실행 및 상태 업데이트
        """
        try:
            current_price = market_data.current_price
            sell_amount = sell_volume * current_price
            current_profit_rate = self._calculate_current_profit_rate(current_price)

            # 결과 생성
            profit_loss_amount = sell_amount - self.state.total_investment
            result = InfiniteBuyingResult(
                success=True,
                action_taken=ActionTaken.SELL,
                message=f"무한매수법 매도 실행: 수익률 {current_profit_rate:.2%}",
                trade_price=current_price,
                trade_amount=sell_amount,
                trade_volume=sell_volume,
                current_state=self.state,
                profit_rate=current_profit_rate,
                profit_loss_amount_krw=profit_loss_amount,
            )

            # 상태 리셋 (사이클 종료)
            self.state.phase = InfiniteBuyingPhase.INACTIVE
            self.state.current_round = 0
            self.state.total_investment = Decimal("0")
            self.state.total_volume = Decimal("0")
            self.state.average_price = Decimal("0")
            self.state.buying_rounds = []

            self.logger.info(
                f"무한매수법 매도 실행: 매도가 {current_price:,.0f}원, "
                f"매도량 {sell_volume:.8f}, 수익률 {current_profit_rate:.2%}, "
                f"실현손익 {profit_loss_amount:,.0f}원"
            )

            return result

        except Exception as e:
            self.logger.error(f"무한매수법 매도 실행 실패: {e}")
            raise

    async def _analyze_initial_buy_signal(self, account: Account) -> TradingSignal:
        """
        초기 매수 신호 분석
        """
        available_krw = self._get_available_krw_balance(account)

        if available_krw < self.config.initial_buy_amount:
            return TradingSignal(
                action=TradingAction.HOLD,
                confidence=AlgorithmConstants.MAX_CONFIDENCE,
                reason=f"초기 매수 불가: 필요금액 {self.config.initial_buy_amount:,.0f}원, 보유금액 {available_krw:,.0f}원",
            )

        return TradingSignal(
            action=TradingAction.BUY,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason="무한매수법 초기 매수 신호",
        )

    def _calculate_current_profit_rate(self, current_price: Decimal) -> Decimal:
        """현재 수익률 계산"""
        if self.state.average_price == 0:
            return Decimal("0")
        return (current_price - self.state.average_price) / self.state.average_price

    async def _should_force_sell(self, current_profit_rate: Decimal) -> bool:
        """
        강제 손절 조건 확인

        Args:
            current_profit_rate: 현재 수익률

        Returns:
            bool: 강제 손절 여부
        """
        # 최대 회차 도달 시 강제 손절
        if self.state.current_round >= self.config.max_buy_rounds:
            self.logger.warning(
                f"최대 회차 도달: 현재 {self.state.current_round}회차, "
                f"최대 {self.config.max_buy_rounds}회차"
            )
            return True

        # 최대 손실률 초과
        if current_profit_rate <= self.config.force_stop_loss_rate:
            self.logger.warning(
                f"최대 손실률 초과: 현재 {current_profit_rate:.2%}, "
                f"한계 {self.config.force_stop_loss_rate:.2%}"
            )
            return True

        return False

    async def _should_take_profit(self, current_profit_rate: Decimal) -> bool:
        """익절 조건 확인"""
        return current_profit_rate >= self.config.target_profit_rate

    async def _should_add_buy(
        self, account: Account, market_data: MarketData
    ) -> tuple[bool, str]:
        """
        추가 매수 조건 확인

        Returns:
            tuple[bool, str]: (추가 매수 여부, 사유)
        """
        current_price = market_data.current_price

        # 사용 가능한 KRW 확인
        available_krw = self._get_available_krw_balance(account)
        if available_krw < self.config.initial_buy_amount:
            return False, "사용 가능한 KRW 부족"

        # 시간 기반 매수 조건
        if await self._should_time_based_buy():
            return True, "시간 기반 추가 매수"

        # 가격 하락 기반 매수 조건
        if await self._should_price_drop_buy(market_data):
            drop_rate = (
                self.state.average_price - current_price
            ) / self.state.average_price
            return True, f"가격 하락 기반 추가 매수 (하락률: {drop_rate:.2%})"

        return False, "추가 매수 조건 미충족"

    async def _should_time_based_buy(self) -> bool:
        """
        시간 기반 추가 매수 조건 확인

        Returns:
            bool: 시간 기반 매수 여부
        """
        if not self.config.enable_time_based_buying:
            return False

        if not self.state.buying_rounds:
            return False

        last_buy_time = self.state.buying_rounds[-1].timestamp
        time_diff = datetime.now() - last_buy_time

        return time_diff >= timedelta(days=self.config.time_based_buy_interval_days)

    async def _should_price_drop_buy(self, market_data: MarketData) -> bool:
        """
        가격 하락 기반 추가 매수 조건 확인

        Args:
            market_data: 시장 데이터

        Returns:
            bool: 가격 하락 기반 매수 여부
        """
        current_price = market_data.current_price

        # 최소 매수 간격 확인
        if self.state.buying_rounds:
            last_buy_time = self.state.buying_rounds[-1].timestamp
            time_diff = datetime.now() - last_buy_time
            if time_diff < timedelta(minutes=self.config.min_buy_interval_minutes):
                return False

        # 평균 단가 대비 하락률 계산
        drop_rate = (
            self.state.average_price - current_price
        ) / self.state.average_price

        return drop_rate >= abs(self.config.price_drop_threshold)

    def _create_force_sell_signal(self, current_profit_rate: Decimal) -> TradingSignal:
        """강제 손절 신호 생성"""
        return TradingSignal(
            action=TradingAction.SELL,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"강제 손절: 수익률 {current_profit_rate:.2%}",
        )

    def _create_profit_taking_signal(
        self, current_profit_rate: Decimal
    ) -> TradingSignal:
        """익절 신호 생성"""
        return TradingSignal(
            action=TradingAction.SELL,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"목표 수익률 달성: {current_profit_rate:.2%}",
        )

    async def _create_add_buy_signal(
        self, market_data: MarketData, buy_reason: str
    ) -> TradingSignal:
        """추가 매수 신호 생성"""
        current_price = market_data.current_price
        drop_rate = (
            self.state.average_price - current_price
        ) / self.state.average_price

        return TradingSignal(
            action=TradingAction.BUY,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"{buy_reason} (평균단가: {self.state.average_price:,.0f}, 현재가: {current_price:,.0f}, 하락률: {drop_rate:.2%})",
        )

    def _get_available_krw_balance(self, account: Account) -> Decimal:
        """사용 가능한 KRW 잔액 조회"""
        for balance in account.balances:
            if balance.currency == Currency.KRW:
                return balance.balance - balance.locked
        return Decimal("0")

    def _get_target_currency_balance(
        self, account: Account, market: str
    ) -> Balance | None:
        """대상 통화 잔액 조회"""
        # 마켓에서 대상 통화 추출 (예: KRW-BTC -> BTC)
        target_currency = market.split("-")[1]
        currency = Currency(target_currency)

        for balance in account.balances:
            if balance.currency == currency:
                return balance
        return None
