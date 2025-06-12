import pytest
from decimal import Decimal
from app.domain.models.account import Account, Balance
from app.domain.enums import Currency

def test_account_initialization():
    balance1 = Balance(
        currency="BTC",
        balance=Decimal("0.1"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("50000000"),
        unit="KRW"
    )
    balance2 = Balance(
        currency="ETH",
        balance=Decimal("1.0"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("3000000"),
        unit="DOGE"  # 다른 단위
    )

    account = Account(balances=[balance1, balance2])

    assert len(account.balances) == 2
    assert account.balances[0] == balance1
    assert account.balances[1] == balance2

def test_account_total_krw_balance():
    """계좌의 총 KRW 가치 계산 테스트"""
    balance1 = Balance(
        currency="BTC",
        balance=Decimal("0.1"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("50000000"),
        unit="KRW"
    )
    balance2 = Balance(
        currency="ETH",
        balance=Decimal("1.0"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("3000000"),
        unit="DOGE"  # 다른 단위
    )

    account = Account(balances=[balance1, balance2])

    # KRW 단위인 balance1만 포함되어야 함
    total_krw = account.total_balance_krw
    expected = Decimal("0.1") * Decimal("50000000")  # 5,000,000
    assert total_krw == expected

def test_account_krw_balances():
    """KRW 단위 잔액들만 필터링하는 테스트"""
    balance1 = Balance(
        currency="BTC",
        balance=Decimal("0.1"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("50000000"),
        unit="KRW"
    )
    balance2 = Balance(
        currency="ETH",
        balance=Decimal("1.0"),
        locked=Decimal("0"),
        avg_buy_price=Decimal("3000000"),
        unit="DOGE"  # 다른 단위
    )

    account = Account(balances=[balance1, balance2])

    krw_balances = list(account._krw_balances())
    assert len(krw_balances) == 1
    assert krw_balances[0].unit == "KRW"
    assert krw_balances[0].currency == "BTC"
