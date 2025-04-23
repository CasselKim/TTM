import pytest
from unittest.mock import Mock, patch
from app.infrastructure.external.adapter.upbit_adapter import UpbitAdapter
from app.infrastructure.external.upbit.exceptions import UpbitAPIException

pytestmark = pytest.mark.asyncio(scope="session")

@pytest.fixture
def upbit_adapter():
    return UpbitAdapter(
        access_key="test_access_key",
        secret_key="test_secret_key"
    )

@pytest.mark.asyncio
async def test_get_market_price_success(upbit_adapter):
    # Given
    market = "KRW-BTC"
    mock_response = [{
        "market": market,
        "trade_price": 50000000,
        "timestamp": 1234567890123
    }]
    
    with patch.object(upbit_adapter.client, 'get_ticker', return_value=mock_response):
        # When
        result = await upbit_adapter.get_market_price(market)
        
        # Then
        assert result == {
            "market": market,
            "price": 50000000,
            "timestamp": 1234567890123
        }
        upbit_adapter.client.get_ticker.assert_called_once_with(markets=market)

@pytest.mark.asyncio
async def test_get_market_price_empty_response(upbit_adapter):
    # Given
    market = "KRW-BTC"
    
    with patch.object(upbit_adapter.client, 'get_ticker', return_value=[]):
        # When/Then
        with pytest.raises(UpbitAPIException) as exc_info:
            await upbit_adapter.get_market_price(market)
        
        assert "No price data available" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_market_order_success(upbit_adapter):
    # Given
    market = "KRW-BTC"
    side = "bid"
    volume = "0.01"
    
    mock_response = {
        "uuid": "test-uuid",
        "market": market,
        "state": "wait"
    }
    
    with patch.object(upbit_adapter.client, 'create_order', return_value=mock_response):
        # When
        result = await upbit_adapter.create_market_order(market, side, volume)
        
        # Then
        assert result == {
            "order_id": "test-uuid",
            "market": market,
            "status": "wait"
        }
        upbit_adapter.client.create_order.assert_called_once_with(
            market=market,
            side=side,
            volume=volume,
            price=None,
            ord_type="market"
        )

@pytest.mark.asyncio
async def test_get_order_status_success(upbit_adapter):
    # Given
    order_id = "test-uuid"
    mock_response = {
        "uuid": order_id,
        "state": "done",
        "executed_volume": "0.01",
        "remaining_volume": "0.0"
    }
    
    with patch.object(upbit_adapter.client, 'get_order', return_value=mock_response):
        # When
        result = await upbit_adapter.get_order_status(order_id)
        
        # Then
        assert result == {
            "order_id": order_id,
            "status": "done",
            "executed_volume": "0.01",
            "remaining_volume": "0.0"
        }
        upbit_adapter.client.get_order.assert_called_once_with(uuid=order_id)

@pytest.mark.asyncio
async def test_adapter_error_handling(upbit_adapter):
    # Given
    market = "KRW-BTC"
    
    with patch.object(upbit_adapter.client, 'get_ticker', side_effect=Exception("API Error")):
        # When/Then
        with pytest.raises(UpbitAPIException) as exc_info:
            await upbit_adapter.get_market_price(market)
        
        assert "Failed to get market price" in str(exc_info.value) 