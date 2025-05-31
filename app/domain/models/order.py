from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.enums import OrderSide, OrderType


class OrderState(StrEnum):
    대기 = "wait"
    예약대기 = "watch"
    완료 = "done"
    취소 = "cancel"


@dataclass
class Order:
    """주문 정보"""

    uuid: str
    side: OrderSide
    ord_type: OrderType
    price: Decimal | None
    state: OrderState
    market: str
    created_at: str
    volume: Decimal | None
    remaining_volume: Decimal
    reserved_fee: Decimal
    remaining_fee: Decimal
    paid_fee: Decimal
    locked: Decimal
    executed_volume: Decimal
    trades_count: int


@dataclass
class OrderRequest:
    """주문 요청"""

    market: str
    side: OrderSide
    ord_type: OrderType
    volume: Decimal | None = None
    price: Decimal | None = None


@dataclass
class OrderResult:
    """주문 결과"""

    success: bool
    order: Order | None = None
    error_message: str | None = None
