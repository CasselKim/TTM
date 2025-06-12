from decimal import Decimal
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.application.usecase.dca_usecase import DcaUsecase
from app.domain.models.account import Account, Balance
from app.domain.models.dca import DcaConfig, DcaResult, DcaState
from app.domain.models.ticker import Ticker, MarketState, MarketWarning, ChangeType
from app.domain.models.trading import MarketData
from app.domain.models.order import OrderResult, OrderRequest, Order
from app.domain.enums import TradingAction, ActionTaken, DcaStatus, OrderSide, OrderType, OrderState, DcaPhase
from app.domain.models.status import DcaMarketStatus, MarketName
from app.domain.services.dca_service import DcaService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_account_repository():
    return AsyncMock()


@pytest.fixture
def mock_order_repository():
    return AsyncMock()


@pytest.fixture
def mock_ticker_repository():
    return AsyncMock()


@pytest.fixture
def mock_dca_repository():
    return AsyncMock()


@pytest.fixture
def mock_notification_repo():
    return AsyncMock()


@pytest.fixture
def mock_dca_service():
    return Mock(spec=DcaService)


@pytest.fixture
def dca_usecase(
    mock_account_repository,
    mock_order_repository,
    mock_ticker_repository,
    mock_dca_repository,
    mock_notification_repo,
    mock_dca_service,
):
    return DcaUsecase(
        account_repository=mock_account_repository,
        order_repository=mock_order_repository,
        ticker_repository=mock_ticker_repository,
        dca_repository=mock_dca_repository,
        notification_repo=mock_notification_repo,
        dca_service=mock_dca_service,
    )


@pytest.fixture
def sample_account():
    return Account(
        balances=[
            Balance(
                currency="KRW",
                balance=Decimal("1000000"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("1"),
                unit="KRW",
            ),
            Balance(
                currency="BTC",
                balance=Decimal("0.1"),
                locked=Decimal("0"),
                avg_buy_price=Decimal("50000000"),
                unit="KRW",
            ),
        ]
    )


@pytest.fixture
def sample_ticker():
    return Ticker(
        market="KRW-BTC",
        trade_date="20240101",
        trade_time="120000",
        trade_date_kst="20240101",
        trade_time_kst="120000",
        trade_timestamp=1704067200000,
        opening_price=Decimal("50000000.0"),
        high_price=Decimal("51000000.0"),
        low_price=Decimal("49000000.0"),
        trade_price=Decimal("50500000.0"),
        prev_closing_price=Decimal("50000000.0"),
        change=ChangeType.RISE,
        change_price=Decimal("500000.0"),
        change_rate=Decimal("0.01"),
        signed_change_price=Decimal("500000.0"),
        signed_change_rate=Decimal("0.01"),
        trade_volume=Decimal("0.1"),
        acc_trade_price=Decimal("5050000000.0"),
        acc_trade_price_24h=Decimal("120000000000.0"),
        acc_trade_volume=Decimal("1000.0"),
        acc_trade_volume_24h=Decimal("2400.0"),
        highest_52_week_price=Decimal("60000000.0"),
        highest_52_week_date="2024-01-01",
        lowest_52_week_price=Decimal("30000000.0"),
        lowest_52_week_date="2024-01-01",
        market_state=MarketState.ACTIVE,
        market_warning=MarketWarning.NONE,
        timestamp=1704067200000,
    )


@pytest.fixture
def sample_config():
    return DcaConfig(
        initial_buy_amount=100000,
        target_profit_rate=Decimal("0.1"),
        price_drop_threshold=Decimal("-0.05"),
        max_buy_rounds=10,
    )


@pytest.fixture
def sample_state():
    state = DcaState(market="KRW-BTC")
    state.reset_cycle("KRW-BTC")
    return state


class TestDcaUsecaseStart:
    """DCA 시작 테스트"""

    async def test_start_success(
        self,
        dca_usecase,
        mock_dca_repository,
        mock_account_repository,
        mock_ticker_repository,
        mock_order_repository,
        mock_notification_repo,
        sample_account,
        sample_ticker,
    ):
        """DCA 시작 성공 테스트"""
        # Given
        market = "KRW-BTC"
        initial_buy_amount = 100000

        mock_dca_repository.get_state.return_value = None  # 기존 실행 중인 DCA 없음
        mock_dca_repository.save_config.return_value = True
        mock_dca_repository.save_state.return_value = True

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        sample_order = Order(
            uuid="test-order-123",
            side=OrderSide.BID,
            ord_type=OrderType.PRICE,
            price=Decimal("50000000"),
            state=OrderState.DONE,
            market="KRW-BTC",
            created_at="2024-01-01T12:00:00",
            volume=None,
            remaining_volume=Decimal("0"),
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=Decimal("0"),
            executed_volume=Decimal("0"),
            trades_count=0,
        )

        order_result = OrderResult(
            success=True,
            order=sample_order,
        )
        mock_order_repository.place_order.return_value = order_result

        # When
        with patch.object(dca_usecase.dca_service, 'execute_buy') as mock_execute_buy:
            mock_execute_buy.return_value = DcaResult(
                success=True,
                action_taken=ActionTaken.BUY,
                message="매수 완료",
            )

            result = await dca_usecase.start(
                market=market,
                initial_buy_amount=initial_buy_amount,
            )

        # Then
        assert result.success is True
        assert result.action_taken == ActionTaken.START
        assert "초기 매수가 완료" in result.message

        mock_dca_repository.save_config.assert_called_once()
        mock_dca_repository.save_state.assert_called()
        mock_order_repository.place_order.assert_called_once()
        mock_notification_repo.send_info_notification.assert_called_once()

    async def test_start_already_running(
        self,
        dca_usecase,
        mock_dca_repository,
        sample_state,
    ):
        """이미 실행 중인 DCA가 있을 때 테스트"""
        # Given
        market = "KRW-BTC"
        sample_state.phase = DcaPhase.ACCUMULATING  # is_active가 True가 되도록 설정
        mock_dca_repository.get_state.return_value = sample_state

        # When
        result = await dca_usecase.start(
            market=market,
            initial_buy_amount=100000,
        )

        # Then
        assert result.success is False
        assert "이미 실행 중" in result.message

    async def test_start_initial_buy_failed(
        self,
        dca_usecase,
        mock_dca_repository,
        mock_account_repository,
        mock_ticker_repository,
        mock_order_repository,
        sample_account,
        sample_ticker,
    ):
        """초기 매수 실패 테스트"""
        # Given
        market = "KRW-BTC"

        mock_dca_repository.get_state.return_value = None
        mock_dca_repository.save_config.return_value = True
        mock_dca_repository.save_state.return_value = True

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        order_result = OrderResult(
            success=False,
            error_message="잔고 부족",
        )
        mock_order_repository.place_order.return_value = order_result

        # When
        result = await dca_usecase.start(
            market=market,
            initial_buy_amount=100000,
        )

        # Then
        assert result.success is False
        assert "초기 매수 실패" in result.message
        mock_dca_repository.clear_market_data.assert_called_once_with(market)


class TestDcaUsecaseStop:
    """DCA 종료 테스트"""

    async def test_stop_success_with_position(
        self,
        dca_usecase,
        mock_dca_repository,
        mock_account_repository,
        mock_ticker_repository,
        mock_order_repository,
        mock_notification_repo,
        sample_account,
        sample_ticker,
        sample_config,
        sample_state,
    ):
        """보유 포지션이 있는 상태에서 DCA 종료 성공 테스트"""
        # Given
        market = "KRW-BTC"
        sample_state.phase = DcaPhase.ACCUMULATING  # is_active가 True가 되도록 설정

        mock_dca_repository.get_config.return_value = sample_config
        mock_dca_repository.get_state.return_value = sample_state

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        sample_sell_order = Order(
            uuid="sell-order-123",
            side=OrderSide.ASK,
            ord_type=OrderType.MARKET,
            price=None,
            state=OrderState.DONE,
            market="KRW-BTC",
            created_at="2024-01-01T12:00:00",
            volume=Decimal("0.1"),
            remaining_volume=Decimal("0"),
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=Decimal("0"),
            executed_volume=Decimal("0.1"),
            trades_count=1,
        )

        order_result = OrderResult(
            success=True,
            order=sample_sell_order,
        )
        mock_order_repository.place_order.return_value = order_result

        # When
        with patch.object(dca_usecase.dca_service, 'execute_sell') as mock_execute_sell:
            mock_execute_sell.return_value = DcaResult(
                success=True,
                action_taken=ActionTaken.SELL,
                message="매도 완료",
                profit_rate=Decimal("0.05"),
                profit_loss_amount_krw=5000,
            )

            result = await dca_usecase.stop(market=market)

        # Then
        assert result.success is True
        assert result.action_taken == ActionTaken.STOP

        mock_order_repository.place_order.assert_called_once()
        mock_dca_repository.clear_market_data.assert_called_once_with(market)
        mock_notification_repo.send_info_notification.assert_called()

    async def test_stop_not_running(
        self,
        dca_usecase,
        mock_dca_repository,
    ):
        """실행 중이 아닌 DCA 종료 시도 테스트"""
        # Given
        market = "KRW-BTC"
        mock_dca_repository.get_config.return_value = None
        mock_dca_repository.get_state.return_value = None

        # When
        result = await dca_usecase.stop(market=market)

        # Then
        assert result.success is False
        assert "실행 중이 아닙니다" in result.message


class TestDcaUsecaseRun:
    """DCA 실행 테스트"""

    async def test_run_buy_signal(
        self,
        dca_usecase,
        mock_dca_repository,
        mock_account_repository,
        mock_ticker_repository,
        sample_config,
        sample_state,
        sample_account,
        sample_ticker,
    ):
        """매수 신호 처리 테스트"""
        # Given
        market = "KRW-BTC"

        mock_dca_repository.get_config.return_value = sample_config
        mock_dca_repository.get_state.return_value = sample_state

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        with patch.object(dca_usecase.dca_service, 'analyze_signal') as mock_analyze_signal:
            from app.domain.models.trading import TradingSignal
            mock_analyze_signal.return_value = TradingSignal(
                action=TradingAction.BUY,
                confidence=Decimal("0.8"),
                reason="가격 하락 매수 신호",
            )

            with patch.object(dca_usecase, '_handle_buy_signal') as mock_handle_buy:
                mock_handle_buy.return_value = DcaResult(
                    success=True,
                    action_taken=ActionTaken.BUY,
                    message="매수 완료",
                )

                result = await dca_usecase.run(market=market)

        # Then
        assert result.success is True
        assert result.action_taken == ActionTaken.BUY
        mock_handle_buy.assert_called_once()

    async def test_run_hold_signal(
        self,
        dca_usecase,
        mock_dca_repository,
        mock_account_repository,
        mock_ticker_repository,
        sample_config,
        sample_state,
        sample_account,
        sample_ticker,
    ):
        """홀드 신호 처리 테스트"""
        # Given
        market = "KRW-BTC"

        mock_dca_repository.get_config.return_value = sample_config
        mock_dca_repository.get_state.return_value = sample_state

        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        with patch.object(dca_usecase.dca_service, 'analyze_signal') as mock_analyze_signal:
            from app.domain.models.trading import TradingSignal
            mock_analyze_signal.return_value = TradingSignal(
                action=TradingAction.HOLD,
                confidence=Decimal("0.5"),
                reason="매수 조건 미충족",
            )

            result = await dca_usecase.run(market=market)

        # Then
        assert result.success is True
        assert result.action_taken == ActionTaken.HOLD
        assert "매수 조건 미충족" in result.message


class TestDcaUsecaseInternalMethods:
    """Internal methods 테스트"""

    async def test_get_account_and_market_data(
        self,
        dca_usecase,
        mock_account_repository,
        mock_ticker_repository,
        sample_account,
        sample_ticker,
    ):
        """계좌 및 시장 데이터 조회 테스트"""
        # Given
        market = "KRW-BTC"
        mock_account_repository.get_account_balance.return_value = sample_account
        mock_ticker_repository.get_ticker.return_value = sample_ticker

        # When
        account, market_data = await dca_usecase._get_account_and_market_data(market)

        # Then
        assert account == sample_account
        assert isinstance(market_data, MarketData)
        assert market_data.market == market
        assert market_data.current_price == sample_ticker.trade_price

    async def test_create_dca_instance(
        self,
        dca_usecase,
        mock_dca_repository,
        sample_config,
        sample_state,
    ):
        """DCA 인스턴스 생성 테스트"""
        # Given
        market = "KRW-BTC"
        mock_dca_repository.get_config.return_value = sample_config
        mock_dca_repository.get_state.return_value = sample_state

        # When
        dca_data = await dca_usecase._create_dca_instance(market)

        # Then
        assert dca_data is not None
        config, state = dca_data
        assert config == sample_config
        assert state == sample_state

    async def test_create_dca_instance_no_data(
        self,
        dca_usecase,
        mock_dca_repository,
    ):
        """데이터 없는 상태에서 DCA 인스턴스 생성 테스트"""
        # Given
        market = "KRW-BTC"
        mock_dca_repository.get_config.return_value = None
        mock_dca_repository.get_state.return_value = None

        # When
        dca_data = await dca_usecase._create_dca_instance(market)

        # Then
        assert dca_data is None



    async def test_send_dca_notification(
        self,
        dca_usecase,
        mock_notification_repo,
    ):
        """DCA 알림 발송 테스트"""
        # Given
        title = "테스트 알림"
        message = "테스트 메시지"
        fields = [("필드1", "값1", True)]

        # When
        await dca_usecase._send_dca_notification(title, message, fields)

        # Then
        mock_notification_repo.send_info_notification.assert_called_once_with(
            title=title,
            message=message,
            fields=fields,
        )


class TestDcaUsecaseQueryMethods:
    """조회 메소드 테스트"""

    async def test_get_active_markets(
        self,
        dca_usecase,
        mock_dca_repository,
    ):
        """활성 마켓 조회 테스트"""
        # Given
        expected_markets = ["KRW-BTC", "KRW-ETH"]
        mock_dca_repository.get_active_markets.return_value = expected_markets

        # When
        result = await dca_usecase.get_active_markets()

        # Then
        assert result == expected_markets

    async def test_get_active_dca_summary(
        self,
        dca_usecase,
        mock_dca_repository,
    ):
        """활성 DCA 요약 조회 테스트"""
        # Given
        mock_dca_repository.get_active_markets.return_value = ["KRW-BTC"]

        with patch.object(dca_usecase, 'get_dca_market_status') as mock_get_status:
            mock_status = Mock()
            mock_status.current_round = 5
            mock_status.total_investment = 500000
            mock_status.average_price = Decimal("50000000")
            mock_status.current_profit_rate = Decimal("0.05")
            mock_status.cycle_id = "test-cycle-123"
            mock_get_status.return_value = mock_status

            mock_config = Mock()
            mock_config.max_buy_rounds = 10
            mock_dca_repository.get_config.return_value = mock_config

            # When
            result = await dca_usecase.get_active_dca_summary()

        # Then
        assert len(result) == 1
        summary = result[0]
        assert summary["market"] == "KRW-BTC"
        assert summary["symbol"] == "BTC"
        assert summary["current_round"] == 5
        assert summary["max_rounds"] == 10
