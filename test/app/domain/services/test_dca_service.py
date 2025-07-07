"""DCA 도메인 서비스 테스트"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.domain.services.dca_service import DcaService
from app.domain.models.dca import DcaConfig, DcaState, BuyingRound, BuyType
from app.domain.models.trading import TradingSignal, MarketData
from app.domain.models.account import Account, Balance
from app.domain.enums import TradingAction, DcaPhase


class TestDcaServiceSignalAnalysis:
    """DCA 서비스 신호 분석 테스트"""

    @pytest.fixture
    def dca_service(self):
        """DCA 서비스 인스턴스"""
        return DcaService()

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            initial_buy_amount=10000,
            target_profit_rate=Decimal("0.10"),
            add_buy_multiplier=Decimal("1.5"),
            force_stop_loss_rate=Decimal("-0.25"),
            max_buy_rounds=5,
            enable_smart_dca=False
        )

    @pytest.fixture
    def sample_account(self):
        """샘플 계좌 정보"""
        balances = [
            Balance(
                currency="KRW",
                balance=Decimal("100000"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("1"),
                unit="KRW"
            ),
            Balance(
                currency="BTC",
                balance=Decimal("0.5"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("40000"),
                unit="KRW"
            )
        ]
        return Account(balances=balances)

    @pytest.fixture
    def sample_market_data(self):
        """샘플 마켓 데이터"""
        return MarketData(
            market="KRW-BTC",
            current_price=Decimal("42000"),
            volume_24h=Decimal("1000"),
            change_rate_24h=Decimal("0.05")
        )

    def test_analyze_signal_initial_buy(self, dca_service, sample_config, sample_account, sample_market_data):
        """초기 매수 신호 분석 테스트"""
        # 비활성 상태
        state = DcaState(market="KRW-BTC", phase=DcaPhase.INACTIVE)

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.BUY
        assert "DCA 초기 매수 신호" in signal.reason

    def test_analyze_signal_initial_buy_insufficient_funds(self, dca_service, sample_config, sample_market_data):
        """초기 매수 자금 부족 테스트"""
        # 자금 부족한 계좌
        balances = [Balance(
            currency="KRW",
            balance=Decimal("5000"),
            locked=Decimal("0"),
            avg_buy_price=Decimal("1"),
            unit="KRW"
        )]
        poor_account = Account(balances=balances)

        state = DcaState(market="KRW-BTC", phase=DcaPhase.INACTIVE)

        signal = dca_service.analyze_signal(
            account=poor_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.HOLD
        assert "초기 매수 불가" in signal.reason

    def test_analyze_signal_take_profit(self, dca_service, sample_config, sample_account, sample_market_data):
        """익절 신호 분석 테스트"""
        # 수익이 난 상태
        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=2,
            total_investment=20000,
            total_volume=Decimal("0.5"),
            average_price=Decimal("35000"),  # 현재 가격 42000보다 낮음 (약 20% 수익)
            target_sell_price=Decimal("38500")  # 10% 목표 수익률
        )

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.SELL
        assert "목표 수익률 달성" in signal.reason

    def test_analyze_signal_force_sell_by_loss_rate(self, dca_service, sample_config, sample_account, sample_market_data):
        """손실률로 인한 강제 매도 테스트"""
        # 큰 손실이 난 상태 (-30%)
        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=2,
            total_investment=20000,
            total_volume=Decimal("0.5"),
            average_price=Decimal("60000")  # 현재 가격 42000보다 높음 (-30% 손실)
        )

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.SELL
        assert "강제 손절" in signal.reason

    def test_analyze_signal_force_sell_by_max_rounds(self, dca_service, sample_config, sample_account, sample_market_data):
        """최대 회차 도달로 인한 강제 매도 테스트"""
        # 최대 회차에 도달한 상태
        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=5,  # max_buy_rounds와 같음
            total_investment=50000,
            total_volume=Decimal("1.0"),
            average_price=Decimal("50000")
        )

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.SELL
        assert "강제 손절" in signal.reason

    def test_analyze_signal_additional_buy(self, dca_service, sample_account, sample_market_data):
        """추가 매수 신호 테스트"""
        # 가격 하락 기반 매수를 위한 설정
        config = DcaConfig(
            initial_buy_amount=10000,
            price_drop_threshold=Decimal("-0.05"),  # 5% 하락 시 매수
            min_buy_interval_minutes=1,
            enable_time_based_buying=False
        )

        # 이전 매수보다 충분한 시간이 지나고 가격이 하락한 상태
        past_time = datetime.now() - timedelta(minutes=5)
        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),  # 이전 매수가
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=past_time
        )

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=1,
            total_investment=10000,
            total_volume=Decimal("0.2"),
            average_price=Decimal("50000"),  # 현재 가격 42000 (16% 하락)
            buying_rounds=[buying_round]
        )

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=config,
            state=state
        )

        assert signal.action == TradingAction.BUY
        assert "가격 하락 기반 추가 매수" in signal.reason

    def test_analyze_signal_hold(self, dca_service, sample_config, sample_account, sample_market_data):
        """홀드 신호 테스트"""
        # 조건을 만족하지 않는 상태
        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=2,
            total_investment=20000,
            total_volume=Decimal("0.5"),
            average_price=Decimal("40000")  # 현재 가격과 비슷 (5% 수익)
        )

        signal = dca_service.analyze_signal(
            account=sample_account,
            market_data=sample_market_data,
            config=sample_config,
            state=state
        )

        assert signal.action == TradingAction.HOLD
        assert "DCA 대기 중" in signal.reason


class TestDcaServiceCalculations:
    """DCA 서비스 계산 로직 테스트"""

    @pytest.fixture
    def dca_service(self):
        """DCA 서비스 인스턴스"""
        return DcaService()

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            initial_buy_amount=10000,
            add_buy_multiplier=Decimal("1.5"),
            max_investment_ratio=Decimal("0.5"),
            enable_smart_dca=False
        )

    @pytest.fixture
    def sample_account(self):
        """샘플 계좌 정보"""
        balances = [
            Balance(
                currency="KRW",
                balance=Decimal("100000"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("1"),
                unit="KRW"
            ),
            Balance(
                currency="BTC",
                balance=Decimal("0.5"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("40000"),
                unit="KRW"
            )
        ]
        return Account(balances=balances)

    @pytest.fixture
    def sample_market_data(self):
        """샘플 마켓 데이터"""
        return MarketData(
            market="KRW-BTC",
            current_price=Decimal("40000"),
            volume_24h=Decimal("1000"),
            change_rate_24h=Decimal("0.05")
        )

    def test_calculate_buy_amount_initial(self, dca_service, sample_config, sample_account, sample_market_data):
        """초기 매수 금액 계산 테스트"""
        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.INACTIVE,
            current_round=0
        )

        buy_amount = dca_service.calculate_buy_amount(
            account=sample_account,
            config=sample_config,
            state=state,
            market_data=sample_market_data
        )

        assert buy_amount == 10000  # initial_buy_amount

    def test_calculate_buy_amount_additional_dca(self, dca_service, sample_config, sample_account, sample_market_data):
        """추가 매수 금액 계산 테스트 (기존 DCA)"""
        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now()
        )

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=1,
            total_investment=10000,
            buying_rounds=[buying_round]
        )

        buy_amount = dca_service.calculate_buy_amount(
            account=sample_account,
            config=sample_config,
            state=state,
            market_data=sample_market_data
        )

        # 이전 매수 금액 * 배수 = 10000 * 1.5 = 15000
        assert buy_amount == 15000

    def test_calculate_buy_amount_smart_dca(self, dca_service, sample_account, sample_market_data):
        """SmartDCA 매수 금액 계산 테스트"""
        config = DcaConfig(
            initial_buy_amount=10000,
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.5"),
            smart_dca_max_multiplier=Decimal("3.0"),
            smart_dca_min_multiplier=Decimal("0.5")
        )

        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now()
        )

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=1,
            total_investment=10000,
            average_price=Decimal("50000"),
            buying_rounds=[buying_round]
        )

        buy_amount = dca_service.calculate_buy_amount(
            account=sample_account,
            config=config,
            state=state,
            market_data=sample_market_data
        )

        # SmartDCA 배수 계산: (50000/40000)^1.5 ≈ 1.4
        # 매수 금액: 10000 * 1.4 ≈ 14000
        assert buy_amount > 10000
        assert buy_amount < 20000

    def test_calculate_buy_amount_investment_limit(self, dca_service, sample_config, sample_market_data):
        """투자 한도 제한 테스트"""
        # 이미 많이 투자한 상태
        balances = [Balance(
            currency="KRW",
            balance=Decimal("100000"),
            locked=Decimal("0"),
            avg_buy_price=Decimal("1"),
            unit="KRW"
        )]
        account = Account(balances=balances)

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=1,
            total_investment=40000  # 전체 KRW 잔액의 40%
        )

        buy_amount = dca_service.calculate_buy_amount(
            account=account,
            config=sample_config,
            state=state,
            market_data=sample_market_data
        )

        # max_investment_ratio = 0.5, 총 KRW = 100000
        # 최대 투자 가능: 50000, 이미 투자: 40000
        # 추가 투자 가능: 10000
        assert buy_amount == 10000

    def test_calculate_sell_amount(self, dca_service, sample_market_data):
        """매도 수량 계산 테스트"""
        balances = [
            Balance(
                currency="KRW",
                balance=Decimal("50000"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("1"),
                unit="KRW"
            ),
            Balance(
                currency="BTC",
                balance=Decimal("0.5"),
                locked=Decimal("0.1"),
                avg_buy_price=Decimal("40000"),
                unit="KRW"
            )
        ]
        account = Account(balances=balances)

        state = DcaState(
            market="KRW-BTC",
            average_price=Decimal("40000")
        )

        sell_amount = dca_service.calculate_sell_amount(
            account=account,
            market_data=sample_market_data,
            state=state
        )

        # 사용 가능한 수량: 0.5 - 0.1 = 0.4
        assert sell_amount == Decimal("0.4")


class TestDcaServiceExecution:
    """DCA 서비스 실행 로직 테스트"""

    @pytest.fixture
    def dca_service(self):
        """DCA 서비스 인스턴스"""
        return DcaService()

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            initial_buy_amount=10000,
            target_profit_rate=Decimal("0.10")
        )

    @pytest.fixture
    def sample_market_data(self):
        """샘플 마켓 데이터"""
        return MarketData(
            market="KRW-BTC",
            current_price=Decimal("40000"),
            volume_24h=Decimal("1000"),
            change_rate_24h=Decimal("0.05")
        )

    def test_execute_buy_initial(self, dca_service, sample_config, sample_market_data):
        """초기 매수 실행 테스트"""
        state = DcaState(market="KRW-BTC", phase=DcaPhase.INACTIVE)

        new_round = dca_service.execute_buy(
            market_data=sample_market_data,
            buy_amount=10000,
            config=sample_config,
            state=state,
            buy_type=BuyType.INITIAL,
            reason="초기 매수"
        )

        # 새로운 매수 회차 확인
        assert new_round.round_number == 1
        assert new_round.buy_amount == 10000
        assert new_round.buy_price == Decimal("40000")
        assert new_round.buy_type == BuyType.INITIAL

        # 상태 업데이트 확인
        assert state.phase == DcaPhase.ACCUMULATING
        assert state.current_round == 1
        assert state.total_investment == 10000
        assert len(state.buying_rounds) == 1

    def test_execute_buy_additional(self, dca_service, sample_config, sample_market_data):
        """추가 매수 실행 테스트"""
        # 이미 매수가 있는 상태
        first_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now()
        )

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=1,
            total_investment=10000,
            total_volume=Decimal("0.2"),
            average_price=Decimal("50000"),
            buying_rounds=[first_round]
        )

        new_round = dca_service.execute_buy(
            market_data=sample_market_data,
            buy_amount=15000,
            config=sample_config,
            state=state,
            buy_type=BuyType.PRICE_DROP,
            reason="가격 하락 매수"
        )

        # 새로운 매수 회차 확인
        assert new_round.round_number == 2
        assert new_round.buy_amount == 15000

        # 상태 업데이트 확인
        assert state.current_round == 2
        assert state.total_investment == 25000
        assert len(state.buying_rounds) == 2

    def test_execute_sell(self, dca_service, sample_market_data):
        """매도 실행 테스트"""
        # 매수 히스토리가 있는 상태
        buying_rounds = [
            BuyingRound(
                round_number=1,
                buy_price=Decimal("50000"),
                buy_amount=10000,
                buy_volume=Decimal("0.2"),
                timestamp=datetime.now()
            ),
            BuyingRound(
                round_number=2,
                buy_price=Decimal("40000"),
                buy_amount=15000,
                buy_volume=Decimal("0.375"),
                timestamp=datetime.now()
            )
        ]

        state = DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=2,
            total_investment=25000,
            total_volume=Decimal("0.575"),
            average_price=Decimal("43478"),  # 25000 / 0.575
            buying_rounds=buying_rounds
        )

        profit_amount = dca_service.execute_sell(
            market_data=sample_market_data,
            sell_volume=Decimal("0.575"),
            state=state
        )

        # 수익 계산 확인
        # 매도 금액: 40000 * 0.575 = 23000
        # 수익: 23000 - 25000 = -2000 (손실)
        assert profit_amount == Decimal("-2000")

        # 상태 초기화 확인
        assert state.phase == DcaPhase.INACTIVE
        assert state.current_round == 0
        assert state.total_investment == 0
        assert len(state.buying_rounds) == 0


class TestDcaServiceConditions:
    """DCA 서비스 조건 확인 테스트"""

    @pytest.fixture
    def dca_service(self):
        """DCA 서비스 인스턴스"""
        return DcaService()

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            max_buy_rounds=3,
            min_buy_interval_minutes=30,
            force_stop_loss_rate=Decimal("-0.25"),
            target_profit_rate=Decimal("0.10"),
            time_based_buy_interval_hours=24,
            enable_time_based_buying=True
        )

    def test_can_buy_more_success(self, dca_service, sample_config):
        """추가 매수 가능 테스트"""
        past_time = datetime.now() - timedelta(minutes=60)
        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=past_time
        )

        state = DcaState(
            market="KRW-BTC",
            current_round=1,
            last_buy_time=past_time,
            buying_rounds=[buying_round]
        )

        can_buy, reason = dca_service.can_buy_more(
            config=sample_config,
            state=state,
            current_time=datetime.now()
        )

        assert can_buy is True
        assert "추가 매수 가능" in reason

    def test_can_buy_more_max_rounds_reached(self, dca_service, sample_config):
        """최대 회차 도달 테스트"""
        state = DcaState(
            market="KRW-BTC",
            current_round=3  # max_buy_rounds와 같음
        )

        can_buy, reason = dca_service.can_buy_more(
            config=sample_config,
            state=state,
            current_time=datetime.now()
        )

        assert can_buy is False
        assert "최대 매수 회차" in reason

    def test_can_buy_more_min_interval_not_met(self, dca_service, sample_config):
        """최소 매수 간격 미충족 테스트"""
        recent_time = datetime.now() - timedelta(minutes=10)  # 30분보다 짧음

        state = DcaState(
            market="KRW-BTC",
            current_round=1,
            last_buy_time=recent_time
        )

        can_buy, reason = dca_service.can_buy_more(
            config=sample_config,
            state=state,
            current_time=datetime.now()
        )

        assert can_buy is False
        assert "최소 매수 간격" in reason

    def test_should_time_based_buy(self, dca_service, sample_config):
        """시간 기반 매수 조건 테스트"""
        old_time = datetime.now() - timedelta(hours=25)  # 24시간보다 오래됨
        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=old_time
        )

        state = DcaState(
            market="KRW-BTC",
            buying_rounds=[buying_round]
        )

        should_buy = dca_service.should_time_based_buy(config=sample_config, state=state)
        assert should_buy is True

    def test_should_price_drop_buy(self, dca_service):
        """가격 하락 기반 매수 조건 테스트"""
        market_data = MarketData(
            market="KRW-BTC",
            current_price=Decimal("40000"),
            volume_24h=Decimal("1000"),
            change_rate_24h=Decimal("0.05")
        )
        config = DcaConfig(
            price_drop_threshold=Decimal("-0.05"),  # 5% 하락 트리거
            min_buy_interval_minutes=1
        )

        old_time = datetime.now() - timedelta(minutes=5)
        buying_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=old_time
        )

        state = DcaState(
            market="KRW-BTC",
            average_price=Decimal("50000"),  # 현재가 40000 (20% 하락)
            buying_rounds=[buying_round]
        )

        should_buy = dca_service.should_price_drop_buy(
            market_data=market_data,
            config=config,
            state=state
        )

        assert should_buy is True
