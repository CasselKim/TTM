from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ChangeType(StrEnum):
    EVEN = "EVEN"  # 보합
    RISE = "RISE"  # 상승
    FALL = "FALL"  # 하락


class MarketState(StrEnum):
    PREVIEW = "PREVIEW"  # 입금지원
    ACTIVE = "ACTIVE"  # 거래지원가능
    DELISTED = "DELISTED"  # 거래지원종료


class MarketWarning(StrEnum):
    NONE = "NONE"  # 해당없음
    CAUTION = "CAUTION"  # 투자유의


@dataclass
class Ticker:
    """종목 현재가 정보"""

    market: str  # 종목 구분 코드 (ex. KRW-BTC)
    trade_price: Decimal  # 현재가
    prev_closing_price: Decimal  # 전일 종가
    change: ChangeType  # 전일 대비 (EVEN/RISE/FALL)
    change_price: Decimal  # 변화액의 절대값
    change_rate: Decimal  # 변화율의 절대값
    signed_change_price: Decimal  # 부호가 있는 변화액
    signed_change_rate: Decimal  # 부호가 있는 변화율
    opening_price: Decimal  # 시가
    high_price: Decimal  # 고가
    low_price: Decimal  # 저가
    trade_volume: Decimal  # 가장 최근 거래량
    acc_trade_price: Decimal  # 누적 거래대금(UTC 0시 기준)
    acc_trade_price_24h: Decimal  # 24시간 누적 거래대금
    acc_trade_volume: Decimal  # 누적 거래량(UTC 0시 기준)
    acc_trade_volume_24h: Decimal  # 24시간 누적 거래량
    highest_52_week_price: Decimal  # 52주 신고가
    highest_52_week_date: str  # 52주 신고가 달성일
    lowest_52_week_price: Decimal  # 52주 신저가
    lowest_52_week_date: str  # 52주 신저가 달성일
    trade_date: str  # 최근 거래 일자(UTC)
    trade_time: str  # 최근 거래 시각(UTC)
    trade_date_kst: str  # 최근 거래 일자(KST)
    trade_time_kst: str  # 최근 거래 시각(KST)
    trade_timestamp: int  # 최근 거래 일시(UTC Unix Timestamp)
    market_state: MarketState  # 거래상태
    market_warning: MarketWarning  # 유의 종목 여부
    timestamp: int  # 타임스탬프(millisecond)
