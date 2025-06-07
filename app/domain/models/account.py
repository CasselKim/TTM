from collections.abc import Iterator
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, field_serializer


class Currency(StrEnum):
    KRW = "KRW"
    BTC = "BTC"
    ETH = "ETH"
    XRP = "XRP"
    DOGE = "DOGE"


class Balance(BaseModel):
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

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

    @property
    def available_balance(self) -> Decimal:
        """사용 가능한 잔액 (전체 잔액 - 잠긴 잔액)"""
        return self.balance - self.locked

    def can_trade(self, amount: Decimal) -> bool:
        """거래 가능 여부 확인"""
        return self.available_balance >= amount

    def lock_amount(self, amount: Decimal) -> Self:
        """금액을 잠금 처리한 새로운 Balance 객체 반환"""
        if amount > self.available_balance:
            raise ValueError(
                f"잠금 금액({amount})이 사용 가능 잔액({self.available_balance})보다 큽니다"
            )

        return self.model_copy(update={"locked": self.locked + amount})

    def unlock_amount(self, amount: Decimal) -> Self:
        """금액을 잠금 해제한 새로운 Balance 객체 반환"""
        if amount > self.locked:
            raise ValueError(
                f"해제 금액({amount})이 잠긴 금액({self.locked})보다 큽니다"
            )

        return self.model_copy(update={"locked": self.locked - amount})


class Account(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    balances: list[Balance]

    def _krw_balances(self) -> Iterator[Balance]:
        return (balance for balance in self.balances if balance.unit == Currency.KRW)

    @property
    def total_balance_krw(self) -> Decimal:
        return sum((b.total_value for b in self._krw_balances()), Decimal("0"))

    def get_balance(self, currency: Currency) -> Balance | None:
        """특정 통화의 잔액 정보 조회"""
        for balance in self.balances:
            if balance.currency == currency:
                return balance
        return None

    def has_currency(self, currency: Currency) -> bool:
        """특정 통화 보유 여부 확인"""
        return self.get_balance(currency) is not None

    def get_available_balance(self, currency: Currency) -> Decimal:
        """특정 통화의 사용 가능한 잔액 조회"""
        balance = self.get_balance(currency)
        return balance.available_balance if balance else Decimal("0")

    def can_buy(self, amount_krw: Decimal) -> bool:
        """KRW로 매수 가능 여부 확인"""
        krw_balance = self.get_balance(Currency.KRW)
        return krw_balance.can_trade(amount_krw) if krw_balance else False

    def can_sell(self, currency: Currency, volume: Decimal) -> bool:
        """특정 통화 매도 가능 여부 확인"""
        balance = self.get_balance(currency)
        return balance.can_trade(volume) if balance else False

    @classmethod
    def from_api_response(cls, data: list[dict[str, Any]]) -> Self:
        """API 응답으로부터 Account 객체 생성"""
        balances = []
        for item in data:
            balance = Balance(
                currency=Currency(item["currency"]),
                balance=Decimal(item["balance"]),
                locked=Decimal(item["locked"]),
                avg_buy_price=Decimal(item["avg_buy_price"]),
                unit=Currency(item["unit_currency"]),
            )
            balances.append(balance)

        return cls(balances=balances)
