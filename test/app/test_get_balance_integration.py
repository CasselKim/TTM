import pytest
from decimal import Decimal
from unittest.mock import patch
from app.adapters.secondary.adapter.upbit_adapter import UpbitAdapter
from app.usecase.usecase.get_account_balance_usecase import GetAccountBalanceUseCase
from app.domain.models.account import Currency

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_upbit_client():
    with patch('app.adapters.secondary.adapter.upbit_adapter.UpbitClient') as mock:
        client = mock.return_value
        # Mock the get_accounts response
        client.get_accounts.return_value = [
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
        yield client

@pytest.mark.asyncio
async def test_get_balance_integration(mock_upbit_client):
    # Given
    adapter = UpbitAdapter(access_key="test_access_key", secret_key="test_secret_key")
    usecase = GetAccountBalanceUseCase(account_repository=adapter)

    # When
    result = await usecase.execute()

    # Then
    assert len(result.balances) == 2

    btc_balance = next(b for b in result.balances if b.currency == str(Currency.BTC))
    assert btc_balance.balance == '1.5'
    assert btc_balance.avg_buy_price == '50000000'
    assert btc_balance.unit == str(Currency.KRW)

    eth_balance = next(b for b in result.balances if b.currency == str(Currency.ETH))
    assert eth_balance.balance == '2.0'
    assert eth_balance.avg_buy_price == '3000000'
    assert eth_balance.unit == str(Currency.KRW)

    expected_total = str(Decimal('1.5') * Decimal('50000000') + Decimal('2.0') * Decimal('3000000'))
    assert result.total_balance_krw == expected_total 