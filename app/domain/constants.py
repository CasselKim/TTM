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
    COLOR_WARNING = 0xFFAA00  # 주황색 - 경고, 확인 요청

    # 기본 봇 설정
    DEFAULT_COMMAND_PREFIX = "!"

    # 거래 커맨드 제한
    MAX_TRADE_AMOUNT_KRW = 1_000_000  # 최대 거래 금액: 100만원
    MAX_TRADE_VOLUME_BTC = Decimal("0.01")  # 최대 BTC 거래량: 0.01 BTC

    # 타임아웃 설정
    TRADE_CONFIRMATION_TIMEOUT_SECONDS = 30.0  # 거래 확인 타임아웃: 30초

    # 이모지
    EMOJI_CONFIRM = "✅"
    EMOJI_CANCEL = "❌"
    EMOJI_BUY = "📈"
    EMOJI_SELL = "📉"
    EMOJI_INFO = "💡"
    EMOJI_WARNING = "⚠️"
    EMOJI_PROCESSING = "🔄"
    EMOJI_SUCCESS = "✅"
    EMOJI_ERROR = "❌"
    EMOJI_TIMEOUT = "⏰"

    # Discord embed 필드 최대 길이
    EMBED_FIELD_MAX_LENGTH = 1024

    # Discord 관리자 사용자 ID 목록 (DM 용)
    # 실제 운영 시 .env 또는 설정 파일에서 주입하도록 하며, 여기서는 기본값을 빈 리스트로 둡니다.
    ADMIN_USER_IDS: list[int] = []


class AlgorithmConstants:
    """거래 알고리즘 관련 상수"""

    # 매도 비율
    MIN_SELL_RATIO = Decimal("0.5")  # 최소 50%
    MAX_CONFIDENCE = Decimal("1.0")  # 최대 신뢰도


class NetworkConstants:
    """네트워크 통신 관련 상수"""

    # Upbit API
    UPBIT_API_BASE_URL = "https://api.upbit.com/v1"


class DcaConstants:
    """DCA 관련 상수"""

    # 기본 목표 수익률 (10%)
    DEFAULT_TARGET_PROFIT_RATE = Decimal("0.10")

    # 추가 매수 트리거 하락률 (-5%)
    DEFAULT_PRICE_DROP_THRESHOLD = Decimal("-0.05")

    # 최대 매수 회차 (10회)
    DEFAULT_MAX_BUY_ROUNDS = 10

    # DCA 스케줄러 기본 실행 주기 (초)
    DEFAULT_SCHEDULER_INTERVAL_SECONDS = 30.0
