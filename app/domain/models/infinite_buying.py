"""
라오어의 무한매수법 관련 도메인 모델

무한매수법은 분할 매수를 통해 평균 단가를 낮추고,
목표 수익률 달성 시 전량 매도하는 투자 전략입니다.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self
import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

from app.domain.exceptions import (
    ForceStopLossError,
    MaxInvestmentRatioError,
    PriceDropThresholdError,
    ProfitRateError,
)

if TYPE_CHECKING:
    from app.domain.types import ActionTaken


class InfiniteBuyingPhase(StrEnum):
    """무한매수법 단계"""

    INACTIVE = "inactive"  # 비활성 상태
    INITIAL_BUY = "initial_buy"  # 초기 매수 단계
    ACCUMULATING = "accumulating"  # 추가 매수(물타기) 단계
    PROFIT_TAKING = "profit_taking"  # 익절 대기 단계
    FORCE_SELLING = "force_selling"  # 강제 손절 단계


class InfiniteBuyingConfig(BaseModel):
    """무한매수법 설정"""

    model_config = ConfigDict(
        validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True
    )

    # 기본 매수 설정
    initial_buy_amount: Decimal  # 초기 매수 금액 (KRW)
    add_buy_multiplier: Decimal = Decimal("1.5")  # 추가 매수 배수

    # 수익/손실 기준
    target_profit_rate: Decimal = Decimal("0.10")  # 목표 수익률 (10%)
    price_drop_threshold: Decimal = Decimal("-0.04")  # 추가 매수 트리거 하락률 (-4%)
    force_stop_loss_rate: Decimal = Decimal("-0.25")  # 강제 손절률 (-25%)

    # 리스크 관리
    max_buy_rounds: int = 8  # 최대 매수 회차
    max_investment_ratio: Decimal = Decimal("0.30")  # 전체 자산 대비 최대 투자 비율

    # 시간 관리
    min_buy_interval_minutes: int = 30  # 최소 매수 간격 (분)
    max_cycle_days: int = 30  # 최대 사이클 기간 (일)

    @field_serializer(
        "initial_buy_amount",
        "add_buy_multiplier",
        "target_profit_rate",
        "price_drop_threshold",
        "force_stop_loss_rate",
        "max_investment_ratio",
    )
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        """설정값 검증"""
        if self.target_profit_rate <= 0:
            raise ProfitRateError()
        if self.price_drop_threshold >= 0:
            raise PriceDropThresholdError()
        if self.force_stop_loss_rate >= 0:
            raise ForceStopLossError()
        if self.max_investment_ratio <= 0 or self.max_investment_ratio > 1:
            raise MaxInvestmentRatioError()
        return self

    @classmethod
    def from_cache_json(cls, json_str: str) -> "InfiniteBuyingConfig":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)

    def calculate_next_buy_amount(self, current_round: int) -> Decimal:
        """다음 매수 금액 계산"""
        if current_round == 0:
            return self.initial_buy_amount
        return self.initial_buy_amount * (self.add_buy_multiplier**current_round)


class BuyingRound(BaseModel):
    """개별 매수 회차 정보"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    round_number: int  # 회차 번호 (1부터 시작)
    buy_price: Decimal  # 매수 가격
    buy_amount: Decimal  # 매수 금액 (KRW)
    buy_volume: Decimal  # 매수 수량 (코인)
    timestamp: datetime  # 매수 시점

    @field_serializer("buy_price", "buy_amount", "buy_volume")
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat()

    @property
    def unit_cost(self) -> Decimal:
        """단위당 비용 (수수료 포함)"""
        if self.buy_volume == 0:
            return Decimal("0")
        return self.buy_amount / self.buy_volume

    @classmethod
    def from_cache_json(cls, json_str: str) -> "BuyingRound":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json()


class InfiniteBuyingState(BaseModel):
    """무한매수법 현재 상태"""

    model_config = ConfigDict(
        validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True
    )

    # 기본 상태
    market: str  # 거래 시장 (예: "KRW-BTC")
    phase: InfiniteBuyingPhase = InfiniteBuyingPhase.INACTIVE
    cycle_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])

    # 매수 정보
    current_round: int = 0  # 현재 매수 회차
    total_investment: Decimal = Decimal("0")  # 총 투자 금액
    total_volume: Decimal = Decimal("0")  # 총 보유 수량
    average_price: Decimal = Decimal("0")  # 평균 매수 단가

    # 최근 거래 정보
    last_buy_price: Decimal = Decimal("0")  # 마지막 매수 가격
    last_buy_time: datetime | None = None  # 마지막 매수 시점

    # 사이클 정보
    cycle_start_time: datetime | None = None  # 사이클 시작 시점
    target_sell_price: Decimal = Decimal("0")  # 목표 매도 가격

    # 매수 히스토리
    buying_rounds: list[BuyingRound] = Field(default_factory=list)  # 매수 회차별 정보

    @field_serializer(
        "total_investment",
        "total_volume",
        "average_price",
        "last_buy_price",
        "target_sell_price",
    )
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("last_buy_time", "cycle_start_time")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat() if dt else None

    @property
    def is_active(self) -> bool:
        """활성 상태 여부"""
        return self.phase != InfiniteBuyingPhase.INACTIVE

    def calculate_current_profit_rate(self, current_price: Decimal) -> Decimal:
        """현재 수익률 계산 (평균 단가 기준)"""
        if self.average_price == 0:
            return Decimal("0")
        return (current_price - self.average_price) / self.average_price

    @property
    def max_loss_rate(self) -> Decimal:
        """최대 손실률 (첫 매수 가격 기준)"""
        if not self.buying_rounds or self.average_price == 0:
            return Decimal("0")

        first_buy_price = self.buying_rounds[0].buy_price
        return (self.average_price - first_buy_price) / first_buy_price

    def add_buying_round(
        self, buy_round: BuyingRound, config: InfiniteBuyingConfig
    ) -> None:
        """매수 회차 추가 및 상태 업데이트"""
        self.buying_rounds.append(buy_round)
        self.current_round = buy_round.round_number
        self.last_buy_price = buy_round.buy_price
        self.last_buy_time = buy_round.timestamp

        # 총 투자 금액 및 수량 업데이트
        self.total_investment += buy_round.buy_amount
        self.total_volume += buy_round.buy_volume

        # 평균 단가 재계산
        if self.total_volume > 0:
            self.average_price = self.total_investment / self.total_volume

        # 목표 매도 가격 업데이트
        self.target_sell_price = self.average_price * (1 + config.target_profit_rate)

        # 단계 업데이트
        if self.phase == InfiniteBuyingPhase.INITIAL_BUY:
            self.phase = InfiniteBuyingPhase.ACCUMULATING

    def can_buy_more(
        self, config: InfiniteBuyingConfig, current_time: datetime
    ) -> tuple[bool, str]:
        """추가 매수 가능 여부 확인"""
        if not self.is_active:
            return False, "비활성 상태입니다"

        if self.current_round >= config.max_buy_rounds:
            return False, f"최대 매수 회차({config.max_buy_rounds})에 도달했습니다"

        if self.last_buy_time:
            time_diff = (current_time - self.last_buy_time).total_seconds() / 60
            if time_diff < config.min_buy_interval_minutes:
                return (
                    False,
                    f"최소 매수 간격({config.min_buy_interval_minutes}분)이 "
                    "지나지 않았습니다",
                )

        return True, "추가 매수 가능"

    def should_force_sell(
        self, current_price: Decimal, config: InfiniteBuyingConfig
    ) -> bool:
        """강제 매도 여부 확인"""
        if not self.is_active or self.average_price == 0:
            return False

        profit_rate = self.calculate_current_profit_rate(current_price)
        return profit_rate <= config.force_stop_loss_rate

    def should_take_profit(self, current_price: Decimal) -> bool:
        """익절 여부 확인"""
        if not self.is_active or self.target_sell_price == 0:
            return False

        return current_price >= self.target_sell_price

    def reset_cycle(self, market: str) -> None:
        """새로운 사이클로 초기화"""
        self.market = market
        self.cycle_id = str(uuid.uuid4())[:8]
        self.phase = InfiniteBuyingPhase.INITIAL_BUY
        self.current_round = 0
        self.total_investment = Decimal("0")
        self.total_volume = Decimal("0")
        self.average_price = Decimal("0")
        self.last_buy_price = Decimal("0")
        self.last_buy_time = None
        self.cycle_start_time = datetime.now()
        self.target_sell_price = Decimal("0")
        self.buying_rounds = []

    def complete_cycle(self, sell_price: Decimal, sell_volume: Decimal) -> Decimal:
        """사이클 완료 및 수익률 계산"""
        if self.total_investment == 0:
            return Decimal("0")

        # 총 매도 금액 계산 (수수료는 별도 계산)
        total_sell_amount = sell_price * sell_volume

        # 수익률 계산
        profit_rate = (
            total_sell_amount - self.total_investment
        ) / self.total_investment

        # 상태 초기화
        self.phase = InfiniteBuyingPhase.INACTIVE

        return profit_rate

    @classmethod
    def from_cache_json(cls, json_str: str) -> "InfiniteBuyingState":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)

    def copy_with_updates(self, **kwargs: Any) -> "InfiniteBuyingState":
        """업데이트된 복사본 생성"""
        return self.model_copy(update=kwargs)


class InfiniteBuyingResult(BaseModel):
    """무한매수법 실행 결과"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    success: bool  # 실행 성공 여부
    action_taken: "ActionTaken"  # 수행된 액션
    message: str  # 결과 메시지

    # 거래 정보 (실제 거래가 발생한 경우)
    trade_price: Decimal | None = None
    trade_amount: Decimal | None = None
    trade_volume: Decimal | None = None

    # 상태 정보
    current_state: InfiniteBuyingState | None = None
    profit_rate: Decimal | None = None

    @field_serializer("trade_price", "trade_amount", "trade_volume", "profit_rate")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Decimal을 float로 직렬화"""
        return float(value) if value is not None else None

    @classmethod
    def from_cache_json(cls, json_str: str) -> "InfiniteBuyingResult":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)


# Forward reference 해결을 위한 model rebuild
# ActionTaken이 정의된 후에 호출해야 함
def rebuild_models() -> None:
    """Pydantic v2 forward reference 해결을 위한 model rebuild"""
    from app.domain.types import ActionTaken  # noqa: F401

    InfiniteBuyingResult.model_rebuild()
