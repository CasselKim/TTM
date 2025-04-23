from decimal import Decimal
from typing import Dict, Any, List
from app.domain.models.account import Account, Balance, Currency
from app.domain.repositories.account_repository import AccountRepository
from ..upbit.client import UpbitClient
from ..upbit.exceptions import UpbitAPIException

class UpbitAdapter(AccountRepository):
    def __init__(self, access_key: str, secret_key: str):
        self.client = UpbitClient(access_key=access_key, secret_key=secret_key)
    async def get_account_balance(self) -> Account:
        """계좌 잔액 정보 조회"""
        try:
            response = self.client.get_accounts()
            balances = [
                Balance(
                    currency=Currency(item["currency"]),
                    balance=Decimal(item["balance"]),
                    locked=Decimal(item["locked"]),
                    avg_buy_price=Decimal(item["avg_buy_price"]),
                    unit=Currency(item["unit_currency"])
                )
                for item in response
            ]
            return Account(balances=balances)
        except Exception as e:
            raise UpbitAPIException(f"Failed to get account balance: {str(e)}") 