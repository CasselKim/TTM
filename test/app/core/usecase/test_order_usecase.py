from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, Mock

from app.usecase.usecase.order_usecase import (
    OrderUseCase,
    BuyWithAmountDTO,
    BuyWithMoneyDTO,
    SellWithAmountDTO,
    SellWithMoneyDTO
)
from app.domain.models.order import Order, OrderRequest, OrderResult, OrderSide, OrderType, OrderState
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_order_repository():
    """모의 주문 리포지토리"""
    return Mock(spec=OrderRepository)


@pytest.fixture
def mock_ticker_repository():
    """모의 티커 리포지토리"""
    return Mock(spec=TickerRepository)


@pytest.fixture
def order_usecase(mock_order_repository, mock_ticker_repository):
    """주문 유스케이스 인스턴스"""
    return OrderUseCase(mock_order_repository, mock_ticker_repository)


class TestOrderUseCase:

    @pytest.mark.asyncio
    async def test_buy_limit_success(self, order_usecase, mock_order_repository):
        """지정가 매수 성공 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")

        order = Order(
            uuid="test-uuid-123",
            side=OrderSide.매수,
            ord_type=OrderType.지정가,
            market=market,
            volume=volume,
            price=price,
            state=OrderState.대기,
            created_at="2023-01-01T00:00:00+09:00",
            remaining_volume=volume,
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=price * volume,
            executed_volume=Decimal("0"),
            trades_count=0
        )

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=True,
            order=order
        ))

        # When
        result = await order_usecase.buy_limit(market, volume, price)

        # Then
        assert result.success is True
        assert result.order_uuid == "test-uuid-123"
        assert result.market == market
        assert result.volume == str(volume)
        assert result.price == str(price)
        assert result.error_message is None

        # 올바른 주문 요청으로 호출되었는지 확인
        call_args = mock_order_repository.place_order.call_args[0][0]
        assert isinstance(call_args, OrderRequest)
        assert call_args.market == market
        assert call_args.side == OrderSide.매수
        assert call_args.ord_type == OrderType.지정가
        assert call_args.volume == volume
        assert call_args.price == price

    @pytest.mark.asyncio
    async def test_buy_limit_failure(self, order_usecase, mock_order_repository):
        """지정가 매수 실패 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")
        error_msg = "Insufficient balance"

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=False,
            error_message=error_msg
        ))

        # When
        result = await order_usecase.buy_limit(market, volume, price)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert result.error_message == error_msg

    @pytest.mark.asyncio
    async def test_buy_limit_exception(self, order_usecase, mock_order_repository):
        """지정가 매수 예외 발생 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")

        mock_order_repository.place_order = AsyncMock(side_effect=Exception("Network error"))

        # When
        result = await order_usecase.buy_limit(market, volume, price)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_buy_market_success(self, order_usecase, mock_order_repository):
        """시장가 매수 성공 테스트"""
        # Given
        market = "KRW-BTC"
        amount = Decimal("50000")

        order = Order(
            uuid="test-uuid-456",
            side=OrderSide.매수,
            ord_type=OrderType.시장가매수,
            market=market,
            volume=None,
            price=amount,
            state=OrderState.대기,
            created_at="2023-01-01T00:00:00+09:00",
            remaining_volume=Decimal("0"),
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=amount,
            executed_volume=Decimal("0"),
            trades_count=0
        )

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=True,
            order=order
        ))

        # When
        result = await order_usecase.buy_market(market, amount)

        # Then
        assert result.success is True
        assert result.order_uuid == "test-uuid-456"
        assert result.market == market
        assert result.amount == str(amount)
        assert result.error_message is None

        # 올바른 주문 요청으로 호출되었는지 확인
        call_args = mock_order_repository.place_order.call_args[0][0]
        assert isinstance(call_args, OrderRequest)
        assert call_args.market == market
        assert call_args.side == OrderSide.매수
        assert call_args.ord_type == OrderType.시장가매수
        assert call_args.price == amount
        assert call_args.volume is None

    @pytest.mark.asyncio
    async def test_buy_market_failure(self, order_usecase, mock_order_repository):
        """시장가 매수 실패 테스트"""
        # Given
        market = "KRW-BTC"
        amount = Decimal("50000")
        error_msg = "Insufficient balance"

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=False,
            error_message=error_msg
        ))

        # When
        result = await order_usecase.buy_market(market, amount)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert result.error_message == error_msg

    @pytest.mark.asyncio
    async def test_buy_market_exception(self, order_usecase, mock_order_repository):
        """시장가 매수 예외 발생 테스트"""
        # Given
        market = "KRW-BTC"
        amount = Decimal("50000")

        mock_order_repository.place_order = AsyncMock(side_effect=Exception("Network error"))

        # When
        result = await order_usecase.buy_market(market, amount)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_sell_limit_success(self, order_usecase, mock_order_repository):
        """지정가 매도 성공 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")

        order = Order(
            uuid="test-uuid-789",
            side=OrderSide.매도,
            ord_type=OrderType.지정가,
            market=market,
            volume=volume,
            price=price,
            state=OrderState.대기,
            created_at="2023-01-01T00:00:00+09:00",
            remaining_volume=volume,
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=volume,
            executed_volume=Decimal("0"),
            trades_count=0
        )

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=True,
            order=order
        ))

        # When
        result = await order_usecase.sell_limit(market, volume, price)

        # Then
        assert result.success is True
        assert result.order_uuid == "test-uuid-789"
        assert result.market == market
        assert result.volume == str(volume)
        assert result.price == str(price)
        assert result.error_message is None

        # 올바른 주문 요청으로 호출되었는지 확인
        call_args = mock_order_repository.place_order.call_args[0][0]
        assert isinstance(call_args, OrderRequest)
        assert call_args.market == market
        assert call_args.side == OrderSide.매도
        assert call_args.ord_type == OrderType.지정가
        assert call_args.volume == volume
        assert call_args.price == price

    @pytest.mark.asyncio
    async def test_sell_limit_failure(self, order_usecase, mock_order_repository):
        """지정가 매도 실패 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")
        error_msg = "Insufficient balance"

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=False,
            error_message=error_msg
        ))

        # When
        result = await order_usecase.sell_limit(market, volume, price)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert result.error_message == error_msg

    @pytest.mark.asyncio
    async def test_sell_limit_exception(self, order_usecase, mock_order_repository):
        """지정가 매도 예외 발생 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        price = Decimal("50000000")

        mock_order_repository.place_order = AsyncMock(side_effect=Exception("Network error"))

        # When
        result = await order_usecase.sell_limit(market, volume, price)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_sell_market_success(self, order_usecase, mock_order_repository):
        """시장가 매도 성공 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")

        order = Order(
            uuid="test-uuid-abc",
            side=OrderSide.매도,
            ord_type=OrderType.시장가매도,
            market=market,
            volume=volume,
            price=None,
            state=OrderState.대기,
            created_at="2023-01-01T00:00:00+09:00",
            remaining_volume=volume,
            reserved_fee=Decimal("0"),
            remaining_fee=Decimal("0"),
            paid_fee=Decimal("0"),
            locked=volume,
            executed_volume=Decimal("0"),
            trades_count=0
        )

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=True,
            order=order
        ))

        # When
        result = await order_usecase.sell_market(market, volume)

        # Then
        assert result.success is True
        assert result.order_uuid == "test-uuid-abc"
        assert result.market == market
        assert result.volume == str(volume)
        assert result.error_message is None

        # 올바른 주문 요청으로 호출되었는지 확인
        call_args = mock_order_repository.place_order.call_args[0][0]
        assert isinstance(call_args, OrderRequest)
        assert call_args.market == market
        assert call_args.side == OrderSide.매도
        assert call_args.ord_type == OrderType.시장가매도
        assert call_args.volume == volume
        assert call_args.price is None

    @pytest.mark.asyncio
    async def test_sell_market_failure(self, order_usecase, mock_order_repository):
        """시장가 매도 실패 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")
        error_msg = "Insufficient balance"

        mock_order_repository.place_order = AsyncMock(return_value=OrderResult(
            success=False,
            error_message=error_msg
        ))

        # When
        result = await order_usecase.sell_market(market, volume)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert result.error_message == error_msg

    @pytest.mark.asyncio
    async def test_sell_market_exception(self, order_usecase, mock_order_repository):
        """시장가 매도 예외 발생 테스트"""
        # Given
        market = "KRW-BTC"
        volume = Decimal("0.001")

        mock_order_repository.place_order = AsyncMock(side_effect=Exception("Network error"))

        # When
        result = await order_usecase.sell_market(market, volume)

        # Then
        assert result.success is False
        assert result.order_uuid is None
        assert "Network error" in result.error_message
