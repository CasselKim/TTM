from decimal import Decimal
from typing import Dict, Any, List
from app.domain.models.account import Account, Balance, Currency
from app.domain.repositories.account_repository import AccountRepository
from ..upbit.client import UpbitClient
from ..upbit.exceptions import UpbitAPIException

class UpbitAdapter(AccountRepository):
    def __init__(self, access_key: str, secret_key: str):
        self.client = UpbitClient(access_key=access_key, secret_key=secret_key)

    async def get_market_price(self, market: str) -> dict[str, Any]:
        """특정 마켓의 현재가 조회"""
        try:
            response = self.client.get_ticker(markets=market)
            if not response:
                raise UpbitAPIException("No price data available")
            return {
                "market": market,
                "price": response[0]["trade_price"],
                "timestamp": response[0]["timestamp"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to get market price: {str(e)}")

    async def create_market_order(self, market: str, side: str, volume: str) -> dict[str, Any]:
        """시장가 주문 생성"""
        try:
            response = self.client.create_order(
                market=market,
                side=side,
                volume=volume,
                price=None,
                ord_type="market"
            )
            return {
                "order_id": response["uuid"],
                "market": response["market"],
                "status": response["state"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to create market order: {str(e)}")

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """주문 상태 조회"""
        try:
            response = self.client.get_order(uuid=order_id)
            return {
                "order_id": response["uuid"],
                "status": response["state"],
                "executed_volume": response["executed_volume"],
                "remaining_volume": response["remaining_volume"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to get order status: {str(e)}")

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