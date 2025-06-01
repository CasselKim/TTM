"""
라오어의 무한매수법 알고리즘

분할 매수를 통해 평균 단가를 낮추고, 목표 수익률 달성 시 전량 매도하는 투자 전략입니다.

매매 로직:
1. 초기 매수: 설정된 금액으로 첫 매수
2. 추가 매수: 평균 단가 대비 일정 비율 이상 하락 시 추가 매수 (물타기)
3. 익절: 평균 단가 대비 목표 수익률 달성 시 전량 매도
4. 손절: 강제 손절 조건 달성 시 전량 매도
5. 사이클 반복: 매도 후 새로운 사이클 시작
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.constants import AlgorithmConstants
from app.domain.enums import TradingAction
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.infinite_buying import (
    BuyingRound,
    InfiniteBuyingConfig,
    InfiniteBuyingPhase,
    InfiniteBuyingResult,
    InfiniteBuyingState,
)
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.trade_algorithms.base import TradingAlgorithm


class InfiniteBuyingAlgorithm(TradingAlgorithm):
    """
    라오어의 무한매수법 구현

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
        # 상태 초기화 확인
        if not self.state.is_active:
            return await self._analyze_initial_buy_signal(account, market_data)

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
        if await self._should_add_buy(account, market_data):
            return await self._create_add_buy_signal(account, market_data)

        # 홀드
        return TradingSignal(
            action=TradingAction.HOLD,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 대기 중 (평균단가: {self.state.average_price:,.0f}, 현재가: {market_data.current_price:,.0f}, 수익률: {current_profit_rate:.2%})",
        )

    async def calculate_buy_amount(
        self,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
        max_investment_ratio: Decimal,
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
            f"무한매수법 매도 수량 계산: 전량 매도 {available_volume} (평균단가: {self.state.average_price:,.0f})"
        )

        return available_volume

    async def execute_buy(
        self, account: Account, market_data: MarketData, buy_amount: Decimal
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
            )

            # 상태 업데이트
            if not self.state.is_active:
                # 새 사이클 시작
                cycle_id = str(uuid.uuid4())[:8]
                self.state.reset_cycle(market_data.market, cycle_id)

            self.state.add_buying_round(new_round)
            self.state.phase = InfiniteBuyingPhase.ACCUMULATING

            # 목표 매도 가격 업데이트
            self.state.target_sell_price = self.state.average_price * (
                Decimal("1") + self.config.target_profit_rate
            )

            self.logger.info(
                f"무한매수법 {new_round.round_number}회차 매수 완료: "
                f"가격 {current_price:,.0f}원, 금액 {buy_amount:,.0f}원, "
                f"평균단가 {self.state.average_price:,.0f}원, "
                f"목표가 {self.state.target_sell_price:,.0f}원"
            )

            return InfiniteBuyingResult(
                success=True,
                action_taken="buy",
                message=f"{new_round.round_number}회차 매수 완료 (평균단가: {self.state.average_price:,.0f}원)",
                trade_price=current_price,
                trade_amount=buy_amount,
                trade_volume=buy_volume,
                current_state=self.state,
            )

        except Exception as e:
            self.logger.error(f"무한매수법 매수 실행 중 오류: {e}")
            return InfiniteBuyingResult(
                success=False,
                action_taken="buy_failed",
                message=f"매수 실행 실패: {e!s}",
                current_state=self.state,
            )

    async def execute_sell(
        self,
        account: Account,
        market_data: MarketData,
        sell_volume: Decimal,
        is_force_sell: bool = False,
    ) -> InfiniteBuyingResult:
        """
        매도 실행 및 사이클 완료
        """
        try:
            current_price = market_data.current_price
            sell_amount = sell_volume * current_price  # 수수료는 실제 거래에서 적용

            # 수익률 계산 및 사이클 완료
            profit_rate = self.state.complete_cycle(current_price, sell_volume)

            action_type = "force_sell" if is_force_sell else "sell"
            message = (
                f"무한매수법 사이클 완료 ({'손절' if is_force_sell else '익절'}): "
                f"수익률 {profit_rate:.2%}, 매도가 {current_price:,.0f}원"
            )

            self.logger.info(message)

            return InfiniteBuyingResult(
                success=True,
                action_taken=action_type,
                message=message,
                trade_price=current_price,
                trade_amount=sell_amount,
                trade_volume=sell_volume,
                current_state=self.state,
                profit_rate=profit_rate,
            )

        except Exception as e:
            self.logger.error(f"무한매수법 매도 실행 중 오류: {e}")
            return InfiniteBuyingResult(
                success=False,
                action_taken="sell_failed",
                message=f"매도 실행 실패: {e!s}",
                current_state=self.state,
            )

    # Private methods

    async def _analyze_initial_buy_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """초기 매수 신호 분석"""
        available_krw = self._get_available_krw_balance(account)

        if available_krw < self.config.initial_buy_amount:
            return TradingSignal(
                action=TradingAction.HOLD,
                confidence=Decimal("0.5"),
                reason=f"초기 매수 자금 부족 (필요: {self.config.initial_buy_amount:,.0f}원, 보유: {available_krw:,.0f}원)",
            )

        return TradingSignal(
            action=TradingAction.BUY,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 초기 매수 신호 (매수금액: {self.config.initial_buy_amount:,.0f}원)",
        )

    def _calculate_current_profit_rate(self, current_price: Decimal) -> Decimal:
        """현재 수익률 계산"""
        if self.state.average_price == 0:
            return Decimal("0")
        return (current_price - self.state.average_price) / self.state.average_price

    async def _should_force_sell(self, current_profit_rate: Decimal) -> bool:
        """강제 손절 조건 확인"""
        # 손실률이 강제 손절선을 넘었거나
        if current_profit_rate <= self.config.force_stop_loss_rate:
            return True

        # 최대 회차에 도달했거나
        if self.state.current_round >= self.config.max_buy_rounds:
            return True

        # 최대 사이클 기간을 초과한 경우
        if (
            self.state.cycle_start_time
            and datetime.now() - self.state.cycle_start_time
            > timedelta(days=self.config.max_cycle_days)
        ):
            return True

        return False

    async def _should_take_profit(self, current_profit_rate: Decimal) -> bool:
        """익절 조건 확인"""
        return current_profit_rate >= self.config.target_profit_rate

    async def _should_add_buy(self, account: Account, market_data: MarketData) -> bool:
        """추가 매수 조건 확인"""
        # 최대 회차 확인
        if self.state.current_round >= self.config.max_buy_rounds:
            return False

        # 가격 하락률 확인
        if self.state.average_price == 0:
            return False

        price_drop_rate = (
            market_data.current_price - self.state.average_price
        ) / self.state.average_price
        if price_drop_rate > self.config.price_drop_threshold:
            return False

        # 최소 매수 간격 확인
        if (
            self.state.last_buy_time
            and datetime.now() - self.state.last_buy_time
            < timedelta(minutes=self.config.min_buy_interval_minutes)
        ):
            return False

        # 사용 가능한 자금 확인
        available_krw = self._get_available_krw_balance(account)
        if self.state.buying_rounds:
            next_buy_amount = (
                self.state.buying_rounds[-1].buy_amount * self.config.add_buy_multiplier
            )
            if available_krw < next_buy_amount:
                return False

        return True

    def _create_force_sell_signal(self, current_profit_rate: Decimal) -> TradingSignal:
        """강제 손절 신호 생성"""
        return TradingSignal(
            action=TradingAction.SELL,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 강제 손절 (손실률: {current_profit_rate:.2%})",
        )

    def _create_profit_taking_signal(
        self, current_profit_rate: Decimal
    ) -> TradingSignal:
        """익절 신호 생성"""
        return TradingSignal(
            action=TradingAction.SELL,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 목표 수익률 달성 (수익률: {current_profit_rate:.2%})",
        )

    async def _create_add_buy_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """추가 매수 신호 생성"""
        drop_rate = (
            market_data.current_price - self.state.average_price
        ) / self.state.average_price
        return TradingSignal(
            action=TradingAction.BUY,
            confidence=AlgorithmConstants.MAX_CONFIDENCE,
            reason=f"무한매수법 {self.state.current_round + 1}회차 추가 매수 (하락률: {drop_rate:.2%})",
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
        # market 형식: "KRW-BTC" -> target_currency는 "BTC"
        target_currency_str = market.split("-")[1]
        target_currency = Currency(target_currency_str)

        for balance in account.balances:
            if balance.currency == target_currency:
                return balance
        return None
