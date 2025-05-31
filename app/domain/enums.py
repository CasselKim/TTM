"""도메인 Enum 정의"""

from enum import Enum


class OrderSide(str, Enum):
    """주문 방향"""

    BID = "bid"  # 매수
    ASK = "ask"  # 매도


class OrderType(str, Enum):
    """주문 타입"""

    LIMIT = "limit"  # 지정가
    PRICE = "price"  # 시장가 매수
    MARKET = "market"  # 시장가 매도


class TradingAction(str, Enum):
    """거래 액션"""

    BUY = "BUY"  # 매수
    SELL = "SELL"  # 매도
    HOLD = "HOLD"  # 보유


class OrderStatus(str, Enum):
    """주문 상태"""

    WAIT = "wait"  # 대기
    DONE = "done"  # 체결 완료
    CANCEL = "cancel"  # 취소
    PARTIAL = "partial"  # 부분 체결


class MarketWarning(str, Enum):
    """마켓 경고 타입"""

    NONE = "NONE"  # 해당 사항 없음
    CAUTION = "CAUTION"  # 투자유의
