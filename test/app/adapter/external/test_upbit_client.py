import pytest
import httpx
from unittest.mock import Mock, patch, ANY
from app.infrastructure.external.upbit.client import UpbitClient
from app.infrastructure.external.upbit.exceptions import UpbitAPIException

@pytest.fixture
def upbit_client():
    return UpbitClient(
        access_key="test_access_key",
        secret_key="test_secret_key"
    )

@pytest.fixture
def mock_response():
    response = Mock()
    response.raise_for_status = Mock()
    return response

def test_get_market_all(upbit_client, mock_response):
    # Given
    expected_data = [{"market": "KRW-BTC", "korean_name": "비트코인"}]
    mock_response.json.return_value = expected_data
    
    with patch.object(upbit_client.client, 'request', return_value=mock_response):
        # When
        result = upbit_client.get_market_all()
        
        # Then
        assert result == expected_data
        upbit_client.client.request.assert_called_once_with(
            "GET",
            "https://api.upbit.com/v1/market/all",
            params=None,
            headers={"Authorization": ANY}
        )

def test_get_ticker(upbit_client, mock_response):
    # Given
    market = "KRW-BTC"
    expected_data = [{
        "market": market,
        "trade_price": 50000000,
        "timestamp": 1234567890123
    }]
    mock_response.json.return_value = expected_data
    
    with patch.object(upbit_client.client, 'request', return_value=mock_response):
        # When
        result = upbit_client.get_ticker(markets=market)
        
        # Then
        assert result == expected_data
        upbit_client.client.request.assert_called_once_with(
            "GET",
            "https://api.upbit.com/v1/ticker",
            params={"markets": market},
            headers={"Authorization": ANY}
        )

def test_create_order(upbit_client, mock_response):
    # Given
    order_data = {
        "market": "KRW-BTC",
        "side": "bid",
        "volume": "0.01",
        "price": "50000000",
        "ord_type": "limit"
    }
    expected_data = {
        "uuid": "test-uuid",
        "market": order_data["market"],
        "state": "wait"
    }
    mock_response.json.return_value = expected_data
    
    with patch.object(upbit_client.client, 'request', return_value=mock_response):
        # When
        result = upbit_client.create_order(**order_data)
        
        # Then
        assert result == expected_data
        upbit_client.client.request.assert_called_once_with(
            "POST",
            "https://api.upbit.com/v1/orders",
            params=order_data,
            headers={"Authorization": ANY}
        )

def test_api_error_handling(upbit_client):
    # Given
    with patch.object(upbit_client.client, 'request') as mock_request:
        mock_request.side_effect = httpx.HTTPError("API Error")
        
        # When/Then
        with pytest.raises(UpbitAPIException) as exc_info:
            upbit_client.get_market_all()
        
        assert "API request failed" in str(exc_info.value) 