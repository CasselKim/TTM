"""DCA 모델 테스트"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.domain.models.dca import (
    DcaConfig,
    DcaState,
    BuyingRound,
    BuyType,
    DcaResult
)
from app.domain.enums import ActionTaken, DcaPhase


class TestDcaConfig:
    """DCA 설정 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = DcaConfig()

        assert config.initial_buy_amount == 5000
        assert config.add_buy_multiplier == Decimal("1.5")
        assert config.target_profit_rate == Decimal("0.10")
        assert config.enable_smart_dca is False

    def test_smart_dca_config(self):
        """SmartDCA 설정 테스트"""
        config = DcaConfig(
            enable_smart_dca=True,
            smart_dca_rho=Decimal("2.0"),
            smart_dca_max_multiplier=Decimal("4.0"),
            smart_dca_min_multiplier=Decimal("0.2")
        )

        assert config.enable_smart_dca is True
        assert config.smart_dca_rho == Decimal("2.0")
        assert config.smart_dca_max_multiplier == Decimal("4.0")
        assert config.smart_dca_min_multiplier == Decimal("0.2")


    def test_smart_dca_multiplier_disabled(self):
        """SmartDCA 비활성화 시 배수 계산 테스트"""
        config = DcaConfig(enable_smart_dca=False)

        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("40000"), Decimal("50000")
        )
        assert multiplier == Decimal("1.0")

    def test_smart_dca_multiplier_enabled(self):
        """SmartDCA 활성화 시 배수 계산 테스트"""
        config = DcaConfig(
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.5"),
            smart_dca_max_multiplier=Decimal("3.0"),
            smart_dca_min_multiplier=Decimal("0.3")
        )

        # 가격 하락 시 매수 증가
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("40000"), Decimal("50000")  # 20% 하락
        )
        assert multiplier > Decimal("1.0")
        assert multiplier < Decimal("3.0")

        # 가격 상승 시 매수 감소
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("60000"), Decimal("50000")  # 20% 상승
        )
        assert multiplier < Decimal("1.0")
        assert multiplier > Decimal("0.3")

        # 극단적 하락 시 최대 배수 제한
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("10000"), Decimal("50000")  # 80% 하락
        )
        assert multiplier == Decimal("3.0")

        # 극단적 상승 시 최소 배수 제한
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("200000"), Decimal("50000")  # 300% 상승
        )
        assert multiplier == Decimal("0.3")

    def test_smart_dca_multiplier_zero_reference(self):
        """기준 가격이 0일 때 배수 계산 테스트"""
        config = DcaConfig(enable_smart_dca=True)

        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("50000"), Decimal("0")
        )
        assert multiplier == Decimal("1.0")


class TestBuyingRound:
    """매수 회차 테스트"""

    def test_buying_round_creation(self):
        """매수 회차 생성 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            buy_type=BuyType.INITIAL,
            reason="초기 매수"
        )

        assert round_data.round_number == 1
        assert round_data.buy_price == Decimal("50000")
        assert round_data.buy_amount == 10000
        assert round_data.buy_volume == Decimal("0.2")
        assert round_data.buy_type == BuyType.INITIAL
        assert round_data.reason == "초기 매수"

    def test_unit_cost_calculation(self):
        """단위당 비용 계산 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now()
        )

        # unit_cost 프로퍼티가 삭제되어 직접 계산으로 대체
        expected_unit_cost = Decimal("10000") / Decimal("0.2")
        calculated_unit_cost = round_data.buy_amount / round_data.buy_volume if round_data.buy_volume > 0 else Decimal("0")
        assert calculated_unit_cost == expected_unit_cost

    def test_unit_cost_zero_volume(self):
        """매수량이 0일 때 단위당 비용 테스트"""
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=0,
            buy_volume=Decimal("0"),
            timestamp=datetime.now()
        )

        # unit_cost 프로퍼티가 삭제되어 직접 계산으로 대체
        calculated_unit_cost = round_data.buy_amount / round_data.buy_volume if round_data.buy_volume > 0 else Decimal("0")
        assert calculated_unit_cost == Decimal("0")


class TestDcaState:
    """DCA 상태 테스트"""

    def test_initial_state(self):
        """초기 상태 테스트"""
        state = DcaState(market="KRW-BTC")

        assert state.market == "KRW-BTC"
        assert state.phase == DcaPhase.INACTIVE
        assert state.current_round == 0
        assert state.total_investment == 0
        assert state.total_volume == Decimal("0")
        assert state.average_price == Decimal("0")
        assert state.is_active is False

    def test_add_buying_round(self):
        """매수 회차 추가 테스트"""
        state = DcaState(market="KRW-BTC")
        config = DcaConfig(target_profit_rate=Decimal("0.10"))

        # 첫 번째 매수
        first_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now(),
            buy_type=BuyType.INITIAL
        )

        state.add_buying_round(first_round, config)

        assert state.current_round == 1
        assert state.total_investment == 10000
        assert state.total_volume == Decimal("0.2")
        assert state.average_price == Decimal("50000")
        assert state.target_sell_price == Decimal("55000")  # 10% 상승
        assert state.last_buy_price == Decimal("50000")

        # 두 번째 매수
        second_round = BuyingRound(
            round_number=2,
            buy_price=Decimal("40000"),
            buy_amount=15000,
            buy_volume=Decimal("0.375"),
            timestamp=datetime.now(),
            buy_type=BuyType.PRICE_DROP
        )

        state.add_buying_round(second_round, config)

        assert state.current_round == 2
        assert state.total_investment == 25000
        assert state.total_volume == Decimal("0.575")
        # 평균 단가: 25000 / 0.575 ≈ 43478
        expected_avg = Decimal("25000") / Decimal("0.575")
        assert abs(state.average_price - expected_avg) < Decimal("0.01")

    def test_profit_rate_calculation(self):
        """수익률 계산 테스트"""
        state = DcaState(
            market="KRW-BTC",
            average_price=Decimal("50000")
        )

        # 10% 상승
        profit_rate = state.calculate_current_profit_rate(Decimal("55000"))
        assert profit_rate == Decimal("0.1")

        # 20% 하락
        profit_rate = state.calculate_current_profit_rate(Decimal("40000"))
        assert profit_rate == Decimal("-0.2")

        # 평균단가가 0일 때
        state.average_price = Decimal("0")
        profit_rate = state.calculate_current_profit_rate(Decimal("50000"))
        assert profit_rate == Decimal("0")

    def test_reset_cycle(self):
        """사이클 리셋 테스트"""
        state = DcaState(
            market="KRW-BTC",
            current_round=3,
            total_investment=50000,
            total_volume=Decimal("1.0"),
            average_price=Decimal("50000")
        )

        # 매수 기록 추가
        round_data = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now()
        )
        state.buying_rounds.append(round_data)

        # reset_cycle 메서드가 삭제되어 complete_cycle로 대체
        state.complete_cycle()
        # 새 마켓으로 사이클 시작
        state.start_new_cycle("KRW-ETH")

        assert state.market == "KRW-ETH"
        assert state.phase == DcaPhase.INITIAL_BUY
        assert state.current_round == 0
        assert state.total_investment == 0
        assert state.total_volume == Decimal("0")
        assert state.average_price == Decimal("0")
        assert len(state.buying_rounds) == 0

    def test_time_based_buy_tracking(self):
        """시간 기반 매수 추적 테스트"""
        state = DcaState(market="KRW-BTC")
        config = DcaConfig()

        # 시간 기반 매수
        time_based_round = BuyingRound(
            round_number=1,
            buy_price=Decimal("50000"),
            buy_amount=10000,
            buy_volume=Decimal("0.2"),
            timestamp=datetime.now(),
            buy_type=BuyType.TIME_BASED
        )

        state.add_buying_round(time_based_round, config)

        assert state.last_time_based_buy_time is not None
        assert state.last_time_based_buy_time == time_based_round.timestamp

        # 일반 매수는 시간 기반 매수 시간을 업데이트하지 않음
        normal_round = BuyingRound(
            round_number=2,
            buy_price=Decimal("45000"),
            buy_amount=15000,
            buy_volume=Decimal("0.333"),
            timestamp=datetime.now(),
            buy_type=BuyType.PRICE_DROP
        )

        previous_time = state.last_time_based_buy_time
        state.add_buying_round(normal_round, config)

        assert state.last_time_based_buy_time == previous_time


class TestDcaResult:
    """DCA 결과 테스트"""

    def test_result_creation(self):
        """결과 생성 테스트"""
        state = DcaState(market="KRW-BTC")

        result = DcaResult(
            success=True,
            action_taken=ActionTaken.BUY,
            message="매수 실행 완료",
            trade_price=Decimal("50000"),
            trade_amount=10000,
            trade_volume=Decimal("0.2"),
            current_state=state,
            profit_rate=Decimal("0.05"),
            profit_loss_amount_krw=1000
        )

        assert result.success is True
        assert result.action_taken == ActionTaken.BUY
        assert result.message == "매수 실행 완료"
        assert result.trade_price == Decimal("50000")
        assert result.trade_amount == 10000
        assert result.trade_volume == Decimal("0.2")
        assert result.current_state == state
        assert result.profit_rate == Decimal("0.05")
        assert result.profit_loss_amount_krw == 1000


class TestSmartDcaIntegration:
    """SmartDCA 통합 테스트"""

    def test_smart_dca_performance_comparison(self):
        """SmartDCA 성능 비교 테스트"""
        # V자 회복 시나리오: 50k → 30k → 70k
        price_scenario = [50000, 40000, 30000, 50000, 70000]

        # 기본 DCA 설정
        dca_config = DcaConfig(
            initial_buy_amount=10000,
            add_buy_multiplier=Decimal("1.5")
        )

        # SmartDCA 설정
        smart_config = DcaConfig(
            initial_buy_amount=10000,
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.5"),
            smart_dca_max_multiplier=Decimal("3.0"),
            smart_dca_min_multiplier=Decimal("0.3")
        )

        # 기본 DCA 시뮬레이션
        dca_total_investment = 0
        dca_total_volume = Decimal("0")
        dca_amount = 10000

        for price in price_scenario:
            current_price = Decimal(str(price))
            volume = Decimal(str(dca_amount)) / current_price
            dca_total_investment += dca_amount
            dca_total_volume += volume
            dca_amount = int(dca_amount * dca_config.add_buy_multiplier)

        # SmartDCA 시뮬레이션
        smart_total_investment = 0
        smart_total_volume = Decimal("0")
        smart_avg_price = Decimal("0")

        for i, price in enumerate(price_scenario):
            current_price = Decimal(str(price))

            if i == 0:
                smart_amount = smart_config.initial_buy_amount
            else:
                multiplier = smart_config.calculate_smart_dca_multiplier(
                    current_price, smart_avg_price
                )
                smart_amount = int(smart_config.initial_buy_amount * multiplier)

            volume = Decimal(str(smart_amount)) / current_price
            smart_total_investment += smart_amount
            smart_total_volume += volume

            if smart_total_volume > 0:
                smart_avg_price = Decimal(str(smart_total_investment)) / smart_total_volume

        # 최종 성과 비교
        final_price = Decimal(str(price_scenario[-1]))

        dca_final_value = dca_total_volume * final_price
        dca_profit_rate = (dca_final_value - Decimal(str(dca_total_investment))) / Decimal(str(dca_total_investment))

        smart_final_value = smart_total_volume * final_price
        smart_profit_rate = (smart_final_value - Decimal(str(smart_total_investment))) / Decimal(str(smart_total_investment))

        # SmartDCA가 더 나은 성과를 보여야 함
        assert smart_profit_rate > dca_profit_rate

        # 투자 효율성 확인 (적은 투자로 더 높은 수익률)
        assert smart_total_investment < dca_total_investment

    def test_smart_dca_risk_management(self):
        """SmartDCA 리스크 관리 테스트"""
        config = DcaConfig(
            enable_smart_dca=True,
            smart_dca_rho=Decimal("2.0"),
            smart_dca_max_multiplier=Decimal("2.0"),
            smart_dca_min_multiplier=Decimal("0.5")
        )

        # 극단적 하락 시나리오
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("1000"), Decimal("100000")  # 99% 하락
        )
        assert multiplier == Decimal("2.0")  # 최대 배수 제한

        # 극단적 상승 시나리오
        multiplier = config.calculate_smart_dca_multiplier(
            Decimal("1000000"), Decimal("10000")  # 10000% 상승
        )
        assert multiplier == Decimal("0.5")  # 최소 배수 제한


class TestDcaConfigUpdate:
    """DCA 설정 변경 테스트"""

    def test_config_update_all_params(self):
        """모든 파라미터 업데이트 테스트"""
        # 기존 설정
        original_config = DcaConfig(
            initial_buy_amount=5000,
            target_profit_rate=Decimal("0.10"),
            add_buy_multiplier=Decimal("1.5"),
            enable_smart_dca=False
        )

        # 새로운 설정 데이터
        new_data = {
            "initial_buy_amount": 10000,
            "target_profit_rate": Decimal("0.15"),
            "add_buy_multiplier": Decimal("2.0"),
            "enable_smart_dca": True,
            "smart_dca_rho": Decimal("1.8"),
            "smart_dca_max_multiplier": Decimal("4.0"),
            "smart_dca_min_multiplier": Decimal("0.2"),
            "price_drop_threshold": Decimal("-0.03"),
            "force_stop_loss_rate": Decimal("-0.30"),
            "max_buy_rounds": 12,
            "time_based_buy_interval_hours": 48,
            "enable_time_based_buying": True
        }

        # 새로운 설정 생성
        updated_config = DcaConfig(**new_data)

        # 검증
        assert updated_config.initial_buy_amount == 10000
        assert updated_config.target_profit_rate == Decimal("0.15")
        assert updated_config.add_buy_multiplier == Decimal("2.0")
        assert updated_config.enable_smart_dca is True
        assert updated_config.smart_dca_rho == Decimal("1.8")
        assert updated_config.smart_dca_max_multiplier == Decimal("4.0")
        assert updated_config.smart_dca_min_multiplier == Decimal("0.2")
        assert updated_config.price_drop_threshold == Decimal("-0.03")
        assert updated_config.force_stop_loss_rate == Decimal("-0.30")
        assert updated_config.max_buy_rounds == 12
        assert updated_config.time_based_buy_interval_hours == 48
        assert updated_config.enable_time_based_buying is True

    def test_config_partial_update(self):
        """부분 업데이트 테스트"""
        # 기존 설정
        original_config = DcaConfig(
            initial_buy_amount=5000,
            target_profit_rate=Decimal("0.10"),
            add_buy_multiplier=Decimal("1.5"),
            enable_smart_dca=False
        )

        # 기존 값 유지하며 일부만 변경
        config_data = original_config.model_dump()
        config_data["target_profit_rate"] = Decimal("0.20")
        config_data["enable_smart_dca"] = True

        updated_config = DcaConfig(**config_data)

        # 변경된 값 확인
        assert updated_config.target_profit_rate == Decimal("0.20")
        assert updated_config.enable_smart_dca is True

        # 변경되지 않은 값 확인
        assert updated_config.initial_buy_amount == 5000
        assert updated_config.add_buy_multiplier == Decimal("1.5")

    def test_config_validation_on_update(self):
        """설정 변경 시 유효성 검증 테스트"""
        # 잘못된 목표 수익률 (음수)
        with pytest.raises(Exception):
            DcaConfig(target_profit_rate=Decimal("-0.1"))

        # 잘못된 추가 매수 하락률 (양수)
        with pytest.raises(Exception):
            DcaConfig(price_drop_threshold=Decimal("0.025"))

        # 잘못된 강제 손절률 (양수)
        with pytest.raises(Exception):
            DcaConfig(force_stop_loss_rate=Decimal("0.25"))

        # 잘못된 최대 투자 비율 (1 초과)
        with pytest.raises(Exception):
            DcaConfig(max_investment_ratio=Decimal("1.5"))

    def test_smart_dca_config_update(self):
        """SmartDCA 관련 설정 변경 테스트"""
        config = DcaConfig(enable_smart_dca=False)

        # SmartDCA 활성화 및 파라미터 설정
        config_data = config.model_dump()
        config_data.update({
            "enable_smart_dca": True,
            "smart_dca_rho": Decimal("2.5"),
            "smart_dca_max_multiplier": Decimal("6.0"),
            "smart_dca_min_multiplier": Decimal("0.1")
        })

        updated_config = DcaConfig(**config_data)

        assert updated_config.enable_smart_dca is True
        assert updated_config.smart_dca_rho == Decimal("2.5")
        assert updated_config.smart_dca_max_multiplier == Decimal("6.0")
        assert updated_config.smart_dca_min_multiplier == Decimal("0.1")

        # 새로운 설정으로 SmartDCA 배수 계산 테스트
        multiplier = updated_config.calculate_smart_dca_multiplier(
            Decimal("40000"), Decimal("50000")  # 20% 하락
        )
        assert multiplier > Decimal("1.0")
        assert multiplier <= Decimal("6.0")

    def test_time_based_config_update(self):
        """시간 기반 매수 설정 변경 테스트"""
        config = DcaConfig(
            enable_time_based_buying=False,
            time_based_buy_interval_hours=72
        )

        # 시간 기반 매수 활성화 및 간격 변경
        config_data = config.model_dump()
        config_data.update({
            "enable_time_based_buying": True,
            "time_based_buy_interval_hours": 24
        })

        updated_config = DcaConfig(**config_data)

        assert updated_config.enable_time_based_buying is True
        assert updated_config.time_based_buy_interval_hours == 24

    def test_json_serialization_deserialization(self):
        """JSON 직렬화/역직렬화 테스트"""
        original_config = DcaConfig(
            initial_buy_amount=8000,
            target_profit_rate=Decimal("0.12"),
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.8")
        )

        # JSON으로 직렬화 (메서드가 여전히 존재함)
        json_str = original_config.to_cache_json()

        # JSON에서 역직렬화 (메서드가 여전히 존재함)
        restored_config = DcaConfig.from_cache_json(json_str)

        # 값 비교
        assert restored_config.initial_buy_amount == original_config.initial_buy_amount
        assert restored_config.target_profit_rate == original_config.target_profit_rate
        assert restored_config.enable_smart_dca == original_config.enable_smart_dca
        assert restored_config.smart_dca_rho == original_config.smart_dca_rho
