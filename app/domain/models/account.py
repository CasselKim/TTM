from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import List, Iterator


class Currency(StrEnum):
    KRW = "KRW"
    BTC = "BTC"
    ETH = "ETH"
    XRP = "XRP"
    DOGE = "DOGE"


@dataclass
class Balance:
    currency: Currency
    balance: Decimal
    locked: Decimal
    avg_buy_price: Decimal
    unit: Currency

    @property
    def total_value(self) -> Decimal:
        return self.balance * self.avg_buy_price


@dataclass
class Account:
    balances: list[Balance]

    def _krw_balances(self) -> Iterator[Balance]:
        return (
            balance for balance in self.balances 
            if balance.unit == Currency.KRW
        )

    @property
    def total_balance_krw(self) -> Decimal:
        return sum(
            (b.total_value for b in self._krw_balances()),
            Decimal('0')
        )