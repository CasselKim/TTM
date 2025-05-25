from abc import ABC, abstractmethod

from app.domain.models.account import Account


class AccountRepository(ABC):
    @abstractmethod
    async def get_account_balance(self) -> Account:
        """계좌 잔액 정보를 조회합니다."""
