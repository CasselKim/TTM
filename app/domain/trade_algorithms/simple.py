"""
간단한 변동률 기반 매매 알고리즘

24시간 변동률을 기준으로 매수/매도 신호를 생성하는 알고리즘입니다.
"""

import logging
from decimal import Decimal

from app.domain.models.account import Account, Balance, Currency
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.trade_algorithms.base import TradingAlgorithm


class SimpleTradingAlgorithm(TradingAlgorithm):
    """
    간단한 변동률 기반 매매 알고리즘

    매매 로직:
    - 24시간 변동률이 -5% 이하면 매수 신호
    - 24시간 변동률이 +10% 이상이면 매도 신호
    - 그 외에는 HOLD
    """

    def __init__(self) -> None:
        self.buy_threshold = Decimal("-0.05")  # -5%
        self.sell_threshold = Decimal("0.10")  # +10%
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """
        변동률 기반 매매 신호 분석
        """
        change_rate = market_data.change_rate_24h

        # 매수 신호: 24시간 변동률이 -5% 이하
        if change_rate <= self.buy_threshold:
            return TradingSignal(
                action="BUY",
                confidence=min(
                    abs(change_rate) / abs(self.buy_threshold), Decimal("1.0")
                ),
                reason=f"24시간 변동률 {change_rate:.2%}로 매수 임계값({self.buy_threshold:.2%}) 이하",
            )

        # 매도 신호: 24시간 변동률이 +10% 이상이고 보유 중인 경우
        elif change_rate >= self.sell_threshold:
            target_balance = self._get_target_currency_balance(
                account, market_data.market
            )
            if target_balance and target_balance.balance > Decimal("0"):
                return TradingSignal(
                    action="SELL",
                    confidence=min(change_rate / self.sell_threshold, Decimal("1.0")),
                    reason=f"24시간 변동률 {change_rate:.2%}로 매도 임계값({self.sell_threshold:.2%}) 이상",
                )

        # HOLD 신호
        return TradingSignal(
            action="HOLD",
            confidence=Decimal("1.0"),
            reason=f"24시간 변동률 {change_rate:.2%}로 매매 조건 미충족",
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
        매수 금액 계산: 사용 가능한 KRW 잔액의 설정된 비율만큼 매수
        """
        available_krw = self._get_available_krw_balance(account)

        # 신뢰도에 따라 투자 비율 조정
        investment_ratio = max_investment_ratio * signal.confidence
        buy_amount = available_krw * investment_ratio

        # 최소 주문 금액 확인
        if buy_amount < min_order_amount:
            return Decimal("0")

        self.logger.info(
            f"매수 금액 계산: 사용가능 KRW {available_krw}, "
            f"투자비율 {investment_ratio:.2%}, 매수금액 {buy_amount}"
        )

        return buy_amount

    async def calculate_sell_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매도 수량 계산: 보유 중인 대상 통화의 전량 매도
        """
        target_balance = self._get_target_currency_balance(account, market_data.market)

        if not target_balance:
            return Decimal("0")

        # 사용 가능한 수량 (locked 제외)
        available_volume = target_balance.balance - target_balance.locked

        # 신뢰도에 따라 매도 비율 조정 (최소 50%)
        sell_ratio = max(Decimal("0.5"), signal.confidence)
        sell_volume = available_volume * sell_ratio

        self.logger.info(
            f"매도 수량 계산: 보유량 {target_balance.balance}, "
            f"사용가능 {available_volume}, 매도비율 {sell_ratio:.2%}, "
            f"매도수량 {sell_volume}"
        )

        return sell_volume

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
