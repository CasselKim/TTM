"""
라오어의 무한매수법 알고리즘 테스트

무한매수법 알고리즘의 핵심 기능들을 테스트합니다:
- 초기 매수 신호 생성
- 추가 매수 조건 확인
- 익절/손절 조건 확인
- 매수/매도 금액 계산
- 상태 관리
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app.domain.constants import AlgorithmConstants
from app.domain.enums import TradingAction
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.infinite_buying import (
    BuyingRound,
    BuyType,
    InfiniteBuyingConfig,
    InfiniteBuyingPhase,
    InfiniteBuyingState,
)
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.services.infinite_buying_service import InfiniteBuyingService
from app.domain.types import ActionTaken


class TestInfiniteBuyingConfig:
    """InfiniteBuyingConfig 테스트"""

    def test_default_config_creation(self):
        """기본 설정으로 config 생성 테스트"""
        config = InfiniteBuyingConfig(initial_buy_amount=Decimal("100000"))

        assert config.initial_buy_amount == Decimal("100000")
        assert config.add_buy_multiplier == Decimal("1.5")
        assert config.target_profit_rate == Decimal("0.10")
        assert config.price_drop_threshold == Decimal("-0.025")
        assert config.force_stop_loss_rate == Decimal("-0.25")
        assert config.max_buy_rounds == 8
        assert config.max_investment_ratio == Decimal("0.30")
        assert config.min_buy_interval_minutes == 30
        assert config.max_cycle_days == 45
        assert config.time_based_buy_interval_days == 3
        assert config.enable_time_based_buying is True

    def test_custom_config_creation(self):
        """커스텀 설정으로 config 생성 테스트"""
        config = InfiniteBuyingConfig(
            initial_buy_amount=Decimal("50000"),
            add_buy_multiplier=Decimal("2.0"),
            target_profit_rate=Decimal("0.15"),
            max_buy_rounds=5
        )

        assert config.initial_buy_amount == Decimal("50000")
        assert config.add_buy_multiplier == Decimal("2.0")
        assert config.target_profit_rate == Decimal("0.15")
        assert config.max_buy_rounds == 5


class TestInfiniteBuyingState:
    """InfiniteBuyingState 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")

        assert state.market == "KRW-BTC"
        assert state.phase == InfiniteBuyingPhase.INACTIVE
        assert state.current_round == 0
        assert state.total_investment == Decimal("0")
        assert state.total_volume == Decimal("0")
        assert state.average_price == Decimal("0")
        assert not state.is_active
        assert len(state.buying_rounds) == 0

    def test_add_buying_round(self):
        """매수 회차 추가 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")
        config = InfiniteBuyingConfig(initial_buy_amount=Decimal("100000"))

        # 첫 번째 매수 회차 추가
        first_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000000"),
            buy_amount=Decimal("100000"),
            buy_volume=Decimal("0.002"),
            timestamp=datetime.now()
        )

        state.add_buying_round(first_round, config)

        assert state.current_round == 1
        assert state.total_investment == Decimal("100000")
        assert state.total_volume == Decimal("0.002")
        assert state.average_price == Decimal("50000000")
        assert len(state.buying_rounds) == 1

    def test_multiple_buying_rounds(self):
        """여러 매수 회차 추가 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")
        config = InfiniteBuyingConfig(initial_buy_amount=Decimal("100000"))

        # 첫 번째 매수: 5천만원에 10만원
        first_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000000"),
            buy_amount=Decimal("100000"),
            buy_volume=Decimal("0.002"),
            timestamp=datetime.now()
        )
        state.add_buying_round(first_round, config)

        # 두 번째 매수: 4천5백만원에 15만원
        second_round = BuyingRound(
            round_number=2,
            buy_price=Decimal("45000000"),
            buy_amount=Decimal("150000"),
            buy_volume=Decimal("0.00333333"),
            timestamp=datetime.now()
        )
        state.add_buying_round(second_round, config)

        assert state.current_round == 2
        assert state.total_investment == Decimal("250000")
        assert state.total_volume == Decimal("0.00533333")
        # 평균 단가 = 250000 / 0.00533333 ≈ 46875029 (소수점 오차 허용)
        expected_avg_price = state.total_investment / state.total_volume
        assert abs(state.average_price - expected_avg_price) < Decimal("0.01")

    def test_reset_cycle(self):
        """사이클 초기화 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")

        # 일부 데이터 설정
        state.current_round = 3
        state.total_investment = Decimal("500000")
        state.phase = InfiniteBuyingPhase.ACCUMULATING

        # 사이클 초기화
        state.reset_cycle("KRW-ETH")

        assert state.market == "KRW-ETH"
        assert state.cycle_id != ""
        assert state.phase == InfiniteBuyingPhase.INITIAL_BUY
        assert state.current_round == 0
        assert state.total_investment == Decimal("0")
        assert state.total_volume == Decimal("0")
        assert state.average_price == Decimal("0")
        assert len(state.buying_rounds) == 0

    def test_complete_cycle(self):
        """사이클 완료 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")

        # 초기 투자 설정
        state.total_investment = Decimal("250000")

        # 매도 실행 (수익률 20%)
        profit_rate = state.complete_cycle(
            sell_price=Decimal("60000000"),
            sell_volume=Decimal("0.005")
        )

        expected_sell_amount = Decimal("60000000") * Decimal("0.005")  # 300000
        expected_profit_rate = (expected_sell_amount - Decimal("250000")) / Decimal("250000")

        assert profit_rate == expected_profit_rate
        assert state.phase == InfiniteBuyingPhase.INACTIVE


class TestBuyingRound:
    """BuyingRound 테스트"""

    def test_buying_round_creation(self):
        """매수 회차 생성 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000000"),
            buy_amount=Decimal("100000"),
            buy_volume=Decimal("0.002"),
            timestamp=datetime.now()
        )

        assert round_data.round_number == 1
        assert round_data.buy_price == Decimal("50000000")
        assert round_data.buy_amount == Decimal("100000")
        assert round_data.buy_volume == Decimal("0.002")

    def test_unit_cost_calculation(self):
        """단위당 비용 계산 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000000"),
            buy_amount=Decimal("100000"),
            buy_volume=Decimal("0.002"),
            timestamp=datetime.now()
        )

        # unit_cost = buy_amount / buy_volume = 100000 / 0.002 = 50000000
        assert round_data.unit_cost == Decimal("50000000")

    def test_unit_cost_zero_volume(self):
        """볼륨이 0일 때 단위당 비용 계산 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000000"),
            buy_amount=Decimal("100000"),
            buy_volume=Decimal("0"),
            timestamp=datetime.now()
        )

        assert round_data.unit_cost == Decimal("0")


class TestInfiniteBuyingService:
    """InfiniteBuyingService 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 기본 설정"""
        return InfiniteBuyingConfig(
            initial_buy_amount=Decimal("100000"),
            add_buy_multiplier=Decimal("1.5"),
            target_profit_rate=Decimal("0.10"),
            price_drop_threshold=Decimal("-0.05"),
            force_stop_loss_rate=Decimal("-0.30"),
            max_buy_rounds=5,
            min_buy_interval_minutes=1  # 테스트용으로 짧게 설정
        )

    @pytest.fixture
    def algorithm(self, config):
        """테스트용 알고리즘 인스턴스"""
        return InfiniteBuyingService(config)

    @pytest.fixture
    def account(self):
        """테스트용 계좌"""
        return Account(
            balances=[
                Balance(
                    currency=Currency.KRW,
                    balance=Decimal("1000000"),
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("1"),
                    unit=Currency.KRW
                ),
                Balance(
                    currency=Currency.BTC,
                    balance=Decimal("0"),
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("0"),
                    unit=Currency.KRW
                )
            ]
        )

    @pytest.fixture
    def market_data(self):
        """테스트용 시장 데이터"""
        return MarketData(
            market="KRW-BTC",
            current_price=Decimal("50000000"),
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("0.02")
        )

    @pytest.mark.asyncio
    async def test_initial_buy_signal(self, algorithm, account, market_data):
        """초기 매수 신호 테스트"""
        signal = await algorithm.analyze_signal(account, market_data)

        assert signal.action == TradingAction.BUY
        assert signal.confidence == AlgorithmConstants.MAX_CONFIDENCE
        assert "초기 매수 신호" in signal.reason

    @pytest.mark.asyncio
    async def test_initial_buy_insufficient_funds(self, algorithm, market_data):
        """자금 부족 시 초기 매수 신호 테스트"""
        # 자금이 부족한 계좌
        poor_account = Account(
            balances=[
                Balance(
                    currency=Currency.KRW,
                    balance=Decimal("50000"),  # 부족한 금액
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("1"),
                    unit=Currency.KRW
                )
            ]
        )

        signal = await algorithm.analyze_signal(poor_account, market_data)

        assert signal.action == TradingAction.HOLD
        assert "초기 매수 불가" in signal.reason

    @pytest.mark.asyncio
    async def test_buy_amount_calculation(self, algorithm, account, market_data):
        """매수 금액 계산 테스트"""
        signal = TradingSignal(
            action=TradingAction.BUY,
            confidence=Decimal("1.0"),
            reason="테스트"
        )

        buy_amount = await algorithm.calculate_buy_amount(
            account, signal, Decimal("5000")
        )

        assert buy_amount == Decimal("100000")  # initial_buy_amount

    @pytest.mark.asyncio
    async def test_execute_buy(self, algorithm, account, market_data):
        """매수 실행 테스트"""
        result = await algorithm.execute_buy(market_data, Decimal("100000"))

        assert result.success
        assert result.action_taken == ActionTaken.BUY
        assert result.trade_price == Decimal("50000000")
        assert result.trade_amount == Decimal("100000")
        assert algorithm.state.current_round == 1
        assert algorithm.state.phase == InfiniteBuyingPhase.ACCUMULATING

    @pytest.mark.asyncio
    async def test_add_buy_signal_after_price_drop(self, algorithm, account, market_data):
        """가격 하락 후 추가 매수 신호 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"))

        # 가격이 5% 하락한 시장 데이터
        dropped_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("47500000"),  # 5% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.05")
        )

        # 시간 간격 조건을 맞추기 위해 마지막 매수 시간을 과거로 설정
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(minutes=2)

        signal = await algorithm.analyze_signal(account, dropped_market_data)

        assert signal.action == TradingAction.BUY
        assert "가격 하락 기반 추가 매수" in signal.reason

    @pytest.mark.asyncio
    async def test_profit_taking_signal(self, algorithm, account, market_data):
        """익절 신호 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"))

        # 목표 수익률 달성 시장 데이터 (10% 상승)
        profit_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("55000000"),  # 10% 상승
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("0.10")
        )

        signal = await algorithm.analyze_signal(account, profit_market_data)

        assert signal.action == TradingAction.SELL
        assert "목표 수익률 달성" in signal.reason

    @pytest.mark.asyncio
    async def test_force_sell_signal(self, algorithm, account, market_data):
        """강제 손절 신호 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"))

        # 강제 손절 수준 하락 시장 데이터 (30% 하락)
        crash_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("35000000"),  # 30% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.30")
        )

        signal = await algorithm.analyze_signal(account, crash_market_data)

        assert signal.action == TradingAction.SELL
        assert "강제 손절" in signal.reason

    @pytest.mark.asyncio
    async def test_max_rounds_force_sell(self, algorithm, account, market_data):
        """최대 회차 도달 시 강제 손절 테스트"""
        # 최대 회차까지 매수 진행
        algorithm.state.current_round = algorithm.config.max_buy_rounds
        algorithm.state.phase = InfiniteBuyingPhase.ACCUMULATING
        algorithm.state.average_price = Decimal("52000000")  # 현재가보다 높게 설정해서 손실 상태로 만듦

        signal = await algorithm.analyze_signal(account, market_data)

        assert signal.action == TradingAction.SELL
        assert "강제 손절" in signal.reason

    @pytest.mark.asyncio
    async def test_sell_amount_calculation(self, algorithm, account, market_data):
        """매도 수량 계산 테스트"""
        # BTC 잔고가 있는 계좌로 설정
        account.balances[1].balance = Decimal("0.01")  # BTC 잔고

        signal = TradingSignal(
            action=TradingAction.SELL,
            confidence=Decimal("1.0"),
            reason="테스트"
        )

        sell_amount = await algorithm.calculate_sell_amount(account, market_data, signal)

        assert sell_amount == Decimal("0.01")  # 전량 매도

    @pytest.mark.asyncio
    async def test_execute_sell(self, algorithm, account, market_data):
        """매도 실행 테스트"""
        # 매수 후 상태 설정
        algorithm.state.total_investment = Decimal("100000")
        algorithm.state.phase = InfiniteBuyingPhase.ACCUMULATING

        result = await algorithm.execute_sell(
            market_data, Decimal("0.002")
        )

        assert result.success
        assert result.action_taken == ActionTaken.SELL
        assert result.profit_rate is not None
        assert algorithm.state.phase == InfiniteBuyingPhase.INACTIVE

    @pytest.mark.asyncio
    async def test_hold_signal_during_small_drop(self, algorithm, account, market_data):
        """작은 하락 시 홀드 신호 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"))

        # 작은 하락 (3%, 임계점 5% 미만)
        small_drop_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("48500000"),  # 3% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.03")
        )

        signal = await algorithm.analyze_signal(account, small_drop_market_data)

        assert signal.action == TradingAction.HOLD
        assert "대기 중" in signal.reason

    @pytest.mark.asyncio
    async def test_min_buy_interval_check(self, algorithm, account, market_data):
        """최소 매수 간격 확인 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"))

        # 가격이 하락했지만 시간 간격이 부족한 상황
        dropped_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("47500000"),  # 5% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.05")
        )

        # 방금 매수했으므로 최소 간격 미충족
        signal = await algorithm.analyze_signal(account, dropped_market_data)

        assert signal.action == TradingAction.HOLD
        assert "대기 중" in signal.reason

    def test_profit_rate_calculation(self, algorithm):
        """수익률 계산 테스트"""
        algorithm.state.average_price = Decimal("50000000")

        # 10% 상승
        profit_rate = algorithm._calculate_current_profit_rate(Decimal("55000000"))
        assert profit_rate == Decimal("0.10")

        # 5% 하락
        loss_rate = algorithm._calculate_current_profit_rate(Decimal("47500000"))
        assert loss_rate == Decimal("-0.05")

    def test_available_krw_balance(self, algorithm, account):
        """사용 가능한 KRW 잔액 조회 테스트"""
        available = algorithm._get_available_krw_balance(account)
        assert available == Decimal("1000000")

        # 일부 잠금 상태 설정
        account.balances[0].locked = Decimal("100000")
        available = algorithm._get_available_krw_balance(account)
        assert available == Decimal("900000")

    def test_target_currency_balance(self, algorithm, account):
        """대상 통화 잔액 조회 테스트"""
        balance = algorithm._get_target_currency_balance(account, "KRW-BTC")
        assert balance is not None
        assert balance.currency == Currency.BTC

        # 존재하지 않는 통화
        balance = algorithm._get_target_currency_balance(account, "KRW-ETH")
        assert balance is None

    @pytest.mark.asyncio
    async def test_time_based_buy_signal(self, algorithm, account, market_data):
        """시간 기반 매수 신호 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"), BuyType.INITIAL)

        # 시간 설정: 최소 매수 간격과 시간 기반 매수 모두 만족
        # buying_rounds의 마지막 timestamp를 과거로 설정
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(days=4)

        # 잔액 조정 (초기 매수 후 남은 금액)
        account.balances[0].balance = Decimal("900000")  # 10만원 사용 후 90만원 남음

        # 가격이 하락하지 않은 상황 (기존에는 매수 안됨)
        stable_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("51000000"),  # 2% 상승
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("0.02")
        )

        signal = await algorithm.analyze_signal(account, stable_market_data)

        assert signal.action == TradingAction.BUY
        assert "시간 기반 추가 매수" in signal.reason

    @pytest.mark.asyncio
    async def test_price_drop_vs_time_based_priority(self, algorithm, account, market_data):
        """가격 하락과 시간 기반 매수 우선순위 테스트"""
        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"), BuyType.INITIAL)

        # 시간 설정: 최소 매수 간격은 만족, 시간 기반 매수는 부족
        # buying_rounds의 마지막 timestamp를 12시간 전으로 설정 (1일 미만)
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(hours=12)

        # 잔액 조정
        account.balances[0].balance = Decimal("900000")

        dropped_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("47500000"),  # 5% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.05")
        )

        signal = await algorithm.analyze_signal(account, dropped_market_data)

        assert signal.action == TradingAction.BUY
        assert "가격 하락 기반 추가 매수" in signal.reason

    @pytest.mark.asyncio
    async def test_time_based_buying_disabled(self, account, market_data):
        """시간 기반 매수 비활성화 테스트"""
        config = InfiniteBuyingConfig(
            initial_buy_amount=Decimal("100000"),
            enable_time_based_buying=False,  # 시간 기반 매수 비활성화
            min_buy_interval_minutes=1
        )
        algorithm = InfiniteBuyingService(config)

        # 먼저 초기 매수 실행
        await algorithm.execute_buy(market_data, Decimal("100000"), BuyType.INITIAL)

        # 시간은 충분히 지났지만 시간 기반 매수 비활성화
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(days=2)

        stable_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("51000000"),  # 2% 상승
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("0.02")
        )

        signal = await algorithm.analyze_signal(account, stable_market_data)

        assert signal.action == TradingAction.HOLD
        assert "대기 중" in signal.reason

    @pytest.mark.asyncio
    async def test_buying_round_type_tracking(self, algorithm, account, market_data):
        """매수 회차별 타입 추적 테스트"""
        # 1. 초기 매수
        result1 = await algorithm.execute_buy(market_data, Decimal("100000"), BuyType.INITIAL)
        assert result1.success
        assert algorithm.state.buying_rounds[-1].buy_type == BuyType.INITIAL

        # 시간 경과 및 계좌 보정 (테스트용)
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(days=2)
        account.balances[0].balance = Decimal("900000")  # 남은 잔액

        # 2. 시간 기반 매수 (가격 변화 없음)
        stable_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("50500000"),  # 1% 상승
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("0.01")
        )

        result2 = await algorithm.execute_buy(stable_market_data, Decimal("150000"), BuyType.TIME_BASED)
        assert result2.success
        assert algorithm.state.buying_rounds[-1].buy_type == BuyType.TIME_BASED

        # 3. 가격 하락 기반 매수
        dropped_market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("47500000"),  # 평균단가 대비 5% 하락
            volume_24h=Decimal("1000000000"),
            change_rate_24h=Decimal("-0.05")
        )

        # 시간 간격 및 잔액 조정
        algorithm.state.buying_rounds[-1].timestamp = datetime.now() - timedelta(minutes=31)
        account.balances[0].balance = Decimal("800000")

        result3 = await algorithm.execute_buy(dropped_market_data, Decimal("225000"), BuyType.PRICE_DROP)
        assert result3.success
        assert algorithm.state.buying_rounds[-1].buy_type == BuyType.PRICE_DROP

        # 매수 회차별 타입 확인
        assert len(algorithm.state.buying_rounds) == 3
        assert algorithm.state.buying_rounds[0].buy_type == BuyType.INITIAL
        assert algorithm.state.buying_rounds[1].buy_type == BuyType.TIME_BASED
        assert algorithm.state.buying_rounds[2].buy_type == BuyType.PRICE_DROP

    @pytest.mark.asyncio
    async def test_empty_buying_rounds_with_current_round_gt_zero(self, algorithm, account, market_data):
        """current_round > 0이지만 buying_rounds가 비어있는 데이터 불일치 상황 테스트"""
        # 데이터 불일치 상황 시뮬레이션: current_round는 2이지만 buying_rounds는 비어있음
        algorithm.state.current_round = 2
        algorithm.state.total_investment = Decimal("150000")
        algorithm.state.average_price = Decimal("48000000")
        algorithm.state.buying_rounds = []  # 의도적으로 비워둠

        # 매수 신호 생성
        signal = TradingSignal(
            action=TradingAction.BUY,
            confidence=Decimal("1.0"),
            reason="테스트용 매수 신호"
        )

        # 매수 금액 계산 - IndexError가 발생하지 않아야 함
        buy_amount = await algorithm.calculate_buy_amount(
            account,
            signal,
            min_order_amount=Decimal("5000"),
        )

        # 초기 매수 금액으로 계산되어야 함
        expected_amount = min(algorithm.config.initial_buy_amount, Decimal("1000000"))
        assert buy_amount == expected_amount
        assert buy_amount > 0

        # 실제 매수 실행도 정상 작동해야 함
        result = await algorithm.execute_buy(market_data, buy_amount)
        assert result.success
        assert len(algorithm.state.buying_rounds) == 1  # 새로운 라운드가 추가됨
        assert algorithm.state.current_round == 3  # 회차가 증가함


class TestInfiniteBuyingIntegration:
    """무한매수법 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_cycle_test(self):
        """완전한 사이클 테스트"""
        # 설정 및 초기화
        config = InfiniteBuyingConfig(
            initial_buy_amount=Decimal("100000"),
            add_buy_multiplier=Decimal("1.5"),
            target_profit_rate=Decimal("0.10"),
            price_drop_threshold=Decimal("-0.05"),
            min_buy_interval_minutes=0  # 테스트용으로 즉시 매수 가능
        )

        algorithm = InfiniteBuyingService(config)

        account = Account(
            balances=[
                Balance(
                    currency=Currency.KRW,
                    balance=Decimal("1000000"),
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("1"),
                    unit=Currency.KRW
                ),
                Balance(
                    currency=Currency.BTC,
                    balance=Decimal("0"),
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("0"),
                    unit=Currency.KRW
                )
            ]
        )

        # 시나리오 1: 초기 매수
        market_data_1 = MarketData(
            market="KRW-BTC", current_price=Decimal("50000000"),
            volume_24h=Decimal("1000000000"), change_rate_24h=Decimal("0.02")
        )

        signal_1 = await algorithm.analyze_signal(account, market_data_1)
        assert signal_1.action == TradingAction.BUY

        result_1 = await algorithm.execute_buy(market_data_1, Decimal("100000"))
        assert result_1.success
        assert algorithm.state.current_round == 1

        # 시나리오 2: 5% 하락으로 추가 매수
        market_data_2 = MarketData(
            market="KRW-BTC", current_price=Decimal("47500000"),
            volume_24h=Decimal("1000000000"), change_rate_24h=Decimal("-0.05")
        )

        signal_2 = await algorithm.analyze_signal(account, market_data_2)
        assert signal_2.action == TradingAction.BUY

        buy_amount_2 = await algorithm.calculate_buy_amount(
            account, signal_2, Decimal("5000")
        )
        result_2 = await algorithm.execute_buy(market_data_2, buy_amount_2)
        assert result_2.success
        assert algorithm.state.current_round == 2

        # 시나리오 3: 목표 수익률 달성으로 익절
        market_data_3 = MarketData(
            market="KRW-BTC", current_price=Decimal("55000000"),
            volume_24h=Decimal("1000000000"), change_rate_24h=Decimal("0.10")
        )

        signal_3 = await algorithm.analyze_signal(account, market_data_3)
        assert signal_3.action == TradingAction.SELL

        # 매도 실행 (BTC 잔고 설정)
        account.balances[1].balance = algorithm.state.total_volume

        sell_volume = await algorithm.calculate_sell_amount(account, market_data_3, signal_3)
        result_3 = await algorithm.execute_sell(market_data_3, sell_volume)

        assert result_3.success
        assert result_3.profit_rate is not None
        assert result_3.profit_rate > Decimal("0")  # 수익 발생
        assert algorithm.state.phase == InfiniteBuyingPhase.INACTIVE

    @pytest.mark.asyncio
    async def test_profit_rate_calculation_with_current_price(self):
        """현재가 기준 수익률 계산 테스트"""
        # 무한매수법 상태 설정
        state = InfiniteBuyingState(market="KRW-BTC")
        state.phase = InfiniteBuyingPhase.ACCUMULATING
        state.total_investment = Decimal("250000")  # 총 투자금액 25만원
        state.total_volume = Decimal("0.005")  # 총 보유수량 0.005 BTC
        state.average_price = Decimal("50000000")  # 평균단가 5천만원

        # 현재가별 수익률 테스트
        # 1. 10% 상승한 경우
        current_price_up = Decimal("55000000")
        profit_rate_up = state.calculate_current_profit_rate(current_price_up)
        assert profit_rate_up == Decimal("0.10")  # 10% 수익

        current_value_up = state.total_volume * current_price_up  # 275,000원
        profit_amount_up = current_value_up - state.total_investment  # 25,000원 수익
        assert current_value_up == Decimal("275000")
        assert profit_amount_up == Decimal("25000")

        # 2. 5% 하락한 경우
        current_price_down = Decimal("47500000")
        profit_rate_down = state.calculate_current_profit_rate(current_price_down)
        assert profit_rate_down == Decimal("-0.05")  # 5% 손실

        current_value_down = state.total_volume * current_price_down  # 237,500원
        loss_amount_down = current_value_down - state.total_investment  # -12,500원 손실
        assert current_value_down == Decimal("237500")
        assert loss_amount_down == Decimal("-12500")

        # 3. 변화 없는 경우
        current_price_same = Decimal("50000000")
        profit_rate_same = state.calculate_current_profit_rate(current_price_same)
        assert profit_rate_same == Decimal("0")  # 손익 없음

    def test_profit_rate_calculation_edge_cases(self):
        """수익률 계산 경계 조건 테스트"""
        state = InfiniteBuyingState(market="KRW-BTC")

        # 평균단가가 0인 경우 (매수 전)
        profit_rate = state.calculate_current_profit_rate(Decimal("50000000"))
        assert profit_rate == Decimal("0")

        # 보유수량이 0인 경우
        state.average_price = Decimal("50000000")
        state.total_volume = Decimal("0")
        current_value = state.total_volume * Decimal("55000000")
        assert current_value == Decimal("0")
