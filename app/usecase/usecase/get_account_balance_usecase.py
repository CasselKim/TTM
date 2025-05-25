from dataclasses import dataclass

from app.domain.repositories.account_repository import AccountRepository


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


class GetAccountBalanceUseCase:
    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def execute(self) -> AccountBalanceDTO:
        account = await self.account_repository.get_account_balance()

        return AccountBalanceDTO(
            balances=[
                BalanceDTO(
                    currency=balance.currency,
                    balance=str(balance.balance),
                    locked=str(balance.locked),
                    avg_buy_price=str(balance.avg_buy_price),
                    unit=balance.unit,
                )
                for balance in account.balances
            ],
            total_balance_krw=str(account.total_balance_krw),
        )
