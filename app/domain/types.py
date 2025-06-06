"""
도메인 전체에서 사용되는 공통 타입 정의
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from app.domain.models.infinite_buying import InfiniteBuyingPhase


# StrEnum 정의들
class InfiniteBuyingStatus(StrEnum):
    """무한매수법 실행 상태"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class CycleStatus(StrEnum):
    """사이클 상태"""

    COMPLETED = "completed"
    FAILED = "failed"
    FORCE_STOPPED = "force_stopped"


class ActionTaken(StrEnum):
    """수행된 액션"""

    START = "start"
    STOP = "stop"
    FORCE_STOP = "force_stop"
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXECUTE = "execute"
    BUY_FAILED = "buy_failed"
    SELL_FAILED = "sell_failed"


# 타입 별칭들
MarketName = str
AlgorithmInstance = "InfiniteBuyingAlgorithm"


@dataclass
class TradeStatistics:
    """거래 통계"""

    total_cycles: int
    success_cycles: int
    total_profit: Decimal
    total_profit_rate: Decimal
    average_profit_rate: Decimal
    best_profit_rate: Decimal
    worst_profit_rate: Decimal
    last_updated: datetime


@dataclass
class BuyingRoundInfo:
    """매수 회차 정보"""

    round_number: int
    buy_price: Decimal
    buy_amount: Decimal
    buy_volume: Decimal
    timestamp: datetime


@dataclass
class CycleHistoryItem:
    """사이클 히스토리 항목"""

    cycle_id: str
    market: str
    start_time: datetime
    end_time: datetime
    status: CycleStatus
    total_investment: Decimal
    total_volume: Decimal
    average_price: Decimal
    sell_price: Decimal | None
    profit_rate: Decimal | None
    max_rounds: int
    actual_rounds: int


@dataclass
class InfiniteBuyingMarketStatus:
    """특정 마켓의 무한매수법 상태"""

    market: MarketName
    status: InfiniteBuyingStatus
    phase: InfiniteBuyingPhase
    cycle_id: str | None
    current_round: int
    total_investment: Decimal
    total_volume: Decimal
    average_price: Decimal
    target_sell_price: Decimal
    last_buy_price: Decimal
    last_buy_time: datetime | None
    cycle_start_time: datetime | None
    buying_rounds: list[BuyingRoundInfo]
    statistics: TradeStatistics | None
    recent_history: list[CycleHistoryItem]


@dataclass
class InfiniteBuyingOverallStatus:
    """무한매수법 전체 상태"""

    total_active_markets: int
    active_markets: list[MarketName]
    statuses: dict[MarketName, InfiniteBuyingMarketStatus]
