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
from app.domain.models.trading import PriceHistory, PriceDataPoint
from app.domain.repositories.dca_repository import DcaRepository
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheDcaRepository(DcaRepository):
    """Cache 기반 DCA 데이터 저장소"""

    KEY_CONFIG = "dca:config"
    KEY_STATE = "dca:state"
    KEY_PRICE_HISTORY = "dca:price_history"

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

    async def save_price_data_point(
        self, market: str, price_data: PriceDataPoint
    ) -> bool:
        """가격 데이터 포인트를 저장합니다."""
        # 타임스탬프를 키로 사용 (ISO 형식)
        timestamp_key = price_data.timestamp.isoformat()
        price_key = f"{self.KEY_PRICE_HISTORY}:{market}"

        # 가격 데이터를 쉼표로 구분된 문자열로 저장
        value = price_data.to_cache_string()
        return await self.client.hset(price_key, timestamp_key, value)

    async def get_price_history(
        self, market: str, max_periods: int = 50
    ) -> PriceHistory | None:
        """가격 히스토리를 조회합니다."""
        price_key = f"{self.KEY_PRICE_HISTORY}:{market}"
        data = await self.client.hgetall(price_key)

        if not data:
            return None

        # 타임스탬프 키를 datetime으로 변환하고 정렬
        price_data_points = []
        for timestamp_str, price_str in data.items():
            timestamp = datetime.fromisoformat(timestamp_str)
            price_point = PriceDataPoint.from_cache_string(timestamp, price_str)
            price_data_points.append(price_point)

        # 최신 max_periods 개만 유지
        if len(price_data_points) > max_periods:
            price_data_points = sorted(price_data_points, key=lambda x: x.timestamp)[
                -max_periods:
            ]

        return PriceHistory.from_price_data_points(market, price_data_points)

    async def cleanup_old_price_data(self, market: str, max_periods: int = 50) -> bool:
        """오래된 가격 데이터를 정리합니다."""
        price_key = f"{self.KEY_PRICE_HISTORY}:{market}"
        data = await self.client.hgetall(price_key)

        if not data or len(data) <= max_periods:
            return True

        # 타임스탬프 순으로 정렬
        timestamps = sorted(data.keys(), key=lambda x: datetime.fromisoformat(x))

        # 오래된 데이터 삭제
        old_timestamps = timestamps[:-max_periods]
        if old_timestamps:
            return await self.client.hdel(price_key, *old_timestamps)

        return True

    async def clear_market_data(self, market: str) -> bool:
        """마켓의 모든 데이터를 삭제합니다."""
        success = True

        # 기본 키들 삭제
        keys = [self.KEY_CONFIG, self.KEY_STATE]
        for key in keys:
            if not await self.client.hdel(key, market):
                success = False

        # 가격 히스토리 키 삭제 (전체 hset 삭제)
        price_key = f"{self.KEY_PRICE_HISTORY}:{market}"
        if not await self.client.delete(price_key):
            success = False

        return success

    async def backup_state(self, market: str) -> dict[str, Any]:
        """상태를 백업합니다."""
        backup_data: dict[str, Any] = {}

        # 기본 키들 백업
        keys = {
            "config": self.KEY_CONFIG,
            "state": self.KEY_STATE,
        }

        for data_type, key in keys.items():
            data = await self.client.hget(key, market)
            if data:
                backup_data[data_type] = data

        # 가격 히스토리 백업
        price_key = f"{self.KEY_PRICE_HISTORY}:{market}"
        price_data = await self.client.hgetall(price_key)
        if price_data:
            backup_data["price_history"] = price_data

        return backup_data

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """상태를 복원합니다."""
        success = True

        # 기본 키들 복원
        key_mapping = {
            "config": self.KEY_CONFIG,
            "state": self.KEY_STATE,
        }

        for data_type, data in backup_data.items():
            if data_type in key_mapping:
                key = key_mapping[data_type]
                if not await self.client.hset(key, market, data):
                    success = False

        # 가격 히스토리 복원
        if "price_history" in backup_data:
            price_key = f"{self.KEY_PRICE_HISTORY}:{market}"
            price_data = backup_data["price_history"]

            # 가격 히스토리는 딕셔너리 형태로 저장되어 있음
            if isinstance(price_data, dict):
                for timestamp, price_str in price_data.items():
                    if not await self.client.hset(price_key, timestamp, price_str):
                        success = False

        return success

    async def get_active_markets(self) -> list[str]:
        """활성화된 마켓 목록을 조회합니다."""
        config_data = await self.client.hgetall(self.KEY_CONFIG)
        return list(config_data.keys())

    async def close(self) -> None:
        """연결을 종료합니다."""
        await self.client.close()
