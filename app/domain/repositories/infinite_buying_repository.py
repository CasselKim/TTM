"""
무한매수법 데이터 저장을 위한 레포지토리 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models.infinite_buying import (
    BuyingRound,
    InfiniteBuyingConfig,
    InfiniteBuyingResult,
    InfiniteBuyingState,
)


class InfiniteBuyingRepository(ABC):
    """무한매수법 데이터 레포지토리 추상 인터페이스"""

    @abstractmethod
    async def save_config(self, market: str, config: InfiniteBuyingConfig) -> bool:
        """무한매수법 설정을 저장합니다."""
        pass

    @abstractmethod
    async def get_config(self, market: str) -> InfiniteBuyingConfig | None:
        """무한매수법 설정을 조회합니다."""
        pass

    @abstractmethod
    async def save_state(self, market: str, state: InfiniteBuyingState) -> bool:
        """현재 무한매수법 상태를 저장합니다."""
        pass

    @abstractmethod
    async def get_state(self, market: str) -> InfiniteBuyingState | None:
        """현재 무한매수법 상태를 조회합니다."""
        pass

    @abstractmethod
    async def add_buying_round(self, market: str, buying_round: BuyingRound) -> bool:
        """매수 회차를 추가합니다."""
        pass

    @abstractmethod
    async def get_buying_rounds(
        self, market: str, cycle_id: str | None = None
    ) -> list[BuyingRound]:
        """매수 회차 목록을 조회합니다. cycle_id가 없으면 현재 활성 사이클의 회차들을 반환합니다."""
        pass

    @abstractmethod
    async def save_cycle_history(
        self,
        market: str,
        cycle_id: str,
        state: InfiniteBuyingState,
        result: InfiniteBuyingResult,
    ) -> bool:
        """완료된 사이클 히스토리를 저장합니다."""
        pass

    @abstractmethod
    async def get_cycle_history(
        self, market: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """완료된 사이클 히스토리를 조회합니다."""
        pass

    @abstractmethod
    async def get_trade_statistics(self, market: str) -> dict[str, Any]:
        """거래 통계를 조회합니다."""
        pass

    @abstractmethod
    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """거래 통계를 업데이트합니다."""
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
