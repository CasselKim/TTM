"""
공통 Enum 정의

프로젝트 전반에서 사용되는 열거형들을 정의합니다.
"""

from enum import StrEnum


class TradingMode(StrEnum):
    """거래 모드"""

    SIMULATION = "simulation"  # 시뮬레이션
    LIVE = "live"  # 실거래
