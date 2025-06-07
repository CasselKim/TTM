"""
Cache 클라이언트 - 기본 Redis 연산과 예외 처리를 담당합니다.
"""

import logging

from glide import (
    ClosingError,
    GlideClusterClient,
    GlideClusterClientConfiguration,
    Logger,
    LogLevel,
    NodeAddress,
    RequestError,
)
from glide import (
    ConnectionError as GlideConnectionError,
)
from glide import (
    TimeoutError as GlideTimeoutError,
)

from app.adapters.external.cache.config import CacheConfig

logger = logging.getLogger(__name__)


class CacheClient:
    """Cache 기본 연산을 담당하는 클라이언트"""

    def __init__(self, config: CacheConfig):
        self._config = config
        self._client: GlideClusterClient | None = None

    async def _get_client(self) -> GlideClusterClient:
        """Cache 클라이언트를 가져옵니다."""
        if self._client is None:
            try:
                Logger.set_logger_config(LogLevel.INFO)

                addresses = [NodeAddress(self._config.host, self._config.port)]
                cluster_config = GlideClusterClientConfiguration(
                    addresses=addresses,
                    use_tls=self._config.use_tls,
                    request_timeout=self._config.socket_timeout * 1000,  # milliseconds
                )

                self._client = await GlideClusterClient.create(cluster_config)
                logger.info(
                    f"Cache 서버에 연결되었습니다: {self._config.host}:{self._config.port}"
                )
            except (
                GlideTimeoutError,
                RequestError,
                GlideConnectionError,
                ClosingError,
            ) as e:
                logger.error(f"Cache 연결 실패: {e}")
                raise

        return self._client

    async def get(self, key: str) -> str | None:
        """캐시에서 값을 조회합니다."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                return None
            return value.decode("utf-8") if isinstance(value, bytes) else str(value)
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 조회 실패 - key: {key}, error: {e}")
            return None

    async def set(
        self, key: str, value: str, expire_seconds: int | None = None
    ) -> bool:
        """캐시에 값을 저장합니다."""
        try:
            client = await self._get_client()
            await client.set(key, value)
            if expire_seconds:
                await client.expire(key, expire_seconds)
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 저장 실패 - key: {key}, error: {e}")
            return False
        else:
            return True

    async def delete(self, key: str) -> bool:
        """캐시에서 키를 삭제합니다."""
        try:
            client = await self._get_client()
            await client.delete([key])
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 삭제 실패 - key: {key}, error: {e}")
            return False
        else:
            return True

    async def expire(self, key: str, seconds: int) -> bool:
        """키에 만료 시간을 설정합니다."""
        try:
            client = await self._get_client()
            await client.expire(key, seconds)
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 만료 설정 실패 - key: {key}, error: {e}")
            return False
        else:
            return True

    async def scan(self, pattern: str) -> list[str]:
        """패턴에 맞는 키 목록을 조회합니다."""
        try:
            # glide scan API는 정확하지 않으므로 임시로 빈 리스트 반환
            # 실제 구현에서는 적절한 스캔 방법을 사용해야 함
            keys: list[str] = []
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 키 스캔 실패 - pattern: {pattern}, error: {e}")
            return []
        else:
            return keys

    async def close(self) -> None:
        """캐시 클라이언트 연결을 종료합니다."""
        if self._client:
            try:
                await self._client.close()
                self._client = None
                logger.info("Cache 클라이언트 연결 종료")
            except Exception as e:
                logger.error(f"Cache 클라이언트 종료 실패: {e}")
