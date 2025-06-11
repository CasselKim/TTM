"""도메인 Enum 정의"""

from enum import StrEnum


class OrderSide(StrEnum):
    """주문 방향"""

    BID = "bid"  # 매수
    ASK = "ask"  # 매도


class OrderType(StrEnum):
    """주문 타입"""

    LIMIT = "limit"  # 지정가
    PRICE = "price"  # 시장가 매수
    MARKET = "market"  # 시장가 매도


class TradingAction(StrEnum):
    """거래 액션"""

    BUY = "BUY"  # 매수
    SELL = "SELL"  # 매도
    HOLD = "HOLD"  # 보유


class OrderStatus(StrEnum):
    """주문 상태"""

    WAIT = "wait"  # 대기
    DONE = "done"  # 체결 완료
    CANCEL = "cancel"  # 취소
    PARTIAL = "partial"  # 부분 체결


class MarketWarning(StrEnum):
    """마켓 경고 타입"""

    NONE = "NONE"  # 해당 사항 없음
    CAUTION = "CAUTION"  # 투자유의


class DcaStatus(StrEnum):
    """DCA 실행 상태"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class DcaPhase(StrEnum):
    """DCA 단계"""

    INACTIVE = "inactive"  # 비활성 상태
    INITIAL_BUY = "initial_buy"  # 초기 매수 단계
    ACCUMULATING = "accumulating"  # 추가 매수(물타기) 단계
    PROFIT_TAKING = "profit_taking"  # 익절 대기 단계
    FORCE_SELLING = "force_selling"  # 강제 손절 단계


class CycleStatus(StrEnum):
    """사이클 상태"""

    COMPLETED = "completed"
    FAILED = "failed"
    FORCE_STOPPED = "force_stopped"


class ActionTaken(StrEnum):
    """수행된 액션"""

    START = "start"
    STOP = "stop"
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXECUTE = "execute"
