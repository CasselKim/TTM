import logging
from decimal import Decimal

from app.adapters.external.upbit.client import UpbitClient
from app.adapters.external.upbit.exceptions import UpbitAPIException
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.order import Order, OrderRequest, OrderResult
from app.domain.models.ticker import Ticker
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository

logger = logging.getLogger(__name__)


class UpbitAdapter(AccountRepository, TickerRepository, OrderRepository):
    def __init__(self, access_key: str, secret_key: str):
        self.client = UpbitClient(access_key=access_key, secret_key=secret_key)

    # AccountRepository 구현
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
                    unit=Currency(item["unit_currency"]),
                )
                for item in response
            ]
            return Account(balances=balances)
        except Exception as e:
            logger.exception(f"Failed to get account balance: {e!s}")
            raise UpbitAPIException(f"Failed to get account balance: {e!s}")

    # TickerRepository 구현
    async def get_ticker(self, market: str) -> Ticker:
        """특정 종목의 현재가 정보를 조회합니다."""
        try:
            response = self.client.get_ticker(market)
            if not response:
                raise UpbitAPIException(f"No ticker data found for market: {market}")

            ticker_data = response[0]  # 단일 종목이므로 첫 번째 요소
            return Ticker.from_upbit_api(ticker_data)
        except Exception as e:
            logger.exception(f"Failed to get ticker for {market}: {e!s}")
            raise UpbitAPIException(f"Failed to get ticker for {market}: {e!s}")

    async def get_tickers(self, markets: list[str]) -> list[Ticker]:
        """여러 종목의 현재가 정보를 조회합니다."""
        try:
            markets_str = ",".join(markets)
            response = self.client.get_ticker(markets_str)

            return [Ticker.from_upbit_api(ticker_data) for ticker_data in response]
        except Exception as e:
            logger.exception(f"Failed to get tickers for {markets}: {e!s}")
            raise UpbitAPIException(f"Failed to get tickers for {markets}: {e!s}")

    # OrderRepository 구현
    async def place_order(self, order_request: OrderRequest) -> OrderResult:
        """주문을 실행합니다."""
        try:
            volume_str = str(order_request.volume) if order_request.volume else None
            price_str = str(order_request.price) if order_request.price else None

            response = self.client.place_order(
                market=order_request.market,
                side=order_request.side.value,
                ord_type=order_request.ord_type.value,
                volume=volume_str,
                price=price_str,
            )

            order = Order.from_upbit_api(response)
            return OrderResult(success=True, order=order)

        except Exception as e:
            logger.exception(f"Failed to place order: {e!s}")
            return OrderResult(success=False, error_message=str(e))

    async def get_order(self, uuid: str) -> Order:
        """특정 주문 정보를 조회합니다."""
        try:
            response = self.client.get_order(uuid)
            return Order.from_upbit_api(response)
        except Exception as e:
            logger.exception(f"Failed to get order {uuid}: {e!s}")
            raise UpbitAPIException(f"Failed to get order {uuid}: {e!s}")

    async def cancel_order(self, uuid: str) -> OrderResult:
        """주문을 취소합니다."""
        try:
            response = self.client.cancel_order(uuid)
            order = Order.from_upbit_api(response)
            return OrderResult(success=True, order=order)
        except Exception as e:
            logger.exception(f"Failed to cancel order {uuid}: {e!s}")
            return OrderResult(success=False, error_message=str(e))
