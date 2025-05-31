from decimal import Decimal

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.application.dto.order_dto import (
    LimitBuyResult,
    LimitSellResult,
    MarketBuyResult,
    MarketSellResult,
    OrderError,
)
from app.application.usecase.order_usecase import OrderUseCase
from app.container import Container

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/buy/limit", response_model=LimitBuyResult | OrderError)
@inject
async def buy_limit(
    market: str,
    volume: float,
    price: float,
    order_usecase: OrderUseCase = Depends(Provide[Container.order_usecase]),
) -> LimitBuyResult | OrderError:
    """지정가 매수 주문을 실행합니다."""
    return await order_usecase.buy_limit(
        market=market, volume=Decimal(str(volume)), price=Decimal(str(price))
    )


@router.post("/buy/market", response_model=MarketBuyResult | OrderError)
@inject
async def buy_market(
    market: str,
    amount: float,
    order_usecase: OrderUseCase = Depends(Provide[Container.order_usecase]),
) -> MarketBuyResult | OrderError:
    """시장가 매수 주문을 실행합니다."""
    return await order_usecase.buy_market(market=market, amount=Decimal(str(amount)))


@router.post("/sell/limit", response_model=LimitSellResult | OrderError)
@inject
async def sell_limit(
    market: str,
    volume: float,
    price: float,
    order_usecase: OrderUseCase = Depends(Provide[Container.order_usecase]),
) -> LimitSellResult | OrderError:
    """지정가 매도 주문을 실행합니다."""
    return await order_usecase.sell_limit(
        market=market, volume=Decimal(str(volume)), price=Decimal(str(price))
    )


@router.post("/sell/market", response_model=MarketSellResult | OrderError)
@inject
async def sell_market(
    market: str,
    volume: float,
    order_usecase: OrderUseCase = Depends(Provide[Container.order_usecase]),
) -> MarketSellResult | OrderError:
    """시장가 매도 주문을 실행합니다."""
    return await order_usecase.sell_market(market=market, volume=Decimal(str(volume)))
