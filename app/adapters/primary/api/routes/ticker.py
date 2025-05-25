from fastapi import APIRouter, Depends, Query
from dependency_injector.wiring import inject, Provide
from app.usecase.usecase.get_ticker_price_usecase import (
    GetTickerPriceUseCase, 
    TickerPriceDTO, 
    TickerPricesDTO
)
from app.container import Container

router = APIRouter(prefix="/ticker", tags=["ticker"])


@router.get("/price/{market}", response_model=TickerPriceDTO)
@inject
async def get_ticker_price(
    market: str,
    usecase: GetTickerPriceUseCase = Depends(Provide[Container.get_ticker_price_usecase])
) -> TickerPriceDTO:
    """
    특정 종목의 현재가 정보를 조회합니다.
    
    Args:
        market: 종목 코드 (ex. KRW-BTC)
    
    Returns:
        TickerPriceDTO: 현재가 정보
    """
    return await usecase.execute(market)


@router.get("/prices", response_model=TickerPricesDTO)
@inject
async def get_ticker_prices(
    markets: list[str] = Query(..., description="종목 코드 리스트 (ex. KRW-BTC,KRW-ETH)"),
    usecase: GetTickerPriceUseCase = Depends(Provide[Container.get_ticker_price_usecase])
) -> TickerPricesDTO:
    """
    여러 종목의 현재가 정보를 조회합니다.
    
    Args:
        markets: 종목 코드 리스트 (ex. ["KRW-BTC", "KRW-ETH"])
    
    Returns:
        TickerPricesDTO: 현재가 정보 리스트
    """
    return await usecase.execute_multiple(markets) 