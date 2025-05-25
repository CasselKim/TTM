from dataclasses import dataclass
from decimal import Decimal
import logging

from app.domain.models.order import OrderRequest, OrderResult, OrderSide, OrderType
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository

logger = logging.getLogger(__name__)


@dataclass
class BuyWithAmountDTO:
    """수량 매수 응답 DTO"""
    success: bool
    order_uuid: str | None = None
    market: str | None = None
    volume: str | None = None
    price: str | None = None
    error_message: str | None = None


@dataclass
class BuyWithMoneyDTO:
    """금액 매수 응답 DTO"""
    success: bool
    order_uuid: str | None = None
    market: str | None = None
    amount: str | None = None
    error_message: str | None = None


@dataclass
class SellWithAmountDTO:
    """수량 매도 응답 DTO"""
    success: bool
    order_uuid: str | None = None
    market: str | None = None
    volume: str | None = None
    price: str | None = None
    error_message: str | None = None


@dataclass
class SellWithMoneyDTO:
    """시장가 매도 응답 DTO"""
    success: bool
    order_uuid: str | None = None
    market: str | None = None
    volume: str | None = None
    error_message: str | None = None


class OrderUseCase:
    def __init__(self, order_repository: OrderRepository, ticker_repository: TickerRepository):
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository

    async def buy_limit(self, market: str, volume: Decimal, price: Decimal) -> BuyWithAmountDTO:
        """지정가 매수를 실행합니다.
        
        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매수할 수량
            price: 매수 가격 (지정가)
            
        Returns:
            BuyWithAmountDTO: 매수 결과
        """
        try:
            logger.info(f"Executing limit buy - market: {market}, volume: {volume}, price: {price}")
            
            order_request = OrderRequest(
                market=market,
                side=OrderSide.매수,
                ord_type=OrderType.지정가,
                volume=volume,
                price=price
            )
            
            result = await self.order_repository.place_order(order_request)
            
            if result.success and result.order:
                return BuyWithAmountDTO(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume) if result.order.volume else None,
                    price=str(result.order.price) if result.order.price else None
                )
            else:
                return BuyWithAmountDTO(
                    success=False,
                    error_message=result.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to execute limit buy: {str(e)}")
            return BuyWithAmountDTO(
                success=False,
                error_message=str(e)
            )

    async def buy_market(self, market: str, amount: Decimal) -> BuyWithMoneyDTO:
        """시장가 매수를 실행합니다.
        
        Args:
            market: 마켓 코드 (ex. "KRW-BTC") 
            amount: 매수할 금액
            
        Returns:
            BuyWithMoneyDTO: 매수 결과
        """
        try:
            logger.info(f"Executing market buy - market: {market}, amount: {amount}")
            
            order_request = OrderRequest(
                market=market,
                side=OrderSide.매수,
                ord_type=OrderType.시장가매수,  # 시장가 매수
                price=amount  # 시장가 매수는 price에 매수할 금액을 설정
            )
            
            result = await self.order_repository.place_order(order_request)
            
            if result.success and result.order:
                return BuyWithMoneyDTO(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    amount=str(amount)
                )
            else:
                return BuyWithMoneyDTO(
                    success=False,
                    error_message=result.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to execute market buy: {str(e)}")
            return BuyWithMoneyDTO(
                success=False,
                error_message=str(e)
            )

    async def sell_limit(self, market: str, volume: Decimal, price: Decimal) -> SellWithAmountDTO:
        """지정가 매도를 실행합니다.
        
        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매도할 수량
            price: 매도 가격 (지정가)
            
        Returns:
            SellWithAmountDTO: 매도 결과
        """
        try:
            logger.info(f"Executing limit sell - market: {market}, volume: {volume}, price: {price}")
            
            order_request = OrderRequest(
                market=market,
                side=OrderSide.매도,
                ord_type=OrderType.지정가,
                volume=volume,
                price=price
            )
            
            result = await self.order_repository.place_order(order_request)
            
            if result.success and result.order:
                return SellWithAmountDTO(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume) if result.order.volume else None,
                    price=str(result.order.price) if result.order.price else None
                )
            else:
                return SellWithAmountDTO(
                    success=False,
                    error_message=result.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to execute limit sell: {str(e)}")
            return SellWithAmountDTO(
                success=False,
                error_message=str(e)
            )

    async def sell_market(self, market: str, volume: Decimal) -> SellWithMoneyDTO:
        """시장가 매도를 실행합니다.
        
        Args:
            market: 마켓 코드 (ex. "KRW-BTC")
            volume: 매도할 수량
            
        Returns:
            SellWithMoneyDTO: 매도 결과
        """
        try:
            logger.info(f"Executing market sell - market: {market}, volume: {volume}")
            
            order_request = OrderRequest(
                market=market,
                side=OrderSide.매도,
                ord_type=OrderType.시장가매도,  # 시장가 매도
                volume=volume
            )
            
            result = await self.order_repository.place_order(order_request)
            
            if result.success and result.order:
                return SellWithMoneyDTO(
                    success=True,
                    order_uuid=result.order.uuid,
                    market=result.order.market,
                    volume=str(result.order.volume) if result.order.volume else None
                )
            else:
                return SellWithMoneyDTO(
                    success=False,
                    error_message=result.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to execute market sell: {str(e)}")
            return SellWithMoneyDTO(
                success=False,
                error_message=str(e)
            ) 