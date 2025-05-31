"""
매매 관련 Value Object 정의

매매 설정, 시장 데이터, 매매 신호 등의 불변 값 객체들을 정의합니다.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.models.account import Currency
from app.domain.models.enums import TradingMode


@dataclass
class TradingConfig:
    """거래 설정 (Value Object)"""

    mode: TradingMode
    target_currency: Currency  # 거래 대상 통화 (예: BTC, ETH)
    base_currency: Currency = Currency.KRW  # 기준 통화
    max_investment_ratio: Decimal = Decimal("0.1")  # 최대 투자 비율 (10%)
    min_order_amount: Decimal = Decimal("5000")  # 최소 주문 금액 (KRW)
    stop_loss_ratio: Decimal = Decimal("0.05")  # 손절 비율 (5%)
    take_profit_ratio: Decimal = Decimal("0.1")  # 익절 비율 (10%)


@dataclass
class MarketData:
    """시장 데이터 (Value Object)"""

    market: str  # 예: "KRW-BTC"
    current_price: Decimal
    volume_24h: Decimal
    change_rate_24h: Decimal


@dataclass
class TradingSignal:
    """거래 신호 (Value Object)"""

    action: str  # "BUY", "SELL", "HOLD"
    confidence: Decimal  # 신뢰도 (0.0 ~ 1.0)
    reason: str  # 신호 발생 이유
    suggested_amount: Decimal | None = None  # 제안 거래량
