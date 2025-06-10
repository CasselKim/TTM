"""
도메인 전체에서 사용되는 공통 타입 정의
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, field_serializer

if TYPE_CHECKING:
    pass

from app.domain.models.dca import (
    DcaPhase,
    DcaResult,
    DcaState,
)


# StrEnum 정의들
class DcaStatus(StrEnum):
    """DCA 실행 상태"""

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
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXECUTE = "execute"


# 타입 별칭들
MarketName = str
AlgorithmInstance = "DcaService"


class TradeStatistics(BaseModel):
    """거래 통계"""

    model_config = ConfigDict(
        frozen=True,  # 불변 객체로 설정
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    total_cycles: int
    success_cycles: int
    total_profit: Decimal
    total_profit_rate: Decimal
    average_profit_rate: Decimal
    best_profit_rate: Decimal
    worst_profit_rate: Decimal
    last_updated: datetime

    @field_serializer(
        "total_profit",
        "total_profit_rate",
        "average_profit_rate",
        "best_profit_rate",
        "worst_profit_rate",
    )
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("last_updated")
    def serialize_datetime(self, dt: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat()

    def update_with_result(self, result: DcaResult) -> Self:
        """결과를 반영한 새로운 통계 객체 반환"""
        updates = {
            "total_cycles": self.total_cycles + 1,
            "last_updated": datetime.now(),
        }

        if result.success and result.profit_rate is not None:
            # 성공한 경우 통계 업데이트
            if result.profit_rate > 0:
                updates["success_cycles"] = self.success_cycles + 1

            updates["total_profit"] = self.total_profit + result.profit_rate
            updates["total_profit_rate"] = self.total_profit_rate + result.profit_rate

            # 최고/최저 수익률 업데이트
            updates["best_profit_rate"] = max(self.best_profit_rate, result.profit_rate)
            if (
                result.profit_rate < self.worst_profit_rate
                or self.worst_profit_rate == 0
            ):
                updates["worst_profit_rate"] = result.profit_rate

            # 평균 수익률 재계산
            total_cycles = updates["total_cycles"]
            if isinstance(total_cycles, int) and total_cycles > 0:
                total_profit_rate = updates.get(
                    "total_profit_rate", self.total_profit_rate
                )
                if isinstance(total_profit_rate, Decimal):
                    updates["average_profit_rate"] = total_profit_rate / Decimal(
                        total_cycles
                    )

        return self.model_copy(update=updates)

    @classmethod
    def create_empty(cls) -> Self:
        """빈 통계 객체 생성"""
        return cls(
            total_cycles=0,
            success_cycles=0,
            total_profit=Decimal("0"),
            total_profit_rate=Decimal("0"),
            average_profit_rate=Decimal("0"),
            best_profit_rate=Decimal("0"),
            worst_profit_rate=Decimal("0"),
            last_updated=datetime.now(),
        )

    @classmethod
    def from_cache_json(cls, json_str: str) -> Self:
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json()


class BuyingRoundInfo(BaseModel):
    """매수 회차 정보"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    round_number: int
    buy_price: Decimal
    buy_amount: Decimal
    buy_volume: Decimal
    timestamp: datetime

    @field_serializer("buy_price", "buy_amount", "buy_volume")
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat()


class CycleHistoryItem(BaseModel):
    """사이클 히스토리 항목"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

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

    @field_serializer("total_investment", "total_volume", "average_price")
    def serialize_decimal_required(self, value: Decimal) -> float:
        """필수 Decimal 필드를 float로 직렬화"""
        return float(value)

    @field_serializer("sell_price", "profit_rate")
    def serialize_decimal_optional(self, value: Decimal | None) -> float | None:
        """선택적 Decimal 필드를 float로 직렬화"""
        return float(value) if value is not None else None

    @field_serializer("start_time", "end_time")
    def serialize_datetime(self, dt: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat()

    @classmethod
    def from_state_and_result(
        cls,
        state: "DcaState",
        result: DcaResult,
        end_time: datetime,
        status: CycleStatus,
    ) -> Self:
        """상태와 결과로부터 히스토리 항목 생성"""
        return cls(
            cycle_id=state.cycle_id,
            market=state.market,
            start_time=state.cycle_start_time or datetime.now(),
            end_time=end_time,
            status=status,
            total_investment=state.total_investment,
            total_volume=state.total_volume,
            average_price=state.average_price,
            sell_price=result.trade_price if result.success else None,
            profit_rate=result.profit_rate,
            max_rounds=len(state.buying_rounds),
            actual_rounds=state.current_round,
        )

    @classmethod
    def from_cache_json(cls, json_str: str) -> Self:
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)


class DcaMarketStatus(BaseModel):
    """특정 마켓의 DCA 상태"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    market: MarketName
    status: DcaStatus
    phase: DcaPhase
    cycle_id: str | None
    current_round: int
    total_investment: Decimal
    total_volume: Decimal
    average_price: Decimal
    target_sell_price: Decimal
    last_buy_price: Decimal
    last_buy_time: datetime | None
    cycle_start_time: datetime | None

    # 실시간 수익률 정보 추가
    current_price: Decimal | None = None  # 현재가
    current_profit_rate: Decimal | None = None  # 현재 수익률 (%)
    current_value: Decimal | None = None  # 현재 평가금액 (보유수량 × 현재가)
    profit_loss_amount: Decimal | None = (
        None  # 수익/손실 금액 (현재평가금액 - 총투자금액)
    )

    buying_rounds: list[BuyingRoundInfo]
    statistics: TradeStatistics | None
    recent_history: list[CycleHistoryItem]

    @field_serializer(
        "total_investment",
        "total_volume",
        "average_price",
        "target_sell_price",
        "last_buy_price",
        "current_price",
        "current_profit_rate",
        "current_value",
        "profit_loss_amount",
    )
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Decimal을 float로 직렬화"""
        return float(value) if value is not None else None

    @field_serializer("last_buy_time", "cycle_start_time")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat() if dt else None


class DcaOverallStatus(BaseModel):
    """DCA 전체 상태"""

    model_config = ConfigDict(validate_assignment=True)

    total_active_markets: int
    active_markets: list[MarketName]
    statuses: dict[MarketName, DcaMarketStatus]
