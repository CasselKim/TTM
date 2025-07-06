"""DCA 유스케이스 테스트"""

import pytest
from unittest.mock import AsyncMock, Mock
from decimal import Decimal

from app.application.usecase.dca_usecase import DcaUsecase
from app.domain.models.dca import DcaConfig, DcaState, DcaResult
from app.domain.enums import ActionTaken, DcaPhase


class TestDcaUsecaseConfigUpdate:
    """DCA 유스케이스 설정 변경 테스트"""

    @pytest.fixture
    def mock_repositories(self):
        """모킹된 레포지토리들"""
        return {
            'account_repository': AsyncMock(),
            'order_repository': AsyncMock(),
            'ticker_repository': AsyncMock(),
            'dca_repository': AsyncMock(),
            'notification_repo': AsyncMock(),
            'dca_service': AsyncMock()
        }

    @pytest.fixture
    def dca_usecase(self, mock_repositories):
        """DCA 유스케이스 인스턴스"""
        return DcaUsecase(
            account_repository=mock_repositories['account_repository'],
            order_repository=mock_repositories['order_repository'],
            ticker_repository=mock_repositories['ticker_repository'],
            dca_repository=mock_repositories['dca_repository'],
            notification_repo=mock_repositories['notification_repo'],
            dca_service=mock_repositories['dca_service']
        )

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            initial_buy_amount=10000,
            target_profit_rate=Decimal("0.10"),
            add_buy_multiplier=Decimal("1.5"),
            enable_smart_dca=False
        )

    @pytest.fixture
    def sample_state(self):
        """샘플 DCA 상태"""
        return DcaState(
            market="KRW-BTC",
            phase=DcaPhase.ACCUMULATING,
            current_round=2,
            total_investment=25000,
            total_volume=Decimal("0.5")
        )

    async def test_update_config_success(self, dca_usecase, mock_repositories, sample_config, sample_state):
        """설정 변경 성공 테스트"""
        market = "KRW-BTC"

        # 모킹 설정
        mock_repositories['dca_repository'].get_config.return_value = sample_config
        mock_repositories['dca_repository'].get_state.return_value = sample_state
        mock_repositories['dca_repository'].save_config.return_value = None
        mock_repositories['notification_repo'].send_info_notification.return_value = None

        # 새로운 설정
        new_config = DcaConfig(
            initial_buy_amount=15000,
            target_profit_rate=Decimal("0.15"),
            add_buy_multiplier=Decimal("2.0"),
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.8")
        )

        # 설정 변경 실행
        result = await dca_usecase.update(market, new_config)

        # 검증
        assert result.success is True
        assert result.action_taken == ActionTaken.HOLD
        assert f"{market} DCA 설정이 변경되었습니다." in result.message
        assert result.current_state == sample_state

        # 레포지토리 호출 검증
        mock_repositories['dca_repository'].get_config.assert_called_once_with(market)
        mock_repositories['dca_repository'].get_state.assert_called_once_with(market)
        mock_repositories['dca_repository'].save_config.assert_called_once_with(market, new_config)
        mock_repositories['notification_repo'].send_info_notification.assert_called_once()

    async def test_update_config_no_existing_dca(self, dca_usecase, mock_repositories):
        """실행 중인 DCA가 없을 때 설정 변경 테스트"""
        market = "KRW-BTC"

        # 모킹 설정 - 설정이나 상태가 없음
        mock_repositories['dca_repository'].get_config.return_value = None
        mock_repositories['dca_repository'].get_state.return_value = None

        new_config = DcaConfig(target_profit_rate=Decimal("0.15"))

        # 설정 변경 실행
        result = await dca_usecase.update(market, new_config)

        # 검증
        assert result.success is False
        assert result.action_taken == ActionTaken.HOLD
        assert f"{market} DCA가 실행 중이 아닙니다." in result.message
        assert result.current_state is None

        # save_config이 호출되지 않았는지 확인
        mock_repositories['dca_repository'].save_config.assert_not_called()

    async def test_update_config_with_smart_dca_activation(self, dca_usecase, mock_repositories, sample_state):
        """Smart DCA 활성화 설정 변경 테스트"""
        market = "KRW-BTC"

        # 기존 설정 (Smart DCA 비활성화)
        original_config = DcaConfig(enable_smart_dca=False)

        # 모킹 설정
        mock_repositories['dca_repository'].get_config.return_value = original_config
        mock_repositories['dca_repository'].get_state.return_value = sample_state
        mock_repositories['dca_repository'].save_config.return_value = None
        mock_repositories['notification_repo'].send_info_notification.return_value = None

        # 새로운 설정 (Smart DCA 활성화)
        new_config = DcaConfig(
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.5"),
            smart_dca_max_multiplier=Decimal("3.0"),
            smart_dca_min_multiplier=Decimal("0.3")
        )

        # 설정 변경 실행
        result = await dca_usecase.update(market, new_config)

        # 검증
        assert result.success is True

        # 알림에서 Smart DCA 활성화 상태가 표시되는지 확인
        notification_call = mock_repositories['notification_repo'].send_info_notification.call_args
        fields = notification_call[1]['fields']
        smart_dca_field = next((field for field in fields if field[0] == "Smart DCA"), None)
        assert smart_dca_field is not None
        assert smart_dca_field[1] == "활성화"

    async def test_update_config_with_validation_error(self, dca_usecase, mock_repositories, sample_config, sample_state):
        """유효하지 않은 설정 변경 테스트"""
        market = "KRW-BTC"

        # 모킹 설정
        mock_repositories['dca_repository'].get_config.return_value = sample_config
        mock_repositories['dca_repository'].get_state.return_value = sample_state

        # 잘못된 설정 (목표 수익률이 음수)
        with pytest.raises(Exception):
            invalid_config = DcaConfig(target_profit_rate=Decimal("-0.1"))
            await dca_usecase.update_config(market, invalid_config)

    async def test_update_config_notification_content(self, dca_usecase, mock_repositories, sample_config, sample_state):
        """알림 내용 검증 테스트"""
        market = "KRW-BTC"

        # 모킹 설정
        mock_repositories['dca_repository'].get_config.return_value = sample_config
        mock_repositories['dca_repository'].get_state.return_value = sample_state
        mock_repositories['dca_repository'].save_config.return_value = None
        mock_repositories['notification_repo'].send_info_notification.return_value = None

        # 새로운 설정
        new_config = DcaConfig(
            target_profit_rate=Decimal("0.20"),
            add_buy_multiplier=Decimal("2.5"),
            enable_smart_dca=True
        )

        # 설정 변경 실행
        result = await dca_usecase.update(market, new_config)

        # 알림 호출 검증
        notification_call = mock_repositories['notification_repo'].send_info_notification.call_args

        # 알림 제목 확인
        assert notification_call[1]['title'] == "DCA 설정 변경"

        # 알림 메시지 확인
        assert f"**{market}** 마켓의 DCA 설정이 변경되었습니다." in notification_call[1]['message']

        # 알림 필드 확인
        fields = notification_call[1]['fields']
        assert len(fields) == 3

        # 목표 수익률 필드
        profit_field = next((field for field in fields if field[0] == "목표 수익률"), None)
        assert profit_field is not None
        assert "20.0%" in profit_field[1]

        # 추가 매수 배수 필드
        multiplier_field = next((field for field in fields if field[0] == "추가 매수 배수"), None)
        assert multiplier_field is not None
        assert "2.5" in multiplier_field[1]

        # Smart DCA 필드
        smart_field = next((field for field in fields if field[0] == "Smart DCA"), None)
        assert smart_field is not None
        assert smart_field[1] == "활성화"

    async def test_update_config_preserves_state(self, dca_usecase, mock_repositories, sample_config, sample_state):
        """설정 변경이 상태를 보존하는지 테스트"""
        market = "KRW-BTC"

        # 모킹 설정
        mock_repositories['dca_repository'].get_config.return_value = sample_config
        mock_repositories['dca_repository'].get_state.return_value = sample_state
        mock_repositories['dca_repository'].save_config.return_value = None
        mock_repositories['notification_repo'].send_info_notification.return_value = None

        # 새로운 설정
        new_config = DcaConfig(target_profit_rate=Decimal("0.25"))

        # 설정 변경 실행
        result = await dca_usecase.update(market, new_config)

        # 상태가 보존되는지 확인
        assert result.current_state == sample_state
        assert result.current_state.market == "KRW-BTC"
        assert result.current_state.current_round == 2
        assert result.current_state.total_investment == 25000

        # 상태는 저장되지 않고 설정만 저장되는지 확인
        mock_repositories['dca_repository'].save_config.assert_called_once_with(market, new_config)
        mock_repositories['dca_repository'].save_state.assert_not_called()


class TestDcaUsecaseConfigUpdateIntegration:
    """DCA 설정 변경 통합 테스트"""

    def test_config_update_flow(self):
        """설정 변경 전체 플로우 테스트"""
        # 1. 기존 설정 생성
        original_config = DcaConfig(
            initial_buy_amount=5000,
            target_profit_rate=Decimal("0.10"),
            enable_smart_dca=False
        )

        # 2. 설정 데이터 업데이트 (UI에서 하는 방식 시뮬레이션)
        config_data = original_config.model_dump()
        config_data.update({
            "target_profit_rate": Decimal("0.15"),
            "enable_smart_dca": True,
            "smart_dca_rho": Decimal("1.8"),
            "max_buy_rounds": 12
        })

        # 3. 새로운 설정 객체 생성
        updated_config = DcaConfig(**config_data)

        # 4. 검증
        assert updated_config.target_profit_rate == Decimal("0.15")
        assert updated_config.enable_smart_dca is True
        assert updated_config.smart_dca_rho == Decimal("1.8")
        assert updated_config.max_buy_rounds == 12

        # 변경되지 않은 값들 확인
        assert updated_config.initial_buy_amount == 5000

    def test_smart_dca_multiplier_calculation_after_update(self):
        """설정 변경 후 SmartDCA 배수 계산 테스트"""
        # 기존 설정 (SmartDCA 비활성화)
        original_config = DcaConfig(enable_smart_dca=False)

        # SmartDCA 활성화로 설정 변경
        config_data = original_config.model_dump()
        config_data.update({
            "enable_smart_dca": True,
            "smart_dca_rho": Decimal("2.0"),
            "smart_dca_max_multiplier": Decimal("4.0"),
            "smart_dca_min_multiplier": Decimal("0.25")
        })

        updated_config = DcaConfig(**config_data)

        # 변경된 설정으로 SmartDCA 배수 계산
        # 20% 하락 시나리오
        multiplier = updated_config.calculate_smart_dca_multiplier(
            Decimal("40000"), Decimal("50000")
        )

        # SmartDCA가 활성화되어 배수가 1.0보다 커야 함
        assert multiplier > Decimal("1.0")
        assert multiplier <= Decimal("4.0")  # 최대 배수 제한

        # 극단적 상승 시나리오
        multiplier = updated_config.calculate_smart_dca_multiplier(
            Decimal("100000"), Decimal("50000")
        )

        assert multiplier >= Decimal("0.25")  # 최소 배수 제한
        assert multiplier < Decimal("1.0")
