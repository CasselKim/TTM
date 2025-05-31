"""도메인 상수 정의"""

from decimal import Decimal


class TradingConstants:
    """거래 관련 상수"""

    # Upbit 거래 수수료 (0.05%)
    UPBIT_TRADING_FEE_RATE = Decimal("0.0005")

    # 기본 최대 투자 비율 (10%)
    DEFAULT_MAX_INVESTMENT_RATIO = Decimal("0.1")

    # 기본 최소 주문 금액
    DEFAULT_MIN_ORDER_AMOUNT = Decimal("5000")

    # 기본 손절 비율 (5%)
    DEFAULT_STOP_LOSS_RATIO = Decimal("0.05")

    # 기본 익절 비율 (10%)
    DEFAULT_TAKE_PROFIT_RATIO = Decimal("0.1")


class DiscordConstants:
    """Discord 관련 상수"""

    # Discord 색상 코드
    COLOR_SUCCESS = 0x00FF00  # 녹색 - 매수, 성공
    COLOR_ERROR = 0xFF0000  # 빨간색 - 매도, 에러
    COLOR_INFO = 0x3498DB  # 파란색 - 정보

    # 기본 봇 설정
    DEFAULT_COMMAND_PREFIX = "!"


class AlgorithmConstants:
    """거래 알고리즘 관련 상수"""

    # SimpleTradingAlgorithm 임계값
    SIMPLE_BUY_THRESHOLD = Decimal("-0.05")  # -5%
    SIMPLE_SELL_THRESHOLD = Decimal("0.10")  # +10%

    # 매도 비율
    MIN_SELL_RATIO = Decimal("0.5")  # 최소 50%
    MAX_CONFIDENCE = Decimal("1.0")  # 최대 신뢰도


class NetworkConstants:
    """네트워크 통신 관련 상수"""

    # Upbit API
    UPBIT_API_BASE_URL = "https://api.upbit.com/v1"
