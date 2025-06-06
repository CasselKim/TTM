from pydantic import BaseModel


class LimitBuyResult(BaseModel):
    """지정가 매수 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str
    price: str


class MarketBuyResult(BaseModel):
    """시장가 매수 결과"""

    success: bool
    order_uuid: str
    market: str
    amount: str


class LimitSellResult(BaseModel):
    """지정가 매도 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str
    price: str


class MarketSellResult(BaseModel):
    """시장가 매도 결과"""

    success: bool
    order_uuid: str
    market: str
    volume: str


class OrderError(BaseModel):
    """주문 실패"""

    success: bool
    error_message: str
