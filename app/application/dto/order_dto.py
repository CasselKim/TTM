from dataclasses import dataclass


@dataclass
class LimitBuyResult:
    """지정가 매수 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str
    price: str


@dataclass
class MarketBuyResult:
    """시장가 매수 결과"""

    success: bool
    order_uuid: str
    market: str
    amount: str


@dataclass
class LimitSellResult:
    """지정가 매도 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str
    price: str


@dataclass
class MarketSellResult:
    """시장가 매도 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str


@dataclass
class OrderError:
    """주문 실패"""

    success: bool
    error_message: str
