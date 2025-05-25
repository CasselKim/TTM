import logging
from decimal import Decimal

from app.application.dto.order_dto import (
    LimitBuyResult,
    LimitSellResult,
    MarketBuyResult,
    MarketSellResult,
    OrderError,
)
from app.domain.models.order import OrderRequest, OrderSide, OrderType
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository

logger = logging.getLogger(__name__)


class OrderUseCase:
    def __init__(
        self, order_repository: OrderRepository, ticker_repository: TickerRepository
    ):
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository

    async def buy_limit(
        self, market: str, volume: Decimal, price: Decimal
    ) -> LimitBuyResult | OrderError:
        """지정가 매수를 실행합니다.

        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매수할 수량
            price: 매수 가격 (지정가)

        Returns:
            LimitBuyResult | OrderError: 매수 결과
        """
        try:
            logger.info(
                f"Executing limit buy - market: {market}, volume: {volume}, price: {price}"
            )

            order_request = OrderRequest(
                market=market,
                side=OrderSide.매수,
                ord_type=OrderType.지정가,
                volume=volume,
                price=price,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                return LimitBuyResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                    price=str(result.order.price),
                )
            else:
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )

        except Exception as e:
            logger.error(f"Failed to execute limit buy: {e!s}")
            return OrderError(success=False, error_message=str(e))

    async def buy_market(
        self, market: str, amount: Decimal
    ) -> MarketBuyResult | OrderError:
        """시장가 매수를 실행합니다.

        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            amount: 매수할 금액

        Returns:
            MarketBuyResult | OrderError: 매수 결과
        """
        try:
            logger.info(f"Executing market buy - market: {market}, amount: {amount}")

            order_request = OrderRequest(
                market=market,
                side=OrderSide.매수,
                ord_type=OrderType.시장가매수,  # 시장가 매수
                price=amount,  # 시장가 매수는 price에 매수할 금액을 설정
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                return MarketBuyResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    amount=str(amount),
                )
            else:
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )

        except Exception as e:
            logger.error(f"Failed to execute market buy: {e!s}")
            return OrderError(success=False, error_message=str(e))

    async def sell_limit(
        self, market: str, volume: Decimal, price: Decimal
    ) -> LimitSellResult | OrderError:
        """지정가 매도를 실행합니다.

        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매도할 수량
            price: 매도 가격 (지정가)

        Returns:
            LimitSellResult | OrderError: 매도 결과
        """
        try:
            logger.info(
                f"Executing limit sell - market: {market}, volume: {volume}, price: {price}"
            )

            order_request = OrderRequest(
                market=market,
                side=OrderSide.매도,
                ord_type=OrderType.지정가,
                volume=volume,
                price=price,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                return LimitSellResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                    price=str(result.order.price),
                )
            else:
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )

        except Exception as e:
            logger.error(f"Failed to execute limit sell: {e!s}")
            return OrderError(success=False, error_message=str(e))

    async def sell_market(
        self, market: str, volume: Decimal
    ) -> MarketSellResult | OrderError:
        """시장가 매도를 실행합니다.

        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매도할 수량

        Returns:
            MarketSellResult | OrderError: 매도 결과
        """
        try:
            logger.info(f"Executing market sell - market: {market}, volume: {volume}")

            order_request = OrderRequest(
                market=market,
                side=OrderSide.매도,
                ord_type=OrderType.시장가매도,  # 시장가 매도
                volume=volume,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                return MarketSellResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                )
            else:
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )

        except Exception as e:
            logger.error(f"Failed to execute market sell: {e!s}")
            return OrderError(success=False, error_message=str(e))
