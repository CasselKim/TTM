from collections.abc import Iterator
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, computed_field


class Currency(StrEnum):
    KRW = "KRW"
    BTC = "BTC"
    ETH = "ETH"
    XRP = "XRP"
    DOGE = "DOGE"


class Balance(BaseModel):
    currency: Currency
    balance: Decimal
    locked: Decimal
    avg_buy_price: Decimal
    unit: Currency

    @computed_field
    def total_value(self) -> Decimal:
        return self.balance * self.avg_buy_price


class Account(BaseModel):
    balances: list[Balance]

    def _krw_balances(self) -> Iterator[Balance]:
        return (balance for balance in self.balances if balance.unit == Currency.KRW)

    @computed_field
    def total_balance_krw(self) -> Decimal:
        return sum((b.total_value() for b in self._krw_balances()), Decimal("0"))
