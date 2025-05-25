import logging
from decimal import Decimal
from typing import Any

from app.adapters.secondary.upbit.client import UpbitClient
from app.adapters.secondary.upbit.exceptions import UpbitAPIException
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.order import (
    Order,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderState,
    OrderType,
)
from app.domain.models.ticker import ChangeType, MarketState, MarketWarning, Ticker
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
            logger.error(f"Failed to get account balance: {e!s}")
            raise UpbitAPIException(f"Failed to get account balance: {e!s}")

    # TickerRepository 구현
    async def get_ticker(self, market: str) -> Ticker:
        """특정 종목의 현재가 정보를 조회합니다."""
        try:
            response = self.client.get_ticker(market)
            if not response:
                raise UpbitAPIException(f"No ticker data found for market: {market}")

            ticker_data = response[0]  # 단일 종목이므로 첫 번째 요소
            return self._convert_to_ticker(ticker_data)
        except Exception as e:
            logger.error(f"Failed to get ticker for {market}: {e!s}")
            raise UpbitAPIException(f"Failed to get ticker for {market}: {e!s}")

    async def get_tickers(self, markets: list[str]) -> list[Ticker]:
        """여러 종목의 현재가 정보를 조회합니다."""
        try:
            markets_str = ",".join(markets)
            response = self.client.get_ticker(markets_str)

            return [self._convert_to_ticker(ticker_data) for ticker_data in response]
        except Exception as e:
            logger.error(f"Failed to get tickers for {markets}: {e!s}")
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

            order = self._convert_to_order(response)
            return OrderResult(success=True, order=order)

        except Exception as e:
            logger.error(f"Failed to place order: {e!s}")
            return OrderResult(success=False, error_message=str(e))

    async def get_order(self, uuid: str) -> Order:
        """특정 주문 정보를 조회합니다."""
        try:
            response = self.client.get_order(uuid)
            return self._convert_to_order(response)
        except Exception as e:
            logger.error(f"Failed to get order {uuid}: {e!s}")
            raise UpbitAPIException(f"Failed to get order {uuid}: {e!s}")

    async def cancel_order(self, uuid: str) -> OrderResult:
        """주문을 취소합니다."""
        try:
            response = self.client.cancel_order(uuid)
            order = self._convert_to_order(response)
            return OrderResult(success=True, order=order)
        except Exception as e:
            logger.error(f"Failed to cancel order {uuid}: {e!s}")
            return OrderResult(success=False, error_message=str(e))

    def _convert_to_ticker(self, data: dict[str, Any]) -> Ticker:
        """API 응답을 Ticker 도메인 모델로 변환합니다."""
        return Ticker(
            market=data["market"],
            trade_price=Decimal(str(data["trade_price"])),
            prev_closing_price=Decimal(str(data["prev_closing_price"])),
            change=ChangeType(data["change"]),
            change_price=Decimal(str(data["change_price"])),
            change_rate=Decimal(str(data["change_rate"])),
            signed_change_price=Decimal(str(data["signed_change_price"])),
            signed_change_rate=Decimal(str(data["signed_change_rate"])),
            opening_price=Decimal(str(data["opening_price"])),
            high_price=Decimal(str(data["high_price"])),
            low_price=Decimal(str(data["low_price"])),
            trade_volume=Decimal(str(data["trade_volume"])),
            acc_trade_price=Decimal(str(data["acc_trade_price"])),
            acc_trade_price_24h=Decimal(str(data["acc_trade_price_24h"])),
            acc_trade_volume=Decimal(str(data["acc_trade_volume"])),
            acc_trade_volume_24h=Decimal(str(data["acc_trade_volume_24h"])),
            highest_52_week_price=Decimal(str(data["highest_52_week_price"])),
            highest_52_week_date=data["highest_52_week_date"],
            lowest_52_week_price=Decimal(str(data["lowest_52_week_price"])),
            lowest_52_week_date=data["lowest_52_week_date"],
            trade_date=data["trade_date"],
            trade_time=data["trade_time"],
            trade_date_kst=data["trade_date_kst"],
            trade_time_kst=data["trade_time_kst"],
            trade_timestamp=data["trade_timestamp"],
            market_state=MarketState(data.get("market_state", "ACTIVE")),  # 기본값 설정
            market_warning=MarketWarning(
                data.get("market_warning", "NONE")
            ),  # 기본값 설정
            timestamp=data["timestamp"],
        )

    def _convert_to_order(self, data: dict[str, Any]) -> Order:
        """API 응답을 Order 도메인 모델로 변환합니다."""
        # API 응답 값을 한글 Enum으로 변환
        side_mapping = {"bid": OrderSide.매수, "ask": OrderSide.매도}

        ord_type_mapping = {
            "limit": OrderType.지정가,
            "price": OrderType.시장가매수,
            "market": OrderType.시장가매도,
        }

        state_mapping = {
            "wait": OrderState.대기,
            "watch": OrderState.예약대기,
            "done": OrderState.완료,
            "cancel": OrderState.취소,
        }

        return Order(
            uuid=data["uuid"],
            side=side_mapping[data["side"]],
            ord_type=ord_type_mapping[data["ord_type"]],
            price=Decimal(str(data["price"])) if data["price"] else None,
            state=state_mapping[data["state"]],
            market=data["market"],
            created_at=data["created_at"],
            volume=Decimal(str(data["volume"])) if data["volume"] else None,
            remaining_volume=Decimal(str(data["remaining_volume"])),
            reserved_fee=Decimal(str(data["reserved_fee"])),
            remaining_fee=Decimal(str(data["remaining_fee"])),
            paid_fee=Decimal(str(data["paid_fee"])),
            locked=Decimal(str(data["locked"])),
            executed_volume=Decimal(str(data["executed_volume"])),
            trades_count=data["trades_count"],
        )
