"""
TradingUsecase 테스트

매매 알고리즘 실행 UseCase의 단위 테스트
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from app.domain.models.account import Account, Balance, Currency
from app.domain.models.trading import TradingConfig, MarketData, TradingSignal
from app.domain.models.enums import TradingMode
from app.domain.models.ticker import Ticker, ChangeType, MarketState, MarketWarning
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.application.usecase.trading_usecase import TradingUsecase, AlgorithmType
from app.application.dto.trading_dto import TradingResult


class TestTradingUsecase:
    """TradingUsecase 테스트 클래스"""

    @pytest.fixture
    def mock_account_repository(self):
        """AccountRepository Mock"""
        mock = AsyncMock(spec=AccountRepository)
        return mock

    @pytest.fixture
    def mock_order_repository(self):
        """OrderRepository Mock"""
        mock = AsyncMock(spec=OrderRepository)
        return mock

    @pytest.fixture
    def mock_ticker_repository(self):
        """TickerRepository Mock"""
        mock = AsyncMock(spec=TickerRepository)
        return mock

    @pytest.fixture
    def trading_usecase(self, mock_account_repository, mock_order_repository, mock_ticker_repository):
        """TradingUsecase 인스턴스"""
        return TradingUsecase(
            account_repository=mock_account_repository,
            order_repository=mock_order_repository,
            ticker_repository=mock_ticker_repository,
        )

    @pytest.fixture
    def sample_account(self):
        """샘플 계좌 데이터"""
        return Account(
            balances=[
                Balance(
                    currency=Currency.KRW,
                    balance=Decimal("1000000"),  # 100만원
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("1"),
                    unit=Currency.KRW
                ),
                Balance(
                    currency=Currency.BTC,
                    balance=Decimal("0.1"),
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("50000000"),  # 5천만원
                    unit=Currency.KRW
                )
            ]
        )

    @pytest.fixture
    def sample_ticker(self):
        """샘플 티커 데이터"""
        return Ticker(
            market="KRW-BTC",
            trade_price=Decimal("50000000"),  # 5천만원
            prev_closing_price=Decimal("52000000"),
            change=ChangeType.FALL,
            change_price=Decimal("2000000"),
            change_rate=Decimal("0.038"),  # -3.8%
            signed_change_price=Decimal("-2000000"),
            signed_change_rate=Decimal("-0.038"),
            opening_price=Decimal("52000000"),
            high_price=Decimal("52500000"),
            low_price=Decimal("49500000"),
            trade_volume=Decimal("0.1"),
            acc_trade_price=Decimal("1000000000"),
            acc_trade_price_24h=Decimal("2000000000"),
            acc_trade_volume=Decimal("20"),
            acc_trade_volume_24h=Decimal("40"),
            highest_52_week_price=Decimal("80000000"),
            highest_52_week_date="2024-01-01",
            lowest_52_week_price=Decimal("30000000"),
            lowest_52_week_date="2024-06-01",
            trade_date="2024-01-15",
            trade_time="09:00:00",
            trade_date_kst="2024-01-15",
            trade_time_kst="18:00:00",
            trade_timestamp=1705276800,
            market_state=MarketState.ACTIVE,
            market_warning=MarketWarning.NONE,
            timestamp=1705276800000
        )

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_simulation_mode(
        self,
        trading_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_account,
        sample_ticker
    ):
        """시뮬레이션 모드 매매 알고리즘 실행 테스트"""
        # Given
        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        result = await trading_usecase.execute_trading_algorithm(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=AlgorithmType.SIMPLE,
            max_investment_ratio=Decimal("0.1"),
            min_order_amount=Decimal("5000")
        )

        # Then
        assert isinstance(result, TradingResult)
        assert result.success is True
        mock_account_repository.get_account_balance.assert_called_once()
        mock_ticker_repository.get_ticker.assert_called_once_with("KRW-BTC")

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_buy_signal(
        self,
        trading_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_account,
        sample_ticker
    ):
        """매수 신호 발생 시 테스트"""
        # Given - 변동률을 -6%로 설정하여 매수 신호 발생
        sample_ticker.change_rate = Decimal("0.06")  # 6% (절댓값)
        sample_ticker.signed_change_rate = Decimal("-0.06")  # -6% (실제 변동률)

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        result = await trading_usecase.execute_trading_algorithm(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=AlgorithmType.SIMPLE
        )

        # Then
        assert result.success is True
        assert "시뮬레이션" in result.message
        assert result.executed_amount is not None
        assert result.executed_price is not None

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_hold_signal(
        self,
        trading_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_account,
        sample_ticker
    ):
        """HOLD 신호 발생 시 테스트"""
        # Given - 변동률을 -2%로 설정하여 HOLD 신호 발생
        sample_ticker.change_rate = Decimal("0.02")  # 2% (절댓값)
        sample_ticker.signed_change_rate = Decimal("-0.02")  # -2% (매매 조건 미충족)

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        result = await trading_usecase.execute_trading_algorithm(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=AlgorithmType.SIMPLE
        )

        # Then
        assert result.success is True
        assert "HOLD" in result.message
        assert result.order_uuid is None

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_sell_signal(
        self,
        trading_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_account,
        sample_ticker
    ):
        """매도 신호 발생 시 테스트"""
        # Given - 변동률을 +12%로 설정하여 매도 신호 발생
        sample_ticker.change_rate = Decimal("0.12")  # 12% (절댓값)
        sample_ticker.signed_change_rate = Decimal("0.12")  # +12% (매도 임계값 +10% 이상)

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        result = await trading_usecase.execute_trading_algorithm(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=AlgorithmType.SIMPLE
        )

        # Then
        assert result.success is True
        assert "시뮬레이션" in result.message
        assert "매도" in result.message

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_insufficient_balance(
        self,
        trading_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_ticker
    ):
        """잔액 부족 시 테스트"""
        # Given - 잔액이 부족한 계좌
        insufficient_account = Account(
            balances=[
                Balance(
                    currency=Currency.KRW,
                    balance=Decimal("1000"),  # 1천원 (최소 주문 금액 미만)
                    locked=Decimal("0"),
                    avg_buy_price=Decimal("1"),
                    unit=Currency.KRW
                )
            ]
        )

        mock_account_repository.get_account_balance.return_value = insufficient_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        result = await trading_usecase.execute_trading_algorithm(
            target_currency=Currency.BTC,
            mode=TradingMode.SIMULATION,
            algorithm_type=AlgorithmType.SIMPLE
        )

        # Then
        assert result.success is False
        assert "계좌 상태가 거래에 적합하지 않습니다" in result.message

    @pytest.mark.asyncio
    async def test_create_algorithm_simple_type(self, trading_usecase):
        """SIMPLE 알고리즘 타입 생성 테스트"""
        # Given
        config = TradingConfig(
            mode=TradingMode.SIMULATION,
            target_currency=Currency.BTC
        )

        # When
        algorithm = trading_usecase._create_algorithm(AlgorithmType.SIMPLE, config)

        # Then
        from app.domain.services.simple_trading_algorithm import SimpleTradingAlgorithm
        assert isinstance(algorithm, SimpleTradingAlgorithm)

    def test_create_algorithm_unsupported_type(self, trading_usecase):
        """지원하지 않는 알고리즘 타입 테스트"""
        # Given
        config = TradingConfig(
            mode=TradingMode.SIMULATION,
            target_currency=Currency.BTC
        )

        # When & Then
        with pytest.raises(ValueError, match="지원하지 않는 알고리즘 타입"):
            # 존재하지 않는 알고리즘 타입으로 테스트
            trading_usecase._create_algorithm("INVALID_TYPE", config)  # type: ignore

    def test_get_trading_status(self, trading_usecase):
        """매매 상태 정보 조회 테스트"""
        # When
        status = trading_usecase.get_trading_status()

        # Then
        assert status["service"] == "TradingUsecase"
        assert "available_currencies" in status
        assert "available_modes" in status
        assert "available_algorithms" in status
        assert "default_config" in status

        # 기본 설정 값 확인
        default_config = status["default_config"]
        assert default_config["max_investment_ratio"] == "0.1"
        assert default_config["min_order_amount"] == "5000"

    @pytest.mark.asyncio
    async def test_execute_trading_algorithm_exception_handling(
        self,
        trading_usecase,
        mock_account_repository
    ):
        """예외 발생 시 처리 테스트"""
        # Given
        mock_account_repository.get_account_balance.side_effect = Exception("Database error")

        # When
        result = await trading_usecase.execute_trading_algorithm()

        # Then
        assert result.success is False
        assert "매매 사이클 실행 실패" in result.message
        assert "Database error" in result.message
