from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from app.domain.enums import OrderSide, OrderType


class OrderState(StrEnum):
    WAIT = "wait"
    WATCH = "watch"
    DONE = "done"
    CANCEL = "cancel"


class Order(BaseModel):
    """주문 정보"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

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

    @field_serializer(
        "price",
        "volume",
        "remaining_volume",
        "reserved_fee",
        "remaining_fee",
        "paid_fee",
        "locked",
        "executed_volume",
    )
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Decimal을 float로 직렬화"""
        return float(value) if value is not None else None

    @property
    def is_completed(self) -> bool:
        """주문 완료 여부"""
        return self.state == OrderState.DONE

    @property
    def is_cancelled(self) -> bool:
        """주문 취소 여부"""
        return self.state == OrderState.CANCEL

    @property
    def is_active(self) -> bool:
        """주문 활성 상태 여부"""
        return self.state in [OrderState.WAIT, OrderState.WATCH]

    @property
    def fill_rate(self) -> Decimal:
        """체결률 계산"""
        if self.volume and self.volume > 0:
            return self.executed_volume / self.volume
        return Decimal("0")

    @property
    def average_price(self) -> Decimal | None:
        """평균 체결가 계산"""
        if self.ord_type == OrderType.MARKET:
            # 시장가 주문의 경우 실제 체결 금액에서 계산
            if self.executed_volume > 0:
                if self.side == OrderSide.BID and self.price:
                    # 매수: price는 총 지불 금액
                    return self.price / self.executed_volume
                elif self.side == OrderSide.ASK and self.price:
                    # 매도: 별도 계산 필요
                    return self.price
        return self.price

    @classmethod
    def from_upbit_api(cls, data: dict[str, Any]) -> "Order":
        """Upbit API 응답을 Order 도메인 모델로 변환합니다."""
        # API 응답 값을 Enum으로 변환
        side_mapping = {"bid": OrderSide.BID, "ask": OrderSide.ASK}

        ord_type_mapping = {
            "limit": OrderType.LIMIT,
            "price": OrderType.PRICE,
            "market": OrderType.MARKET,
        }

        state_mapping = {
            "wait": OrderState.WAIT,
            "watch": OrderState.WATCH,
            "done": OrderState.DONE,
            "cancel": OrderState.CANCEL,
        }

        return cls(
            uuid=data["uuid"],
            side=side_mapping[data["side"]],
            ord_type=ord_type_mapping[data["ord_type"]],
            price=Decimal(str(data["price"])) if data.get("price") else None,
            state=state_mapping[data["state"]],
            market=data["market"],
            created_at=data["created_at"],
            volume=Decimal(str(data["volume"])) if data.get("volume") else None,
            remaining_volume=Decimal(str(data.get("remaining_volume", "0"))),
            reserved_fee=Decimal(str(data.get("reserved_fee", "0"))),
            remaining_fee=Decimal(str(data.get("remaining_fee", "0"))),
            paid_fee=Decimal(str(data.get("paid_fee", "0"))),
            locked=Decimal(str(data.get("locked", "0"))),
            executed_volume=Decimal(str(data.get("executed_volume", "0"))),
            trades_count=data.get("trades_count", 0),
        )


class OrderRequest(BaseModel):
    """주문 요청"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    market: str
    side: OrderSide
    ord_type: OrderType
    volume: Decimal | None = None
    price: Decimal | None = None

    @field_validator("volume", "price", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: Any) -> Decimal | None:
        """문자열이나 float를 Decimal로 변환"""
        if v is None:
            return v
        return Decimal(str(v))

    @field_serializer("volume", "price")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Decimal을 float로 직렬화"""
        return float(value) if value is not None else None

    def validate_request(self) -> tuple[bool, str]:
        """주문 요청 유효성 검증"""
        if self.ord_type == OrderType.LIMIT:
            if self.price is None or self.price <= 0:
                return False, "지정가 주문은 가격이 필요합니다"
            if self.volume is None or self.volume <= 0:
                return False, "지정가 주문은 수량이 필요합니다"
        elif self.ord_type == OrderType.MARKET:
            if self.side == OrderSide.BID:
                if self.price is None or self.price <= 0:
                    return False, "시장가 매수 주문은 총 주문 금액이 필요합니다"
            elif self.volume is None or self.volume <= 0:
                return False, "시장가 매도 주문은 수량이 필요합니다"
        elif self.ord_type == OrderType.PRICE:
            if self.price is None or self.price <= 0:
                return False, "시장가 주문(KRW)은 총 주문 금액이 필요합니다"

        return True, "OK"

    @classmethod
    def create_market_buy(cls, market: str, total_krw: Decimal) -> Self:
        """시장가 매수 주문 생성"""
        return cls(
            market=market, side=OrderSide.BID, ord_type=OrderType.PRICE, price=total_krw
        )

    @classmethod
    def create_market_sell(cls, market: str, volume: Decimal) -> Self:
        """시장가 매도 주문 생성"""
        return cls(
            market=market, side=OrderSide.ASK, ord_type=OrderType.MARKET, volume=volume
        )

    @classmethod
    def create_limit_buy(cls, market: str, price: Decimal, volume: Decimal) -> Self:
        """지정가 매수 주문 생성"""
        return cls(
            market=market,
            side=OrderSide.BID,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

    @classmethod
    def create_limit_sell(cls, market: str, price: Decimal, volume: Decimal) -> Self:
        """지정가 매도 주문 생성"""
        return cls(
            market=market,
            side=OrderSide.ASK,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )


class OrderResult(BaseModel):
    """주문 결과"""

    model_config = ConfigDict(validate_assignment=True)

    success: bool
    order: Order | None = None
    error_message: str | None = None

    @property
    def order_uuid(self) -> str | None:
        """주문 UUID 반환"""
        return self.order.uuid if self.order else None

    @classmethod
    def create_success(cls, order: Order) -> Self:
        """성공 결과 생성"""
        return cls(success=True, order=order)

    @classmethod
    def create_failure(cls, error_message: str) -> Self:
        """실패 결과 생성"""
        return cls(success=False, error_message=error_message)
