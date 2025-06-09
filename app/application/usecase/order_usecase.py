import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from app.application.dto.order_dto import (
    LimitBuyResult,
    LimitSellResult,
    MarketBuyResult,
    MarketSellResult,
    OrderError,
)
from app.domain.constants import TradingConstants
from app.domain.enums import OrderSide, OrderType
from app.domain.models.order import OrderRequest
from app.domain.repositories.notification import NotificationRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.types import MarketName

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
        notification_repo: "NotificationRepository",
    ):
        self._order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.notification_repo = notification_repo

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
                f"Executing limit buy - market: {market}, volume: {volume}, "
                f"price: {price}"
            )

            order_request = OrderRequest(
                market=market,
                side=OrderSide.BID,
                ord_type=OrderType.LIMIT,
                volume=volume,
                price=price,
            )

            result = await self._order_repository.place_order(order_request)

            if (
                result.success
                and result.order
                and result.order.price
                and result.order.volume
            ):
                # 거래 성공 알림
                total_price = result.order.price * result.order.volume
                fee = total_price * TradingConstants.UPBIT_TRADING_FEE_RATE
                await self.notification_repo.send_trade_notification(
                    market=result.order.market,
                    side="BUY",
                    price=float(result.order.price),
                    volume=float(result.order.volume),
                    total_price=float(total_price),
                    fee=float(fee),
                    executed_at=datetime.fromisoformat(result.order.created_at),
                )

                return LimitBuyResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                    price=str(result.order.price),
                )
            elif result.success is False:
                # 거래 실패 알림
                await self.notification_repo.send_error_notification(
                    error_type="Limit Buy Failed",
                    error_message=result.error_message or "Unknown error",
                    details=f"Market: {market}, Volume: {volume}, Price: {price}",
                )
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )
            return OrderError(success=False, error_message="Order result is invalid.")

        except Exception as e:
            logger.exception("Failed to execute limit buy")
            await self.notification_repo.send_error_notification(
                error_type="Limit Buy Exception",
                error_message=str(e),
                details=f"Market: {market}, Volume: {volume}, Price: {price}",
            )
            return OrderError(success=False, error_message=str(e))

    async def buy_market(
        self, market: MarketName, amount: Decimal
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
                side=OrderSide.BID,
                ord_type=OrderType.PRICE,  # 시장가 매수
                price=amount,  # 시장가 매수는 price에 매수할 금액을 설정
            )

            result = await self._order_repository.place_order(order_request)

            if result.success and result.order and result.order.price:
                # 거래 성공 알림
                total_price = result.order.price
                fee = total_price * TradingConstants.UPBIT_TRADING_FEE_RATE
                await self.notification_repo.send_trade_notification(
                    market=result.order.market,
                    side="BUY",
                    price=0,  # 시장가는 체결가가 유동적
                    volume=0,  # 시장가는 체결량이 유동적
                    total_price=float(total_price),
                    fee=float(fee),
                    executed_at=datetime.fromisoformat(result.order.created_at),
                )

                return MarketBuyResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    amount=str(amount),
                )
            elif result.success is False:
                # 거래 실패 알림
                await self.notification_repo.send_error_notification(
                    error_type="Market Buy Failed",
                    error_message=result.error_message or "Unknown error",
                    details=f"Market: {market}, Amount: {amount}",
                )
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )
            return OrderError(success=False, error_message="Order result is invalid.")

        except Exception as e:
            logger.exception("Failed to execute market buy")
            await self.notification_repo.send_error_notification(
                error_type="Market Buy Exception",
                error_message=str(e),
                details=f"Market: {market}, Amount: {amount}",
            )
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
                f"Executing limit sell - market: {market}, volume: {volume}, "
                f"price: {price}"
            )
            order_request = OrderRequest(
                market=market,
                side=OrderSide.ASK,
                ord_type=OrderType.LIMIT,
                volume=volume,
                price=price,
            )
            result = await self._order_repository.place_order(order_request)

            if (
                result.success
                and result.order
                and result.order.price
                and result.order.volume
            ):
                total_price = result.order.price * result.order.volume
                fee = total_price * TradingConstants.UPBIT_TRADING_FEE_RATE
                await self.notification_repo.send_trade_notification(
                    market=result.order.market,
                    side="SELL",
                    price=float(result.order.price),
                    volume=float(result.order.volume),
                    total_price=float(total_price),
                    fee=float(fee),
                    executed_at=datetime.fromisoformat(result.order.created_at),
                )
                return LimitSellResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                    price=str(result.order.price),
                )
            elif result.success is False:
                await self.notification_repo.send_error_notification(
                    error_type="Limit Sell Failed",
                    error_message=result.error_message or "Unknown error",
                    details=f"Market: {market}, Volume: {volume}, Price: {price}",
                )
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )
            return OrderError(success=False, error_message="Order result is invalid.")

        except Exception as e:
            logger.exception("Failed to execute limit sell")
            await self.notification_repo.send_error_notification(
                error_type="Limit Sell Exception",
                error_message=str(e),
                details=f"Market: {market}, Volume: {volume}, Price: {price}",
            )
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
                side=OrderSide.ASK,
                ord_type=OrderType.MARKET,  # 시장가 매도
                volume=volume,
            )
            result = await self._order_repository.place_order(order_request)

            if result.success and result.order and result.order.volume:
                await self.notification_repo.send_trade_notification(
                    market=result.order.market,
                    side="SELL",
                    price=0,
                    volume=float(result.order.volume),
                    total_price=0,
                    fee=0,
                    executed_at=datetime.fromisoformat(result.order.created_at),
                )
                return MarketSellResult(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume),
                )
            elif result.success is False:
                await self.notification_repo.send_error_notification(
                    error_type="Market Sell Failed",
                    error_message=result.error_message or "Unknown error",
                    details=f"Market: {market}, Volume: {volume}",
                )
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )
            return OrderError(success=False, error_message="Order result is invalid.")
        except Exception as e:
            logger.exception("Failed to execute market sell")
            await self.notification_repo.send_error_notification(
                error_type="Market Sell Exception",
                error_message=str(e),
                details=f"Market: {market}, Volume: {volume}",
            )
            return OrderError(success=False, error_message=str(e))

    async def get_order(self, uuid: str) -> dict[str, Any] | OrderError:
        """주문 정보를 조회합니다."""
        try:
            logger.info(f"Getting order info for UUID: {uuid}")
            order = await self._order_repository.get_order(uuid)
            return order.model_dump()
        except Exception as e:
            logger.exception(f"Failed to get order {uuid}")
            return OrderError(success=False, error_message=str(e))

    async def cancel_order(self, uuid: str) -> dict[str, Any] | OrderError:
        """주문을 취소합니다.

        Args:
            uuid: 주문 UUID

        Returns:
            dict[str, Any] | OrderError: 취소 결과 또는 에러
        """
        try:
            logger.info(f"Canceling order - uuid: {uuid}")
            result = await self._order_repository.cancel_order(uuid)
            if result.success and result.order:
                # 주문 취소 알림
                await self.notification_repo.send_info_notification(
                    title="주문 취소",
                    message=f"**{result.order.market}** 주문이 취소되었습니다.",
                    fields=[
                        ("주문 UUID", result.order.uuid, False),
                        ("마켓", result.order.market, True),
                        (
                            "주문 유형",
                            "매수" if result.order.side.value == "bid" else "매도",
                            True,
                        ),
                        ("주문 상태", result.order.state.value, True),
                    ],
                )

                return {
                    "success": True,
                    "uuid": result.order.uuid,
                    "market": result.order.market,
                    "side": result.order.side.value,
                    "state": result.order.state.value,
                }
            else:
                return OrderError(
                    success=False, error_message=result.error_message or "Unknown error"
                )
        except Exception as e:
            logger.exception(f"Failed to cancel order {uuid}")
            return OrderError(success=False, error_message=str(e))
