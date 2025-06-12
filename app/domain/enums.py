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


# ==========================================================
# OrderState Enum
# ==========================================================


class OrderState(StrEnum):
    """주문 상태"""

    WAIT = "wait"  # 대기
    WATCH = "watch"  # 모니터링 중
    DONE = "done"  # 완료(체결)
    CANCEL = "cancel"  # 취소


# ==========================================================
# Currency Type
# ==========================================================

# Currency는 단순히 문자열로 처리합니다 (BTC, ETH, KRW 등)
Currency = str
