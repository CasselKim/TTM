import pytest
import httpx
from unittest.mock import Mock, patch, ANY
from app.adapters.secondary.upbit.client import UpbitClient
from app.adapters.secondary.upbit.exceptions import UpbitAPIException

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

@pytest.mark.asyncio
@patch('app.adapters.secondary.upbit.client.requests.request')
async def test_get_accounts_success(mock_request, upbit_client, mock_response):
    # Given
    mock_data = [
        {
            "currency": "BTC",
            "balance": "1.5",
            "locked": "0.0",
            "avg_buy_price": "50000000",
            "unit_currency": "KRW"
        },
        {
            "currency": "ETH",
            "balance": "2.0",
            "locked": "0.0",
            "avg_buy_price": "3000000",
            "unit_currency": "KRW"
        }
    ]
    mock_response.json.return_value = mock_data
    mock_request.return_value = mock_response

    # When
    result = upbit_client.get_accounts()

    # Then
    assert result == mock_data
    mock_request.assert_called_once_with(
        "GET",
        "https://api.upbit.com/v1/accounts",
        params=None,
        headers={
            "Authorization": ANY,
            "Content-Type": "application/json",
            "Charset": "UTF-8"
        }
    )

@pytest.mark.asyncio
@patch('app.adapters.secondary.upbit.client.requests.request', side_effect=Exception("API Error"))
async def test_get_accounts_api_error(mock_request, upbit_client):
    # Given/When/Then
    with pytest.raises(Exception) as exc_info:
        upbit_client.get_accounts()

    assert str(exc_info.value) == "API Error"
