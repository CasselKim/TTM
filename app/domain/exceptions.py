"""도메인 예외 클래스들"""


class ConfigSaveError(RuntimeError):
    """설정 저장 실패 예외"""

    def __init__(self) -> None:
        super().__init__("설정 저장에 실패했습니다.")


class StateSaveError(RuntimeError):
    """상태 저장 실패 예외"""

    def __init__(self) -> None:
        super().__init__("상태 저장에 실패했습니다.")


class DcaConfigError(ValueError):
    """DCA 설정 관련 예외"""

    pass


class ProfitRateError(DcaConfigError):
    """목표 수익률 오류"""

    def __init__(self) -> None:
        super().__init__("목표 수익률은 0보다 커야 합니다")


class PriceDropThresholdError(DcaConfigError):
    """추가 매수 트리거 오류"""

    def __init__(self) -> None:
        super().__init__("추가 매수 트리거는 음수여야 합니다")


class ForceStopLossError(DcaConfigError):
    """강제 손절률 오류"""

    def __init__(self) -> None:
        super().__init__("강제 손절률은 음수여야 합니다")


class MaxInvestmentRatioError(DcaConfigError):
    """최대 투자 비율 오류"""

    def __init__(self) -> None:
        super().__init__("최대 투자 비율은 0과 1 사이여야 합니다")
