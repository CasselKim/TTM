"""공통 시간대 유틸리티.

UTC 혹은 naive datetime 객체를 Asia/Seoul(KST) tz-aware 객체로 변환하거나,
현재 KST 시각을 반환하는 헬퍼 함수를 제공한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Asia/Seoul 표준 시간대 객체 (tz-aware)
KST = ZoneInfo("Asia/Seoul")


def to_kst(dt: datetime) -> datetime:
    """datetime → KST 변환.

    1. tz 정보가 없으면 UTC 로 간주한다.
    2. tz 정보를 가진 경우 그대로 astimezone(KST) 변환한다.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def now_kst() -> datetime:
    """현재 시각(KST) 반환"""
    return datetime.now(tz=KST)
