import json
import logging
from typing import Any

import redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

from app.adapters.external.cache.config import CacheConfig
from app.domain.repositories.cache_repository import CacheRepository

logger = logging.getLogger(__name__)


class ValkeyAdapter(CacheRepository):
    """AWS ElastiCache Valkey 어댑터"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._connection_pool: redis.ConnectionPool | None = None
        self._client: redis.Redis[bytes] | None = None

    def _get_client(self) -> redis.Redis[bytes]:
        """Redis 클라이언트를 반환합니다. 필요시 연결을 생성합니다."""
        if self._client is None:
            retry_policy = Retry(ExponentialBackoff(), retries=3)

            self._connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=self.config.decode_responses,
            )

            self._client = redis.Redis(
                connection_pool=self._connection_pool,
                retry_on_timeout=self.config.retry_on_timeout,
                retry=retry_policy,
            )

            logger.info(
                f"Valkey 클라이언트 연결 생성: {self.config.host}:{self.config.port}"
            )

        return self._client

    async def get(self, key: str) -> Any | None:
        """키에 해당하는 값을 조회합니다."""
        try:
            client = self._get_client()
            value = client.get(key)
            if value is None:
                return None

            # JSON 역직렬화 시도
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"캐시 조회 실패 - key: {key}, error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """키-값을 저장합니다. ttl은 초 단위입니다."""
        try:
            client = self._get_client()

            # JSON 직렬화 시도
            if isinstance(value, dict | list | tuple):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)

            result = client.set(key, serialized_value, ex=ttl)
            logger.debug(f"캐시 저장 - key: {key}, ttl: {ttl}")
            return bool(result)

        except Exception as e:
            logger.error(f"캐시 저장 실패 - key: {key}, error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """키를 삭제합니다."""
        try:
            client = self._get_client()
            result = client.delete(key)
            logger.debug(f"캐시 삭제 - key: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"캐시 삭제 실패 - key: {key}, error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """키가 존재하는지 확인합니다."""
        try:
            client = self._get_client()
            result = client.exists(key)
            return bool(result)

        except Exception as e:
            logger.error(f"캐시 존재 확인 실패 - key: {key}, error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """키에 만료 시간을 설정합니다."""
        try:
            client = self._get_client()
            result = client.expire(key, ttl)
            logger.debug(f"캐시 만료 시간 설정 - key: {key}, ttl: {ttl}")
            return bool(result)

        except Exception as e:
            logger.error(f"캐시 만료 시간 설정 실패 - key: {key}, error: {e}")
            return False

    async def ping(self) -> bool:
        """캐시 서버 연결 상태를 확인합니다."""
        try:
            client = self._get_client()
            result = client.ping()
            return bool(result)

        except Exception as e:
            logger.error(f"캐시 연결 확인 실패 - error: {e}")
            return False

    def close(self) -> None:
        """연결을 종료합니다."""
        if self._client:
            self._client.close()
            logger.info("Valkey 클라이언트 연결 종료")

        if self._connection_pool:
            self._connection_pool.disconnect()
            logger.info("Valkey 연결 풀 종료")
