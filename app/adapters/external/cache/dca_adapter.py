"""
Cache를 사용한 DCA 데이터 저장 어댑터
"""

import logging
from typing import Any

from app.adapters.external.cache.client import CacheClient
from app.adapters.external.cache.config import CacheConfig
from app.domain.models.dca import (
    DcaConfig,
    DcaState,
)
from app.domain.repositories.dca_repository import DcaRepository

logger = logging.getLogger(__name__)


class CacheDcaRepository(DcaRepository):
    """Cache 기반 DCA 데이터 저장소"""

    KEY_CONFIG = "dca:config"
    KEY_STATE = "dca:state"

    def __init__(self, config: CacheConfig):
        self.client = CacheClient(config)

    async def save_config(self, market: str, config: DcaConfig) -> bool:
        """DCA 설정을 저장합니다."""
        value = config.to_cache_json()
        return await self.client.hset(self.KEY_CONFIG, market, value)

    async def get_config(self, market: str) -> DcaConfig | None:
        """DCA 설정을 조회합니다."""
        data = await self.client.hget(self.KEY_CONFIG, market)
        if not data:
            return None
        return DcaConfig.from_cache_json(data)

    async def save_state(self, market: str, state: DcaState) -> bool:
        """DCA 상태를 저장합니다."""
        value = state.to_cache_json()
        return await self.client.hset(self.KEY_STATE, market, value)

    async def get_state(self, market: str) -> DcaState | None:
        """DCA 상태를 조회합니다."""
        data = await self.client.hget(self.KEY_STATE, market)
        if not data:
            return None
        return DcaState.from_cache_json(data)

    async def clear_market_data(self, market: str) -> bool:
        """마켓의 모든 데이터를 삭제합니다."""
        success = True

        keys = [self.KEY_CONFIG, self.KEY_STATE]
        for key in keys:
            if not await self.client.hdel(key, market):
                success = False

        return success

    async def backup_state(self, market: str) -> dict[str, Any]:
        """상태를 백업합니다."""
        backup_data: dict[str, Any] = {}

        keys = {
            "config": self.KEY_CONFIG,
            "state": self.KEY_STATE,
        }

        for data_type, key in keys.items():
            data = await self.client.hget(key, market)
            if data:
                backup_data[data_type] = data

        return backup_data

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """상태를 복원합니다."""
        success = True

        key_mapping = {
            "config": self.KEY_CONFIG,
            "state": self.KEY_STATE,
        }

        for data_type, data in backup_data.items():
            if data_type not in key_mapping:
                continue

            key = key_mapping[data_type]
            if not await self.client.hset(key, market, data):
                success = False

        return success

    async def get_active_markets(self) -> list[str]:
        """활성화된 마켓 목록을 조회합니다."""
        config_data = await self.client.hgetall(self.KEY_CONFIG)
        return list(config_data.keys())

    async def close(self) -> None:
        """연결을 종료합니다."""
        await self.client.close()
