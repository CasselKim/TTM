from abc import ABC, abstractmethod
from typing import Any


class CacheRepository(ABC):
    """캐시 리포지토리 추상 인터페이스"""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """키에 해당하는 값을 조회합니다."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """키-값을 저장합니다. ttl은 초 단위입니다."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """키를 삭제합니다."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """키가 존재하는지 확인합니다."""
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """키에 만료 시간을 설정합니다."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """캐시 서버 연결 상태를 확인합니다."""
        pass
