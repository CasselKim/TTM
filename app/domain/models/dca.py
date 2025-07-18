from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self
import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.domain.exceptions import (
    ForceStopLossError,
    MaxInvestmentRatioError,
    PriceDropThresholdError,
    ProfitRateError,
)
from app.domain.enums import ActionTaken, DcaPhase


class BuyType(StrEnum):
    """매수 타입"""

    INITIAL = "initial"  # 초기 매수
    PRICE_DROP = "price_drop"  # 가격 하락 기반 매수
    TIME_BASED = "time_based"  # 시간 기반 매수


class DcaConfig(BaseModel):
    """DCA 설정"""

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    # 기본 매수 설정
    initial_buy_amount: int = 5000  # 초기 매수 금액 (KRW)
    add_buy_multiplier: Decimal = Decimal("1.5")  # 추가 매수 배수

    # 수익/손실 기준
    target_profit_rate: Decimal = Decimal("0.10")  # 목표 수익률
    price_drop_threshold: Decimal = Decimal("-0.025")  # 추가 매수 트리거 하락률
    force_stop_loss_rate: Decimal = Decimal("-0.25")  # 강제 손절률

    # 리스크 관리
    max_buy_rounds: int = 8  # 최대 매수 회차
    max_investment_ratio: Decimal = Decimal("1")  # 전체 자산 대비 최대 투자 비율

    # 시간 관리
    min_buy_interval_minutes: int = 30  # 최소 매수 간격 (분)
    max_cycle_days: int = 45  # 최대 사이클 기간 (일)

    # 하이브리드 DCA 설정 (시간 단위)
    time_based_buy_interval_hours: int = 72  # 시간 기반 매수 간격 (시간)
    enable_time_based_buying: bool = True  # 시간 기반 매수 활성화

    # SmartDCA 설정
    enable_smart_dca: bool = False  # SmartDCA 활성화 여부
    smart_dca_rho: Decimal = Decimal("1.5")  # SmartDCA ρ 파라미터 (1.0 = 기본 DCA)
    smart_dca_max_multiplier: Decimal = Decimal("5.0")  # SmartDCA 최대 투자 배수
    smart_dca_min_multiplier: Decimal = Decimal("0.1")  # SmartDCA 최소 투자 배수

    # Advanced SmartDCA 설정 (동적 임계값 조정)
    enable_dynamic_thresholds: bool = False  # 동적 임계값 활성화 여부
    va_monthly_growth_rate: Decimal = Decimal(
        "0.01"
    )  # Value Averaging 목표 월간 성장률 (1%)
    price_history_periods: int = 50  # 가격 히스토리 분석 기간
    atr_period: int = 14  # ATR 계산 기간
    rsi_period: int = 14  # RSI 계산 기간
    bollinger_period: int = 20  # 볼린저 밴드 계산 기간
    bollinger_std_dev: Decimal = Decimal("2.0")  # 볼린저 밴드 표준편차 배수

    @field_validator(
        "add_buy_multiplier",
        "target_profit_rate",
        "price_drop_threshold",
        "force_stop_loss_rate",
        "max_investment_ratio",
        "smart_dca_rho",
        "smart_dca_max_multiplier",
        "smart_dca_min_multiplier",
        "va_monthly_growth_rate",
        "bollinger_std_dev",
        mode="before",
    )
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Decimal 필드 역직렬화 처리"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        if isinstance(v, Decimal):
            return v
        raise ValueError(f"Cannot convert {type(v)} to Decimal")

    @field_serializer(
        "target_profit_rate",
        "price_drop_threshold",
        "force_stop_loss_rate",
        "max_investment_ratio",
        "add_buy_multiplier",
        "smart_dca_rho",
        "smart_dca_max_multiplier",
        "smart_dca_min_multiplier",
        "va_monthly_growth_rate",
        "bollinger_std_dev",
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
    def from_cache_json(cls, json_str: str) -> "DcaConfig":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)


class BuyingRound(BaseModel):
    """개별 매수 회차 정보"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    round_number: int  # 회차 번호 (1부터 시작)
    buy_price: Decimal  # 매수 가격
    buy_amount: int  # 매수 금액 (KRW)
    buy_volume: Decimal  # 매수 수량 (코인)
    timestamp: datetime  # 매수 시점
    buy_type: BuyType = BuyType.PRICE_DROP  # 매수 타입
    reason: str | None = None  # 매수 사유 (시간/하락 등)

    @field_validator("buy_price", "buy_volume", mode="before")
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Decimal 필드 역직렬화 처리"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        if isinstance(v, Decimal):
            return v
        raise ValueError(f"Cannot convert {type(v)} to Decimal")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_datetime_field(cls, v: Any) -> datetime:
        """datetime 필드 역직렬화 처리"""
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        if isinstance(v, datetime):
            return v
        raise ValueError(f"Cannot convert {type(v)} to datetime")

    @field_serializer("buy_price", "buy_volume")
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat()


class DcaState(BaseModel):
    """DCA 현재 상태"""

    model_config = ConfigDict(
        validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True
    )

    # 기본 상태
    market: str  # 거래 시장 (예: "KRW-BTC")
    phase: DcaPhase = DcaPhase.INACTIVE
    cycle_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])

    # 매수 정보
    current_round: int = 0  # 현재 매수 회차
    total_investment: int = 0  # 총 투자 금액
    total_volume: Decimal = Decimal("0")  # 총 보유 수량
    average_price: Decimal = Decimal("0")  # 평균 매수 단가

    # 최근 거래 정보
    last_buy_price: Decimal = Decimal("0")  # 마지막 매수 가격
    last_buy_time: datetime | None = None  # 마지막 매수 시점
    last_time_based_buy_time: datetime | None = None  # 마지막 시간 기반 매수 시점

    # 사이클 정보
    cycle_start_time: datetime | None = None  # 사이클 시작 시점
    target_sell_price: Decimal = Decimal("0")  # 목표 매도 가격

    # 매수 히스토리
    buying_rounds: list[BuyingRound] = Field(default_factory=list)  # 매수 회차별 정보

    @field_validator(
        "total_volume",
        "average_price",
        "last_buy_price",
        "target_sell_price",
        mode="before",
    )
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal:
        """Decimal 필드 역직렬화 처리"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        if isinstance(v, Decimal):
            return v
        raise ValueError(f"Cannot convert {type(v)} to Decimal")

    @field_validator(
        "last_buy_time", "cycle_start_time", "last_time_based_buy_time", mode="before"
    )
    @classmethod
    def validate_datetime_fields(cls, v: Any) -> datetime | None:
        """datetime 필드 역직렬화 처리"""
        if v is None:
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        if isinstance(v, datetime):
            return v
        raise ValueError(f"Cannot convert {type(v)} to datetime")

    @field_serializer(
        "total_volume",
        "average_price",
        "last_buy_price",
        "target_sell_price",
    )
    def serialize_decimal(self, value: Decimal) -> float:
        """Decimal을 float로 직렬화"""
        return float(value)

    @field_serializer("last_buy_time", "cycle_start_time", "last_time_based_buy_time")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat() if dt else None

    @property
    def is_active(self) -> bool:
        """DCA가 활성 상태인지 확인"""
        return self.phase != DcaPhase.INACTIVE

    def calculate_current_profit_rate(self, current_price: Decimal) -> Decimal:
        """현재 수익률 계산"""
        if self.average_price == 0:
            return Decimal("0")
        return (current_price - self.average_price) / self.average_price

    def add_buying_round(self, buy_round: BuyingRound, config: DcaConfig) -> None:
        """매수 회차 추가 및 상태 업데이트"""
        self.buying_rounds.append(buy_round)
        self.current_round = len(self.buying_rounds)

        # 투자 금액 및 수량 누적
        self.total_investment += buy_round.buy_amount
        self.total_volume += buy_round.buy_volume

        # 평균 단가 계산
        if self.total_volume > 0:
            self.average_price = Decimal(str(self.total_investment)) / self.total_volume

        # 목표 판매 가격 설정
        self.target_sell_price = self.average_price * (
            Decimal("1") + config.target_profit_rate
        )

        # 최근 매수 정보 업데이트
        self.last_buy_price = buy_round.buy_price
        self.last_buy_time = buy_round.timestamp

        # 시간 기반 매수인 경우 별도 기록
        if buy_round.buy_type == BuyType.TIME_BASED:
            self.last_time_based_buy_time = buy_round.timestamp

    def start_new_cycle(self, market: str) -> None:
        """새 사이클 시작"""
        self.market = market
        self.phase = DcaPhase.INITIAL_BUY
        self.cycle_id = str(uuid.uuid4())[:8]
        self.cycle_start_time = datetime.now()
        self.current_round = 0
        self.total_investment = 0
        self.total_volume = Decimal("0")
        self.average_price = Decimal("0")
        self.last_buy_price = Decimal("0")
        self.last_buy_time = None
        self.last_time_based_buy_time = None
        self.target_sell_price = Decimal("0")
        self.buying_rounds = []

    def complete_cycle(self) -> None:
        """사이클 완료"""
        self.phase = DcaPhase.INACTIVE
        self.current_round = 0
        self.total_investment = 0
        self.total_volume = Decimal("0")
        self.average_price = Decimal("0")
        self.last_buy_price = Decimal("0")
        self.last_buy_time = None
        self.last_time_based_buy_time = None
        self.cycle_start_time = None
        self.target_sell_price = Decimal("0")
        self.buying_rounds = []

    @classmethod
    def from_cache_json(cls, json_str: str) -> "DcaState":
        """캐시 JSON에서 모델 생성"""
        return cls.model_validate_json(json_str)

    def to_cache_json(self) -> str:
        """캐시 저장용 JSON 문자열 반환"""
        return self.model_dump_json(exclude_none=True)


class DcaResult(BaseModel):
    """DCA 실행 결과"""

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    success: bool  # 실행 성공 여부
    action_taken: ActionTaken  # 수행된 액션
    message: str  # 결과 메시지

    # 거래 정보 (실제 거래가 발생한 경우)
    trade_price: Decimal = Decimal("0")
    trade_amount: int = 0
    trade_volume: Decimal = Decimal("0")

    # 상태 정보
    current_state: DcaState | None = None
    profit_rate: Decimal = Decimal("0")
    profit_loss_amount_krw: int = 0

    @field_validator(
        "trade_price",
        "trade_volume",
        "profit_rate",
        "profit_loss_amount_krw",
        mode="before",
    )
    @classmethod
    def validate_decimal_fields(cls, v: Any) -> Decimal | None:
        """Decimal 필드 역직렬화 처리"""
        if v is None:
            return None
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        if isinstance(v, Decimal):
            return v
        raise ValueError(f"Cannot convert {type(v)} to Decimal")

    @field_serializer("trade_price", "trade_volume", "profit_rate")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Decimal을 float로 직렬화"""
        return float(value) if value is not None else None
