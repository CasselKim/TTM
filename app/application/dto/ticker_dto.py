from dataclasses import dataclass


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
