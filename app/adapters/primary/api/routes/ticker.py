from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.application.dto.ticker_dto import TickerPriceDTO, TickerPricesDTO
from app.application.usecase.ticker_usecase import TickerUseCase
from app.container import Container

router = APIRouter(prefix="/ticker", tags=["ticker"])


@router.get("/price/{market}", response_model=TickerPriceDTO)
@inject
async def get_ticker_price(
    market: str,
    usecase: TickerUseCase = Depends(Provide[Container.ticker_usecase]),
) -> TickerPriceDTO:
    """
    특정 종목의 현재가 정보를 조회합니다.

    Args:
        market: 종목 코드 (ex. KRW-BTC)

    Returns:
        TickerPriceDTO: 현재가 정보
    """
    return await usecase.get_ticker_price(market)


@router.get("/prices", response_model=TickerPricesDTO)
@inject
async def get_ticker_prices(
    markets: list[str] = Query(
        ..., description="종목 코드 리스트 (ex. KRW-BTC,KRW-ETH)"
    ),
    usecase: TickerUseCase = Depends(Provide[Container.ticker_usecase]),
) -> TickerPricesDTO:
    """
    여러 종목의 현재가 정보를 조회합니다.

    Args:
        markets: 종목 코드 리스트 (ex. ["KRW-BTC", "KRW-ETH"])

    Returns:
        TickerPricesDTO: 현재가 정보 리스트
    """
    return await usecase.get_ticker_prices(markets)
