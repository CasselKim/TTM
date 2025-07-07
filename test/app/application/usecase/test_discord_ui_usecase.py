"""Discord UI 유스케이스 테스트"""

import pytest
from unittest.mock import AsyncMock, Mock
from decimal import Decimal

from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.domain.models.dca import DcaConfig, DcaState, DcaResult
from app.domain.enums import ActionTaken, DcaPhase


class TestDiscordUIUseCaseDcaConfig:
    """Discord UI 유스케이스 DCA 설정 변경 테스트"""

    @pytest.fixture
    def mock_usecases(self):
        """모킹된 유스케이스들"""
        return {
            'account_usecase': AsyncMock(),
            'dca_usecase': AsyncMock(),
            'ticker_usecase': AsyncMock(),
            'dca_stats_usecase': AsyncMock()
        }

    @pytest.fixture
    def discord_ui_usecase(self, mock_usecases):
        """Discord UI 유스케이스 인스턴스"""
        return DiscordUIUseCase(
            account_usecase=mock_usecases['account_usecase'],
            dca_usecase=mock_usecases['dca_usecase'],
            ticker_usecase=mock_usecases['ticker_usecase'],
            dca_stats_usecase=mock_usecases['dca_stats_usecase']
        )

    @pytest.fixture
    def sample_config(self):
        """샘플 DCA 설정"""
        return DcaConfig(
            initial_buy_amount=10000,
            target_profit_rate=Decimal("0.10"),
            add_buy_multiplier=Decimal("1.5"),
            enable_smart_dca=False,
            max_buy_rounds=8,
            time_based_buy_interval_hours=72,
            enable_time_based_buying=True
        )

    async def test_update_dca_config_success(self, discord_ui_usecase, mock_usecases, sample_config):
        """DCA 설정 변경 성공 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        # update_config 성공 응답 모킹
        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # 설정 변경 실행
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.15"),
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.8")
        )

        # 검증
        assert result["success"] is True
        assert result["ticker"] == "BTC"
        assert result["market"] == market
        assert result["message"] == f"{market} DCA 설정이 변경되었습니다."

        # 업데이트된 설정 확인
        updated_config = result["updated_config"]
        assert updated_config["target_profit_rate"] == 0.15
        assert updated_config["enable_smart_dca"] is True
        assert updated_config["smart_dca_rho"] == 1.8

        # 변경되지 않은 값들이 유지되는지 확인
        assert updated_config["initial_buy_amount"] == 10000
        assert updated_config["add_buy_multiplier"] == 1.5

    async def test_update_dca_config_no_existing_config(self, discord_ui_usecase, mock_usecases):
        """존재하지 않는 DCA 설정 변경 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # 모킹 설정 - 설정이 없음
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = None

        # 설정 변경 실행
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.15")
        )

        # 검증
        assert result["success"] is False
        assert result["ticker"] == "BTC"
        assert result["market"] == market
        assert f"{market} DCA가 실행 중이 아닙니다." in result["message"]

    async def test_update_dca_config_partial_update(self, discord_ui_usecase, mock_usecases, sample_config):
        """부분 설정 변경 테스트"""
        user_id = "test_user_123"
        market = "KRW-ETH"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # 일부 설정만 변경
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            max_buy_rounds=12,
            enable_time_based_buying=False
        )

        # 검증
        assert result["success"] is True

        # update가 올바른 설정으로 호출되었는지 확인
        call_args = mock_usecases['dca_usecase'].update.call_args
        called_market = call_args[0][0]
        called_config = call_args[0][1]

        assert called_market == market
        assert called_config.max_buy_rounds == 12
        assert called_config.enable_time_based_buying is False

        # 변경되지 않은 값들이 유지되는지 확인
        assert called_config.target_profit_rate == Decimal("0.10")
        assert called_config.initial_buy_amount == 10000

    async def test_update_dca_config_smart_dca_activation(self, discord_ui_usecase, mock_usecases):
        """Smart DCA 활성화 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # Smart DCA 비활성화 상태의 기존 설정
        original_config = DcaConfig(enable_smart_dca=False)

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = original_config

        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # Smart DCA 활성화 및 관련 파라미터 설정
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            enable_smart_dca=True,
            smart_dca_rho=Decimal("2.0"),
            smart_dca_max_multiplier=Decimal("4.0"),
            smart_dca_min_multiplier=Decimal("0.25")
        )

        # 검증
        assert result["success"] is True

        # update에 전달된 설정 확인
        call_args = mock_usecases['dca_usecase'].update.call_args
        called_config = call_args[0][1]

        assert called_config.enable_smart_dca is True
        assert called_config.smart_dca_rho == Decimal("2.0")
        assert called_config.smart_dca_max_multiplier == Decimal("4.0")
        assert called_config.smart_dca_min_multiplier == Decimal("0.25")

    async def test_update_dca_config_time_based_settings(self, discord_ui_usecase, mock_usecases, sample_config):
        """시간 기반 매수 설정 변경 테스트"""
        user_id = "test_user_123"
        market = "KRW-DOGE"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # 시간 기반 매수 설정 변경
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            time_based_buy_interval_hours=24,
            enable_time_based_buying=False
        )

        # 검증
        assert result["success"] is True

        # update에 전달된 설정 확인
        call_args = mock_usecases['dca_usecase'].update.call_args
        called_config = call_args[0][1]

        assert called_config.time_based_buy_interval_hours == 24
        assert called_config.enable_time_based_buying is False

    async def test_update_dca_config_all_parameters(self, discord_ui_usecase, mock_usecases, sample_config):
        """모든 파라미터 변경 테스트"""
        user_id = "test_user_123"
        market = "KRW-ADA"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # 모든 파라미터 변경
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.20"),
            price_drop_threshold=Decimal("-0.03"),
            force_stop_loss_rate=Decimal("-0.30"),
            add_buy_multiplier=Decimal("2.0"),
            enable_smart_dca=True,
            smart_dca_rho=Decimal("1.8"),
            smart_dca_max_multiplier=Decimal("5.0"),
            smart_dca_min_multiplier=Decimal("0.2"),
            time_based_buy_interval_hours=48,
            enable_time_based_buying=False,
            max_buy_rounds=15
        )

        # 검증
        assert result["success"] is True

        # 반환된 설정 확인
        updated_config = result["updated_config"]
        assert updated_config["target_profit_rate"] == 0.20
        assert updated_config["price_drop_threshold"] == -0.03
        assert updated_config["force_stop_loss_rate"] == -0.30
        assert updated_config["add_buy_multiplier"] == 2.0
        assert updated_config["enable_smart_dca"] is True
        assert updated_config["smart_dca_rho"] == 1.8
        assert updated_config["smart_dca_max_multiplier"] == 5.0
        assert updated_config["smart_dca_min_multiplier"] == 0.2
        assert updated_config["time_based_buy_interval_hours"] == 48
        assert updated_config["enable_time_based_buying"] is False
        assert updated_config["max_buy_rounds"] == 15

    async def test_update_dca_config_usecase_failure(self, discord_ui_usecase, mock_usecases, sample_config):
        """유스케이스 실패 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        # update_config 실패 응답 모킹
        update_result = DcaResult(
            success=False,
            action_taken=ActionTaken.HOLD,
            message="설정 변경 실패: 유효하지 않은 값"
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # 설정 변경 실행
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.15")
        )

        # 검증
        assert result["success"] is False
        assert result["ticker"] == "BTC"
        assert result["market"] == market
        assert "설정 변경 실패: 유효하지 않은 값" in result["message"]

    async def test_update_dca_config_exception_handling(self, discord_ui_usecase, mock_usecases):
        """예외 처리 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # 모킹 설정 - 예외 발생
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.side_effect = Exception("Database connection error")

        # 설정 변경 실행
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.15")
        )

        # 검증
        assert result["success"] is False
        assert result["ticker"] == "BTC"
        assert result["market"] == market
        assert "Database connection error" in result["message"]

    async def test_update_dca_config_decimal_conversion(self, discord_ui_usecase, mock_usecases, sample_config):
        """Decimal 변환 테스트"""
        user_id = "test_user_123"
        market = "KRW-BTC"

        # 모킹 설정
        mock_dca_repo = AsyncMock()
        mock_usecases['dca_usecase'].dca_repository = mock_dca_repo
        mock_dca_repo.get_config.return_value = sample_config

        update_result = DcaResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=f"{market} DCA 설정이 변경되었습니다."
        )
        mock_usecases['dca_usecase'].update.return_value = update_result

        # float 값으로 설정 변경 (내부에서 Decimal로 변환되어야 함)
        result = await discord_ui_usecase.update_dca_config(
            user_id=user_id,
            market=market,
            target_profit_rate=Decimal("0.15"),  # Decimal로 전달
            add_buy_multiplier=Decimal("2.5")     # Decimal로 전달
        )

        # 검증
        assert result["success"] is True

        # update에 전달된 설정이 Decimal 타입인지 확인
        call_args = mock_usecases['dca_usecase'].update.call_args
        called_config = call_args[0][1]

        assert isinstance(called_config.target_profit_rate, Decimal)
        assert isinstance(called_config.add_buy_multiplier, Decimal)
        assert called_config.target_profit_rate == Decimal("0.15")
        assert called_config.add_buy_multiplier == Decimal("2.5")
