from dataclasses import dataclass


@dataclass
class BalanceDTO:
    currency: str
    balance: str
    locked: str
    avg_buy_price: str
    unit: str


@dataclass
class AccountBalanceDTO:
    balances: list[BalanceDTO]
    total_balance_krw: str
