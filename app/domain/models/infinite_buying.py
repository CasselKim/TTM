"""
라오어의 무한매수법 관련 도메인 모델

무한매수법은 분할 매수를 통해 평균 단가를 낮추고,
목표 수익률 달성 시 전량 매도하는 투자 전략입니다.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, computed_field

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

    # 기본 매수 설정
    initial_buy_amount: Decimal  # 초기 매수 금액 (KRW)
    add_buy_multiplier: Decimal = Decimal("1.5")  # 추가 매수 배수

    # 수익/손실 기준
    target_profit_rate: Decimal = Decimal("0.10")  # 목표 수익률 (10%)
    price_drop_threshold: Decimal = Decimal("-0.05")  # 추가 매수 트리거 하락률 (-5%)
    force_stop_loss_rate: Decimal = Decimal("-0.30")  # 강제 손절률 (-30%)

    # 리스크 관리
    max_buy_rounds: int = 10  # 최대 매수 회차
    max_investment_ratio: Decimal = Decimal("0.50")  # 전체 자산 대비 최대 투자 비율

    # 시간 관리
    min_buy_interval_minutes: int = 30  # 최소 매수 간격 (분)
    max_cycle_days: int = 30  # 최대 사이클 기간 (일)


class BuyingRound(BaseModel):
    """개별 매수 회차 정보"""

    round_number: int  # 회차 번호 (1부터 시작)
    buy_price: Decimal  # 매수 가격
    buy_amount: Decimal  # 매수 금액 (KRW)
    buy_volume: Decimal  # 매수 수량 (코인)
    timestamp: datetime  # 매수 시점

    @computed_field
    def unit_cost(self) -> Decimal:
        """단위당 비용 (수수료 포함)"""
        if self.buy_volume == 0:
            return Decimal("0")
        return self.buy_amount / self.buy_volume


class InfiniteBuyingState(BaseModel):
    """무한매수법 현재 상태"""

    # 기본 상태
    market: str  # 거래 시장 (예: "KRW-BTC")
    phase: InfiniteBuyingPhase = InfiniteBuyingPhase.INACTIVE
    cycle_id: str = ""  # 사이클 고유 ID

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

    @computed_field
    def is_active(self) -> bool:
        """활성 상태 여부"""
        return self.phase != InfiniteBuyingPhase.INACTIVE

    @computed_field
    def current_profit_rate(self) -> Decimal:
        """현재 수익률 (평균 단가 기준)"""
        if self.average_price == 0:
            return Decimal("0")
        # 현재 가격은 별도로 전달받아야 함
        return Decimal("0")  # 계산은 알고리즘에서 수행

    @computed_field
    def max_loss_rate(self) -> Decimal:
        """최대 손실률 (첫 매수 가격 기준)"""
        if not self.buying_rounds or self.average_price == 0:
            return Decimal("0")

        first_buy_price = self.buying_rounds[0].buy_price
        return (self.average_price - first_buy_price) / first_buy_price

    def add_buying_round(self, buy_round: BuyingRound) -> None:
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

        # 목표 매도 가격 업데이트 (평균 단가 + 목표 수익률)
        # 실제 계산은 설정값이 필요하므로 알고리즘에서 수행

    def reset_cycle(self, market: str, cycle_id: str) -> None:
        """새로운 사이클로 초기화"""
        self.market = market
        self.cycle_id = cycle_id
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


class InfiniteBuyingResult(BaseModel):
    """무한매수법 실행 결과"""

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
