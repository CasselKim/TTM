import pytest
from unittest.mock import Mock, patch
from app.adapters.external.upbit.adapter import UpbitAdapter
from app.adapters.external.upbit.exceptions import UpbitAPIException
from decimal import Decimal
from app.domain.models.account import Account, Balance
from app.domain.enums import Currency
from app.domain.models.ticker import Ticker, ChangeType, MarketState, MarketWarning

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
@patch('app.adapters.external.upbit.client.requests.request')
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

    btc_balance = next(b for b in account.balances if b.currency == "BTC")
    assert btc_balance.balance == Decimal("1.5")
    assert btc_balance.locked == Decimal("0")
    assert btc_balance.unit == "KRW"

    eth_balance = next(b for b in account.balances if b.currency == "ETH")
    assert eth_balance.balance == Decimal("2.0")
    assert eth_balance.locked == Decimal("0")
    assert eth_balance.unit == "KRW"

    # Verify request
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "accounts" in args[1]

@pytest.mark.asyncio
@patch('app.adapters.external.upbit.client.requests.request', side_effect=Exception("API Error"))
async def test_get_account_balance_api_error(mock_request, upbit_adapter):
    # Given/When/Then
    with pytest.raises(UpbitAPIException) as exc_info:
        await upbit_adapter.get_account_balance()

    assert str(exc_info.value) == "Failed to get account balance: API Error"


# Ticker 관련 테스트
@pytest.fixture
def mock_ticker_response():
    return [{
        "market": "KRW-BTC",
        "trade_price": 151133000.0,
        "prev_closing_price": 149878000.0,
        "change": "RISE",
        "change_price": 1255000.0,
        "change_rate": 0.0083734771,
        "signed_change_price": 1255000.0,
        "signed_change_rate": 0.0083734771,
        "opening_price": 149962000.0,
        "high_price": 151430000.0,
        "low_price": 149422000.0,
        "trade_volume": 0.00033175,
        "acc_trade_price": 89500621272.70941,
        "acc_trade_price_24h": 427604714815.5981,
        "acc_trade_volume": 594.35874932,
        "acc_trade_volume_24h": 2826.8372881,
        "highest_52_week_price": 163325000.0,
        "highest_52_week_date": "2025-01-20",
        "lowest_52_week_price": 72100000.0,
        "lowest_52_week_date": "2024-08-05",
        "trade_date": "20250524",
        "trade_time": "093325",
        "trade_date_kst": "20250524",
        "trade_time_kst": "183325",
        "trade_timestamp": 1748079205130,
        "timestamp": 1748079210049
    }]

@pytest.mark.asyncio
async def test_get_ticker_success(upbit_adapter, mock_ticker_response):
    """ticker 조회 성공 테스트"""
    with patch.object(upbit_adapter.client, 'get_ticker', return_value=mock_ticker_response):
        result = await upbit_adapter.get_ticker("KRW-BTC")

        assert isinstance(result, Ticker)
        assert result.market == "KRW-BTC"
        assert result.trade_price == Decimal("151133000.0")
        assert result.change == ChangeType.RISE
        assert result.market_state == MarketState.ACTIVE
        assert result.market_warning == MarketWarning.NONE

@pytest.mark.asyncio
async def test_get_ticker_empty_response(upbit_adapter):
    """ticker 조회 시 빈 응답 테스트"""
    with patch.object(upbit_adapter.client, 'get_ticker', return_value=[]):
        with pytest.raises(UpbitAPIException) as exc_info:
            await upbit_adapter.get_ticker("KRW-BTC")

        assert "No ticker data found for market: KRW-BTC" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_tickers_success(upbit_adapter, mock_ticker_response):
    """여러 ticker 조회 성공 테스트"""
    # ETH 데이터 추가
    eth_data = mock_ticker_response[0].copy()
    eth_data["market"] = "KRW-ETH"
    eth_data["trade_price"] = 3571000.0

    mock_response = mock_ticker_response + [eth_data]

    with patch.object(upbit_adapter.client, 'get_ticker', return_value=mock_response):
        result = await upbit_adapter.get_tickers(["KRW-BTC", "KRW-ETH"])

        assert len(result) == 2
        assert result[0].market == "KRW-BTC"
        assert result[1].market == "KRW-ETH"
        assert all(isinstance(ticker, Ticker) for ticker in result)

@pytest.mark.asyncio
async def test_get_ticker_api_error(upbit_adapter):
    """ticker 조회 시 API 에러 테스트"""
    with patch.object(upbit_adapter.client, 'get_ticker', side_effect=Exception("API Error")):
        with pytest.raises(UpbitAPIException) as exc_info:
            await upbit_adapter.get_ticker("KRW-BTC")

        assert "Failed to get ticker for KRW-BTC: API Error" in str(exc_info.value)
