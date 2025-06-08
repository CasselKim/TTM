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
        self.client: GlideClusterClient | None = None

    async def _get_client(self) -> GlideClusterClient:
        """Cache 클라이언트를 가져옵니다."""
        if self.client is None:
            try:
                Logger.set_logger_config(LogLevel.INFO)

                addresses = [NodeAddress(self._config.host, self._config.port)]
                cluster_config = GlideClusterClientConfiguration(
                    addresses=addresses,
                    use_tls=self._config.use_tls,
                    request_timeout=self._config.socket_timeout * 1000,  # milliseconds
                )

                self.client = await GlideClusterClient.create(cluster_config)
                logger.info(
                    f"Cache 서버에 연결되었습니다: "
                    f"{self._config.host}:{self._config.port}"
                )
            except (
                GlideTimeoutError,
                RequestError,
                GlideConnectionError,
                ClosingError,
            ):
                logger.exception("Cache 연결 실패")
                raise

        return self.client

    async def hget(self, key: str, field: str) -> str | None:
        """해시에서 필드 값을 조회합니다."""
        try:
            client = await self._get_client()
            value = await client.hget(key, field)
            logger.info(f"hget - key: {key}, field: {field}, value: {value}")
            if value is None:
                return None
            return value.decode("utf-8") if isinstance(value, bytes) else str(value)
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.exception(f"해시 조회 실패 - key: {key}, field: {field}, error: {e}")
            return None

    async def hset(self, key: str, field: str, value: str) -> bool:
        """해시에 필드 값을 저장합니다."""
        try:
            client = await self._get_client()
            await client.hset(key, {field: value})
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.exception(f"해시 저장 실패 - key: {key}, field: {field}, error: {e}")
            return False
        else:
            return True

    async def hgetall(self, key: str) -> dict[str, str]:
        """해시의 모든 필드와 값을 조회합니다."""
        try:
            client = await self._get_client()
            result = await client.hgetall(key)
            if result is None:
                return {}
            # bytes를 str로 변환
            return {
                k.decode("utf-8") if isinstance(k, bytes) else str(k): v.decode("utf-8")
                if isinstance(v, bytes)
                else str(v)
                for k, v in result.items()
            }
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.exception(f"해시 전체 조회 실패 - key: {key}, error: {e}")
            return {}

    async def hdel(self, key: str, field: str) -> bool:
        """해시에서 필드를 삭제합니다."""
        try:
            client = await self._get_client()
            await client.hdel(key, [field])
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.exception(
                f"해시 필드 삭제 실패 - key: {key}, field: {field}, error: {e}"
            )
            return False
        else:
            return True

    async def close(self) -> None:
        """캐시 클라이언트 연결을 종료합니다."""
        if self.client:
            try:
                await self.client.close()
                self.client = None
                logger.info("Cache 클라이언트 연결 종료")
            except Exception as e:
                logger.exception(f"Cache 클라이언트 종료 실패: {e}")
