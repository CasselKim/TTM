from collections.abc import Iterator
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_serializer

from app.domain.enums import Currency


class Balance(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    currency: Currency
    balance: Decimal
    locked: Decimal
    avg_buy_price: Decimal
    unit: Currency

    @field_serializer("balance", "locked", "avg_buy_price")
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @property
    def total_value(self) -> Decimal:
        return self.balance * self.avg_buy_price


class Account(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    balances: list[Balance]

    def _krw_balances(self) -> Iterator[Balance]:
        return (balance for balance in self.balances if balance.unit == "KRW")

    @property
    def total_balance_krw(self) -> Decimal:
        return sum((b.total_value for b in self._krw_balances()), Decimal("0"))

    def get_balance(self, currency: Currency) -> Balance | None:
        """특정 통화의 잔액 정보 조회"""
        for balance in self.balances:
            if balance.currency == currency:
                return balance
        return None

    # 추가: 사용 가능한 KRW 잔액 반환
    @property
    def available_krw(self) -> Decimal:
        return self.available_balance("KRW")

    def available_balance(self, currency: Currency) -> Decimal:
        """해당 통화의 사용 가능한 잔액(balance - locked)을 반환"""
        balance = self.get_balance(currency)
        if balance is None:
            return Decimal("0")
        return balance.balance - balance.locked
