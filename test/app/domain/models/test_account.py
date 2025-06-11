from decimal import Decimal
from app.domain.models.account import Account, Balance
from app.domain.enums import Currency

def test_account_total_balance_krw():
    # Given
    balances = [
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
    account = Account(balances=balances)

    # When
    total_balance = account.total_balance_krw

    # Then
    expected = Decimal('1.5') * Decimal('50000000') + Decimal('2.0') * Decimal('3000000')
    assert total_balance == expected

def test_account_krw_balances():
    # Given
    balances = [
        Balance(
            currency=Currency.BTC,
            balance=Decimal('1.0'),
            locked=Decimal('0.0'),
            avg_buy_price=Decimal('50000000'),
            unit=Currency.KRW
        ),
        Balance(
            currency=Currency.ETH,
            balance=Decimal('1.0'),
            locked=Decimal('0.0'),
            avg_buy_price=Decimal('3000000'),
            unit=Currency.DOGE  # 다른 단위
        )
    ]
    account = Account(balances=balances)

    # When
    krw_balances = list(account._krw_balances())

    # Then
    assert len(krw_balances) == 1
    assert krw_balances[0].unit == Currency.KRW
    assert krw_balances[0].currency == Currency.BTC
