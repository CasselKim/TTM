"""
TradingScheduler 테스트

거래 스케줄러의 시작/중지 및 기본 동작을 테스트합니다.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.internal.background.trading_scheduler import TradingScheduler
from app.application.dto.trading_dto import TradingResult
from app.application.usecase.trading_usecase import TradingUsecase
from app.domain.models.account import Currency
from app.domain.models.enums import TradingMode


class TestTradingScheduler:
    """TradingScheduler 테스트 클래스"""

    @pytest.fixture
    def mock_trading_usecase(self) -> Mock:
        """TradingUsecase 모킹"""
        mock = Mock(spec=TradingUsecase)
        mock.execute_trading_algorithm = AsyncMock()
        return mock

    @pytest.fixture
    def trading_scheduler(self, mock_trading_usecase: Mock) -> TradingScheduler:
        """테스트용 TradingScheduler 인스턴스"""
        return TradingScheduler(
            trading_usecase=mock_trading_usecase,
            interval_seconds=0.1,  # 테스트를 위해 짧은 간격 설정
            enabled=True,
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
        )

    @pytest.mark.asyncio
    async def test_scheduler_start_and_stop(
        self, trading_scheduler: TradingScheduler, mock_trading_usecase: Mock
    ):
        """스케줄러 시작과 중지 테스트"""
        # Given
        mock_trading_usecase.execute_trading_algorithm.return_value = TradingResult(
            success=True, message="HOLD 신호: 매매 조건 미충족"
        )

        # When - 스케줄러 시작
        await trading_scheduler.start()
        assert trading_scheduler._running is True
        assert trading_scheduler._task is not None

        # 잠시 기다려서 최소 한 번은 실행되도록
        await asyncio.sleep(0.2)

        # When - 스케줄러 중지
        await trading_scheduler.stop()

        # Then
        assert trading_scheduler._running is False
        assert mock_trading_usecase.execute_trading_algorithm.called

    @pytest.mark.asyncio
    async def test_scheduler_already_running_warning(
        self, trading_scheduler: TradingScheduler, mock_trading_usecase: Mock
    ):
        """이미 실행 중인 스케줄러 재시작 시 경고 테스트"""
        # Given
        mock_trading_usecase.execute_trading_algorithm.return_value = TradingResult(
            success=True, message="HOLD 신호"
        )

        # When - 첫 번째 시작
        await trading_scheduler.start()
        assert trading_scheduler._running is True

        # When - 두 번째 시작 시도 (이미 실행 중)
        await trading_scheduler.start()

        # Then - 여전히 하나의 태스크만 실행 중
        assert trading_scheduler._running is True

        # Cleanup
        await trading_scheduler.stop()

    @pytest.mark.asyncio
    async def test_trading_algorithm_execution(
        self, trading_scheduler: TradingScheduler, mock_trading_usecase: Mock
    ):
        """거래 알고리즘 실행 테스트"""
        # Given
        expected_result = TradingResult(
            success=True,
            message="시뮬레이션 매수 주문: 100000원",
            executed_amount=Decimal("100000"),
        )
        mock_trading_usecase.execute_trading_algorithm.return_value = expected_result

        # When
        await trading_scheduler.start()
        await asyncio.sleep(0.2)  # 최소 한 번 실행 대기
        await trading_scheduler.stop()

        # Then
        mock_trading_usecase.execute_trading_algorithm.assert_called_with(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=mock_trading_usecase.execute_trading_algorithm.call_args[1][
                "algorithm_type"
            ],
        )

    @pytest.mark.asyncio
    async def test_scheduler_disabled(self, mock_trading_usecase: Mock):
        """비활성화된 스케줄러 테스트"""
        # Given
        disabled_scheduler = TradingScheduler(
            trading_usecase=mock_trading_usecase,
            interval_seconds=0.1,
            enabled=False,  # 비활성화
        )

        # When
        await disabled_scheduler.start()
        await asyncio.sleep(0.2)
        await disabled_scheduler.stop()

        # Then - 비활성화되어 있으므로 호출되지 않음
        mock_trading_usecase.execute_trading_algorithm.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_exception_handling(
        self, trading_scheduler: TradingScheduler, mock_trading_usecase: Mock
    ):
        """스케줄러 예외 처리 테스트"""
        # Given - 거래 usecase에서 예외 발생
        mock_trading_usecase.execute_trading_algorithm.side_effect = Exception(
            "Test exception"
        )

        # When - 예외가 발생해도 스케줄러는 계속 실행되어야 함
        await trading_scheduler.start()
        await asyncio.sleep(0.2)
        await trading_scheduler.stop()

        # Then - 예외가 발생했지만 여전히 호출됨
        assert mock_trading_usecase.execute_trading_algorithm.called
