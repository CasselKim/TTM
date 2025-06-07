"""도메인 예외 클래스들"""


class ConfigSaveError(RuntimeError):
    """설정 저장 실패 예외"""

    def __init__(self) -> None:
        super().__init__("설정 저장에 실패했습니다.")


class StateSaveError(RuntimeError):
    """상태 저장 실패 예외"""

    def __init__(self) -> None:
        super().__init__("상태 저장에 실패했습니다.")


class InfiniteBuyingConfigError(ValueError):
    """무한매수법 설정 관련 예외"""

    pass


class ProfitRateError(InfiniteBuyingConfigError):
    """목표 수익률 오류"""

    def __init__(self) -> None:
        super().__init__("목표 수익률은 0보다 커야 합니다")


class PriceDropThresholdError(InfiniteBuyingConfigError):
    """추가 매수 트리거 오류"""

    def __init__(self) -> None:
        super().__init__("추가 매수 트리거는 음수여야 합니다")


class ForceStopLossError(InfiniteBuyingConfigError):
    """강제 손절률 오류"""

    def __init__(self) -> None:
        super().__init__("강제 손절률은 음수여야 합니다")


class MaxInvestmentRatioError(InfiniteBuyingConfigError):
    """최대 투자 비율 오류"""

    def __init__(self) -> None:
        super().__init__("최대 투자 비율은 0과 1 사이여야 합니다")


class InsufficientLockAmountError(ValueError):
    """잠금 금액 부족 오류"""

    def __init__(self, amount: str, available: str) -> None:
        super().__init__(
            f"잠금 금액({amount})이 사용 가능 잔액({available})보다 큽니다"
        )


class InsufficientUnlockAmountError(ValueError):
    """잠금 해제 금액 부족 오류"""

    def __init__(self, amount: str, locked: str) -> None:
        super().__init__(f"해제 금액({amount})이 잠긴 금액({locked})보다 큽니다")


class UnsupportedAlgorithmError(ValueError):
    """지원하지 않는 알고리즘 오류"""

    def __init__(self, algorithm_type: str) -> None:
        super().__init__(f"지원하지 않는 알고리즘 타입: {algorithm_type}")
