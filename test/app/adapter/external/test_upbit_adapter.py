import pytest
from unittest.mock import Mock, patch
from app.infrastructure.external.adapter.upbit_adapter import UpbitAdapter
from app.infrastructure.external.upbit.exceptions import UpbitAPIException
from decimal import Decimal
from app.domain.models.account import Account, Balance, Currency

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_response():
    mock = Mock()
    mock.json = Mock()
    mock.raise_for_status = Mock()
    return mock

@pytest.fixture
def upbit_adapter():
    return UpbitAdapter(access_key="test_access_key", secret_key="test_secret_key")

@pytest.mark.asyncio
@patch('app.infrastructure.external.upbit.client.requests.request')
async def test_get_account_balance_success(mock_request, upbit_adapter, mock_response):
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
    account = await upbit_adapter.get_account_balance()

    # Then
    assert isinstance(account, Account)
    assert len(account.balances) == 2
    
    btc_balance = next(b for b in account.balances if b.currency == Currency.BTC)
    assert btc_balance.balance == Decimal('1.5')
    assert btc_balance.avg_buy_price == Decimal('50000000')
    
    eth_balance = next(b for b in account.balances if b.currency == Currency.ETH)
    assert eth_balance.balance == Decimal('2.0')
    assert eth_balance.avg_buy_price == Decimal('3000000')

    # Verify request
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "accounts" in args[1]

@pytest.mark.asyncio
@patch('app.infrastructure.external.upbit.client.requests.request', side_effect=Exception("API Error"))
async def test_get_account_balance_api_error(mock_request, upbit_adapter):
    # Given/When/Then
    with pytest.raises(UpbitAPIException) as exc_info:
        await upbit_adapter.get_account_balance()
    
    assert str(exc_info.value) == "Failed to get account balance: API Error" 