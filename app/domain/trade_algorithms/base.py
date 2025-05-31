"""
매매 알고리즘 기본 인터페이스

순수한 알고리즘 로직만을 담당하며, 매매 신호 분석에만 집중합니다.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.models.account import Account
from app.domain.models.trading import MarketData, TradingSignal


class TradingAlgorithm(ABC):
    """
    매매 알고리즘 기본 인터페이스

    순수한 알고리즘 로직만을 담당하며, 외부 의존성 없이
    주어진 데이터를 바탕으로 매매 신호만을 생성합니다.
    """

    @abstractmethod
    async def analyze_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """
        매매 신호 분석

        Args:
            account: 계좌 정보
            market_data: 시장 데이터

        Returns:
            TradingSignal: 매매 신호
        """
        pass

    @abstractmethod
    async def calculate_buy_amount(
        self,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
        max_investment_ratio: Decimal,
        min_order_amount: Decimal,
    ) -> Decimal:
        """
        매수 금액 계산

        Args:
            account: 계좌 정보
            market_data: 시장 데이터
            signal: 매매 신호
            max_investment_ratio: 최대 투자 비율
            min_order_amount: 최소 주문 금액

        Returns:
            Decimal: 매수 금액
        """
        pass

    @abstractmethod
    async def calculate_sell_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매도 수량 계산

        Args:
            account: 계좌 정보
            market_data: 시장 데이터
            signal: 매매 신호

        Returns:
            Decimal: 매도 수량
        """
        pass
