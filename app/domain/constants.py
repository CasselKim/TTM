from decimal import Decimal

from app.domain.enums import DcaPhase

# ==========================================================
# 🟢 Trading 관련 상수
# ==========================================================

TRADING_UPBIT_TRADING_FEE_RATE = Decimal("0.0005")
TRADING_DEFAULT_MAX_INVESTMENT_RATIO = Decimal("0.1")
TRADING_DEFAULT_MIN_ORDER_AMOUNT = Decimal("5000")
TRADING_DEFAULT_STOP_LOSS_RATIO = Decimal("0.05")
TRADING_DEFAULT_TAKE_PROFIT_RATIO = Decimal("0.1")

# ==========================================================
# 🔵 Discord 관련 상수
# ==========================================================

DISCORD_COLOR_SUCCESS = 0x00FF00  # 녹색 - 매수, 성공
DISCORD_COLOR_ERROR = 0xFF0000  # 빨간색 - 매도, 에러
DISCORD_COLOR_INFO = 0x3498DB  # 파란색 - 정보
DISCORD_COLOR_WARNING = 0xFFAA00  # 주황색 - 경고, 확인 요청

DISCORD_DEFAULT_COMMAND_PREFIX = "!"

DISCORD_MAX_TRADE_AMOUNT_KRW = 1_000_000  # 최대 거래 금액: 100만원
DISCORD_MAX_TRADE_VOLUME_BTC = Decimal("0.01")  # 최대 BTC 거래량: 0.01 BTC

DISCORD_TRADE_CONFIRMATION_TIMEOUT_SECONDS = 30.0  # 거래 확인 타임아웃: 30초

# 이모지
DISCORD_EMOJI_CONFIRM = "✅"
DISCORD_EMOJI_CANCEL = "❌"
DISCORD_EMOJI_BUY = "📈"
DISCORD_EMOJI_SELL = "📉"
DISCORD_EMOJI_INFO = "💡"
DISCORD_EMOJI_WARNING = "⚠️"
DISCORD_EMOJI_PROCESSING = "🔄"
DISCORD_EMOJI_SUCCESS = "✅"
DISCORD_EMOJI_ERROR = "❌"
DISCORD_EMOJI_TIMEOUT = "⏰"

DISCORD_EMBED_FIELD_MAX_LENGTH = 1024

DISCORD_ADMIN_USER_IDS: list[int] = []  # 실제 운영 환경에서 주입

# ==========================================================
# 🟣 알고리즘 관련 상수
# ==========================================================

ALGORITHM_MIN_SELL_RATIO = Decimal("0.5")  # 최소 50%
ALGORITHM_MAX_CONFIDENCE = Decimal("1.0")  # 최대 신뢰도

# ==========================================================
# 🟤 네트워크 관련 상수
# ==========================================================

NETWORK_UPBIT_API_BASE_URL = "https://api.upbit.com/v1"

# ==========================================================
# 🟡 DCA 관련 상수
# ==========================================================

DCA_DEFAULT_TARGET_PROFIT_RATE = Decimal("0.10")
DCA_DEFAULT_PRICE_DROP_THRESHOLD = Decimal("-0.05")
DCA_DEFAULT_MAX_BUY_ROUNDS = 10

DCA_DEFAULT_SCHEDULER_INTERVAL_SECONDS = 30.0
DCA_DEFAULT_ADD_BUY_MULTIPLIER = Decimal("1.5")

# DcaState 초기화 기본값들
DCA_DEFAULT_PHASE = DcaPhase.INACTIVE
DCA_DEFAULT_CURRENT_ROUND = 0
DCA_DEFAULT_TOTAL_INVESTMENT = 0
DCA_DEFAULT_TOTAL_VOLUME = Decimal("0")
DCA_DEFAULT_AVERAGE_PRICE = Decimal("0")
DCA_DEFAULT_LAST_BUY_PRICE = Decimal("0")
DCA_DEFAULT_TARGET_SELL_PRICE = Decimal("0")
