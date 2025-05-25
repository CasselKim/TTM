from app.application.dto.account_dto import AccountBalanceDTO, BalanceDTO
from app.domain.repositories.account_repository import AccountRepository


class AccountUseCase:
    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def get_balance(self) -> AccountBalanceDTO:
        """계좌 잔액 정보를 조회합니다."""
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
