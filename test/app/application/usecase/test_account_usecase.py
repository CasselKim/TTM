from decimal import Decimal
import pytest
from unittest.mock import Mock, AsyncMock
from app.application.dto.account_dto import AccountBalanceDTO
from app.application.usecase.account_usecase import AccountUseCase
from app.domain.models.account import Account, Balance
from app.domain.enums import Currency

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_account_repository():
    return AsyncMock()

@pytest.fixture
def mock_notification_repo():
    return AsyncMock()

@pytest.fixture
def account_usecase(mock_account_repository, mock_notification_repo):
    return AccountUseCase(account_repository=mock_account_repository, notification_repo=mock_notification_repo)

async def test_account_usecase_get_balance(account_usecase, mock_account_repository):
    # Given
    mock_account = Account(
        balances=[
            Balance(
                currency="BTC",
                balance=Decimal('1.5'),
                locked=Decimal('0.0'),
                avg_buy_price=Decimal('50000000'),
                unit="KRW"
            ),
            Balance(
                currency="ETH",
                balance=Decimal('2.0'),
                locked=Decimal('0.0'),
                avg_buy_price=Decimal('3000000'),
                unit="KRW"
            )
        ]
    )
    mock_account_repository.get_account_balance.return_value = mock_account

    # When
    result = await account_usecase.get_balance()

    # Then
    assert isinstance(result, AccountBalanceDTO)
    assert len(result.balances) == 2

    btc_balance = next(b for b in result.balances if b.currency == "BTC")
    assert btc_balance.balance == '1.5'
    assert btc_balance.avg_buy_price == '50000000'

    eth_balance = next(b for b in result.balances if b.currency == "ETH")
    assert eth_balance.balance == '2.0'
    assert eth_balance.avg_buy_price == '3000000'

    expected_total = str(Decimal('1.5') * Decimal('50000000') + Decimal('2.0') * Decimal('3000000'))
    assert result.total_balance_krw == expected_total
