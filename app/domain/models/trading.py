"""
매매 관련 Value Object 정의

매매 설정, 시장 데이터, 매매 신호 등의 불변 값 객체들을 정의합니다.
"""

from decimal import Decimal
from typing import List
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import TradingAction


class MarketData(BaseModel):
    """시장 데이터 (Value Object)"""

    market: str  # "KRW-BTC"
    current_price: Decimal
    volume_24h: Decimal
    change_rate_24h: Decimal


class PriceDataPoint(BaseModel):
    """개별 가격 데이터 포인트"""

    timestamp: datetime
    high: Decimal
    low: Decimal
    close: Decimal

    def to_cache_string(self) -> str:
        """캐시 저장용 문자열로 변환"""
        return f"{self.high},{self.low},{self.close}"

    @classmethod
    def from_cache_string(cls, timestamp: datetime, data: str) -> "PriceDataPoint":
        """캐시 문자열에서 복원"""
        parts = data.split(",")
        return cls(
            timestamp=timestamp,
            high=Decimal(parts[0]),
            low=Decimal(parts[1]),
            close=Decimal(parts[2]),
        )


class PriceHistory(BaseModel):
    """가격 히스토리 (Value Object)"""

    market: str  # "KRW-BTC"
    high_prices: List[Decimal]  # 고가 리스트
    low_prices: List[Decimal]  # 저가 리스트
    close_prices: List[Decimal]  # 종가 리스트
    periods: int  # 기간 수

    def add_price_data(
        self, high: Decimal, low: Decimal, close: Decimal, max_periods: int = 50
    ) -> None:
        """새로운 가격 데이터를 추가합니다."""
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)

        # 최대 기간을 초과하면 오래된 데이터 제거
        if len(self.high_prices) > max_periods:
            self.high_prices.pop(0)
            self.low_prices.pop(0)
            self.close_prices.pop(0)

        self.periods = len(self.close_prices)

    @classmethod
    def create_empty(cls, market: str) -> "PriceHistory":
        """빈 가격 히스토리를 생성합니다."""
        return cls(
            market=market, high_prices=[], low_prices=[], close_prices=[], periods=0
        )

    @classmethod
    def from_price_data_points(
        cls, market: str, data_points: List[PriceDataPoint]
    ) -> "PriceHistory":
        """PriceDataPoint 리스트에서 PriceHistory 생성"""
        # 타임스탬프 순으로 정렬
        sorted_points = sorted(data_points, key=lambda x: x.timestamp)

        return cls(
            market=market,
            high_prices=[point.high for point in sorted_points],
            low_prices=[point.low for point in sorted_points],
            close_prices=[point.close for point in sorted_points],
            periods=len(sorted_points),
        )


class TradingSignal(BaseModel):
    """거래 신호 (Value Object)"""

    action: TradingAction  # BUY, SELL, HOLD
    confidence: Decimal  # 신뢰도 (0.0 ~ 1.0)
    reason: str  # 신호 발생 이유
    suggested_amount: Decimal | None = None  # 제안 거래량
