"""
DCA 데이터 저장을 위한 레포지토리 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models.dca import (
    DcaConfig,
    DcaState,
)
from app.domain.models.trading import PriceHistory, PriceDataPoint


class DcaRepository(ABC):
    """DCA 데이터 레포지토리 추상 인터페이스"""

    @abstractmethod
    async def save_config(self, market: str, config: DcaConfig) -> bool:
        """DCA 설정을 저장합니다."""
        pass

    @abstractmethod
    async def get_config(self, market: str) -> DcaConfig | None:
        """DCA 설정을 조회합니다."""
        pass

    @abstractmethod
    async def save_state(self, market: str, state: DcaState) -> bool:
        """현재 DCA 상태를 저장합니다."""
        pass

    @abstractmethod
    async def get_state(self, market: str) -> DcaState | None:
        """현재 DCA 상태를 조회합니다."""
        pass

    @abstractmethod
    async def clear_market_data(self, market: str) -> bool:
        """특정 마켓의 모든 데이터를 삭제합니다."""
        pass

    @abstractmethod
    async def backup_state(self, market: str) -> dict[str, Any]:
        """현재 상태를 백업용 딕셔너리로 반환합니다."""
        pass

    @abstractmethod
    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """백업 데이터로부터 상태를 복원합니다."""
        pass

    @abstractmethod
    async def get_active_markets(self) -> list[str]:
        """현재 활성화된 DCA 마켓 목록을 반환합니다."""
        pass

    @abstractmethod
    async def save_price_data_point(
        self, market: str, price_data: PriceDataPoint
    ) -> bool:
        """가격 데이터 포인트를 저장합니다."""
        pass

    @abstractmethod
    async def get_price_history(
        self, market: str, max_periods: int = 50
    ) -> PriceHistory | None:
        """가격 히스토리를 조회합니다."""
        pass

    @abstractmethod
    async def cleanup_old_price_data(self, market: str, max_periods: int = 50) -> bool:
        """오래된 가격 데이터를 정리합니다."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """연결을 종료합니다."""
        pass
