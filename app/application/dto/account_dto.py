from pydantic import BaseModel


class BalanceDTO(BaseModel):
    currency: str
    balance: str
    locked: str
    avg_buy_price: str
    unit: str


class AccountBalanceDTO(BaseModel):
    balances: list[BalanceDTO]
    total_balance_krw: str
