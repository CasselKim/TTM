from decimal import Decimal
import pytest
from unittest.mock import Mock, AsyncMock
from app.usecase.usecase.get_account_balance_usecase import GetAccountBalanceUseCase, AccountBalanceDTO
from app.domain.models.account import Account, Balance, Currency

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_account_repository():
    return AsyncMock()

@pytest.fixture
def get_account_balance_usecase(mock_account_repository):
    return GetAccountBalanceUseCase(account_repository=mock_account_repository)

async def test_get_account_balance_usecase_execute(get_account_balance_usecase, mock_account_repository):
    # Given
    mock_account = Account(
        balances=[
            Balance(
                currency=Currency.BTC,
                balance=Decimal('1.5'),
                locked=Decimal('0.0'),
                avg_buy_price=Decimal('50000000'),
                unit=Currency.KRW
            ),
            Balance(
                currency=Currency.ETH,
                balance=Decimal('2.0'),
                locked=Decimal('0.0'),
                avg_buy_price=Decimal('3000000'),
                unit=Currency.KRW
            )
        ]
    )
    mock_account_repository.get_account_balance.return_value = mock_account

    # When
    result = await get_account_balance_usecase.execute()

    # Then
    assert isinstance(result, AccountBalanceDTO)
    assert len(result.balances) == 2

    btc_balance = next(b for b in result.balances if b.currency == str(Currency.BTC))
    assert btc_balance.balance == '1.5'
    assert btc_balance.avg_buy_price == '50000000'

    eth_balance = next(b for b in result.balances if b.currency == str(Currency.ETH))
    assert eth_balance.balance == '2.0'
    assert eth_balance.avg_buy_price == '3000000'

    expected_total = str(Decimal('1.5') * Decimal('50000000') + Decimal('2.0') * Decimal('3000000'))
    assert result.total_balance_krw == expected_total
