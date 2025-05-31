import logging
from datetime import datetime
from decimal import Decimal

from app.adapters.secondary.discord.adapter import DiscordAdapter
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
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository

logger = logging.getLogger(__name__)


class OrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
        discord_adapter: DiscordAdapter | None = None,
    ):
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.discord_adapter = discord_adapter

    async def _send_trade_notification(
        self,
        market: str,
        side: str,
        price: Decimal | None = None,
        volume: Decimal | None = None,
        amount: Decimal | None = None,
    ) -> None:
        """거래 체결 알림을 Discord로 전송합니다."""
        if not self.discord_adapter:
            return

        try:
            # 실제 거래 정보를 조회하거나 추정
            # 시장가의 경우 실제 체결 가격은 나중에 확인 가능
            if price and volume:
                total_price = price * volume
            elif amount:
                total_price = amount
            else:
                total_price = Decimal("0")

            # 수수료 계산 (상수 사용)
            fee = total_price * TradingConstants.UPBIT_TRADING_FEE_RATE

            await self.discord_adapter.send_trade_notification(
                market=market,
                side=side,
                price=float(price) if price else 0,
                volume=float(volume) if volume else 0,
                total_price=float(total_price),
                fee=float(fee),
                executed_at=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            # Discord 알림 실패는 거래에 영향을 주지 않음

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
                side=OrderSide.BID,
                ord_type=OrderType.LIMIT,
                volume=volume,
                price=price,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                # Discord 알림 전송
                await self._send_trade_notification(
                    market=market,
                    side="BUY",
                    price=price,
                    volume=volume,
                )

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
                side=OrderSide.BID,
                ord_type=OrderType.PRICE,  # 시장가 매수
                price=amount,  # 시장가 매수는 price에 매수할 금액을 설정
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                # Discord 알림 전송
                await self._send_trade_notification(
                    market=market,
                    side="BUY",
                    amount=amount,
                )

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
                side=OrderSide.ASK,
                ord_type=OrderType.LIMIT,
                volume=volume,
                price=price,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                # Discord 알림 전송
                await self._send_trade_notification(
                    market=market,
                    side="SELL",
                    price=price,
                    volume=volume,
                )

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
                side=OrderSide.ASK,
                ord_type=OrderType.MARKET,  # 시장가 매도
                volume=volume,
            )

            result = await self.order_repository.place_order(order_request)

            if result.success and result.order:
                # Discord 알림 전송
                await self._send_trade_notification(
                    market=market,
                    side="SELL",
                    volume=volume,
                )

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
