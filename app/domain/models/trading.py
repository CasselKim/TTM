"""
매매 관련 Value Object 정의

매매 설정, 시장 데이터, 매매 신호 등의 불변 값 객체들을 정의합니다.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.domain.enums import TradingAction


class MarketData(BaseModel):
    """시장 데이터 (Value Object)"""

    market: str  # "KRW-BTC"
    current_price: Decimal
    volume_24h: Decimal
    change_rate_24h: Decimal


class TradingSignal(BaseModel):
    """거래 신호 (Value Object)"""

    action: TradingAction  # BUY, SELL, HOLD
    confidence: Decimal  # 신뢰도 (0.0 ~ 1.0)
    reason: str  # 신호 발생 이유
    suggested_amount: Decimal | None = None  # 제안 거래량
