from dataclasses import dataclass

from app.domain.repositories.ticker_repository import TickerRepository


@dataclass
class TickerPriceDTO:
    """현재가 정보 응답 DTO"""

    market: str
    trade_price: str
    prev_closing_price: str
    change: str
    change_price: str
    change_rate: str
    signed_change_price: str
    signed_change_rate: str
    opening_price: str
    high_price: str
    low_price: str
    trade_volume: str
    acc_trade_price: str
    acc_trade_price_24h: str
    acc_trade_volume: str
    acc_trade_volume_24h: str
    highest_52_week_price: str
    highest_52_week_date: str
    lowest_52_week_price: str
    lowest_52_week_date: str
    trade_date: str
    trade_time: str
    trade_date_kst: str
    trade_time_kst: str
    trade_timestamp: int
    market_state: str
    market_warning: str
    timestamp: int


@dataclass
class TickerPricesDTO:
    """여러 종목 현재가 정보 응답 DTO"""

    tickers: list[TickerPriceDTO]


class GetTickerPriceUseCase:
    def __init__(self, ticker_repository: TickerRepository):
        self.ticker_repository = ticker_repository

    async def execute(self, market: str) -> TickerPriceDTO:
        """특정 종목의 현재가 정보를 조회합니다."""
        ticker = await self.ticker_repository.get_ticker(market)

        return TickerPriceDTO(
            market=ticker.market,
            trade_price=str(ticker.trade_price),
            prev_closing_price=str(ticker.prev_closing_price),
            change=ticker.change.value,
            change_price=str(ticker.change_price),
            change_rate=str(ticker.change_rate),
            signed_change_price=str(ticker.signed_change_price),
            signed_change_rate=str(ticker.signed_change_rate),
            opening_price=str(ticker.opening_price),
            high_price=str(ticker.high_price),
            low_price=str(ticker.low_price),
            trade_volume=str(ticker.trade_volume),
            acc_trade_price=str(ticker.acc_trade_price),
            acc_trade_price_24h=str(ticker.acc_trade_price_24h),
            acc_trade_volume=str(ticker.acc_trade_volume),
            acc_trade_volume_24h=str(ticker.acc_trade_volume_24h),
            highest_52_week_price=str(ticker.highest_52_week_price),
            highest_52_week_date=ticker.highest_52_week_date,
            lowest_52_week_price=str(ticker.lowest_52_week_price),
            lowest_52_week_date=ticker.lowest_52_week_date,
            trade_date=ticker.trade_date,
            trade_time=ticker.trade_time,
            trade_date_kst=ticker.trade_date_kst,
            trade_time_kst=ticker.trade_time_kst,
            trade_timestamp=ticker.trade_timestamp,
            market_state=ticker.market_state.value,
            market_warning=ticker.market_warning.value,
            timestamp=ticker.timestamp,
        )

    async def execute_multiple(self, markets: list[str]) -> TickerPricesDTO:
        """여러 종목의 현재가 정보를 조회합니다."""
        tickers = await self.ticker_repository.get_tickers(markets)

        ticker_dtos = [
            TickerPriceDTO(
                market=ticker.market,
                trade_price=str(ticker.trade_price),
                prev_closing_price=str(ticker.prev_closing_price),
                change=ticker.change.value,
                change_price=str(ticker.change_price),
                change_rate=str(ticker.change_rate),
                signed_change_price=str(ticker.signed_change_price),
                signed_change_rate=str(ticker.signed_change_rate),
                opening_price=str(ticker.opening_price),
                high_price=str(ticker.high_price),
                low_price=str(ticker.low_price),
                trade_volume=str(ticker.trade_volume),
                acc_trade_price=str(ticker.acc_trade_price),
                acc_trade_price_24h=str(ticker.acc_trade_price_24h),
                acc_trade_volume=str(ticker.acc_trade_volume),
                acc_trade_volume_24h=str(ticker.acc_trade_volume_24h),
                highest_52_week_price=str(ticker.highest_52_week_price),
                highest_52_week_date=ticker.highest_52_week_date,
                lowest_52_week_price=str(ticker.lowest_52_week_price),
                lowest_52_week_date=ticker.lowest_52_week_date,
                trade_date=ticker.trade_date,
                trade_time=ticker.trade_time,
                trade_date_kst=ticker.trade_date_kst,
                trade_time_kst=ticker.trade_time_kst,
                trade_timestamp=ticker.trade_timestamp,
                market_state=ticker.market_state.value,
                market_warning=ticker.market_warning.value,
                timestamp=ticker.timestamp,
            )
            for ticker in tickers
        ]

        return TickerPricesDTO(tickers=ticker_dtos)
