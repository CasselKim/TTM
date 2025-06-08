"""
Cache를 사용한 무한매수법 데이터 저장 어댑터
"""

import logging
from datetime import datetime
from typing import Any

from app.adapters.external.cache.client import CacheClient
from app.adapters.external.cache.config import CacheConfig
from app.domain.models.infinite_buying import (
    BuyingRound,
    InfiniteBuyingConfig,
    InfiniteBuyingResult,
    InfiniteBuyingState,
)
from app.domain.repositories.infinite_buying_repository import InfiniteBuyingRepository
from app.domain.types import (
    CycleHistoryItem,
    CycleStatus,
    TradeStatistics,
)

logger = logging.getLogger(__name__)

MAX_CYCLE_HISTORY_COUNT = 1000


class CacheInfiniteBuyingRepository(InfiniteBuyingRepository):
    """Cache 기반 무한매수법 데이터 저장소"""

    KEY_CONFIG = "infinite_buying:config"
    KEY_STATE = "infinite_buying:state"
    KEY_HISTORY = "infinite_buying:history"
    KEY_STATS = "infinite_buying:stats"
    KEY_ROUNDS = "infinite_buying:rounds"

    def __init__(self, config: CacheConfig):
        self.client = CacheClient(config)

    async def save_config(self, market: str, config: InfiniteBuyingConfig) -> bool:
        """무한매수법 설정을 저장합니다."""
        value = config.to_cache_json()
        return await self.client.hset(self.KEY_CONFIG, market, value)

    async def get_config(self, market: str) -> InfiniteBuyingConfig | None:
        """무한매수법 설정을 조회합니다."""
        data = await self.client.hget(self.KEY_CONFIG, market)
        if not data:
            return None
        return InfiniteBuyingConfig.from_cache_json(data)

    async def save_state(self, market: str, state: InfiniteBuyingState) -> bool:
        """무한매수법 상태를 저장합니다."""
        value = state.to_cache_json()
        return await self.client.hset(self.KEY_STATE, market, value)

    async def get_state(self, market: str) -> InfiniteBuyingState | None:
        """무한매수법 상태를 조회합니다."""
        data = await self.client.hget(self.KEY_STATE, market)
        if not data:
            return None
        return InfiniteBuyingState.from_cache_json(data)

    async def get_state_with_rounds(self, market: str) -> InfiniteBuyingState | None:
        """매수 회차 정보를 포함한 상태를 조회합니다."""
        state = await self.get_state(market)

        if not state or not state.cycle_id:
            return state

        # KEY_STATE에서 이미 buying_rounds가 포함되어 있으므로 추가 조회 불필요
        # 기존의 중복 저장 방식으로 인한 데이터 불일치 문제를 방지
        return state

    async def add_buying_round(self, market: str, buying_round: BuyingRound) -> bool:
        """매수 라운드를 추가합니다."""
        existing_data = await self.client.hget(self.KEY_ROUNDS, market)

        if existing_data:
            rounds = [
                BuyingRound.from_cache_json(r) for r in existing_data.split("|") if r
            ]
        else:
            rounds = []

        rounds.append(buying_round)
        value = "|".join([r.to_cache_json() for r in rounds])
        return await self.client.hset(self.KEY_ROUNDS, market, value)

    async def get_buying_rounds(
        self, market: str, cycle_id: str | None = None
    ) -> list[BuyingRound]:
        """매수 라운드 목록을 조회합니다."""
        data = await self.client.hget(self.KEY_ROUNDS, market)

        if not data:
            return []

        split_data = data.split("|")
        all_rounds = [BuyingRound.from_cache_json(r) for r in split_data if r]

        if not cycle_id:
            return all_rounds

        filtered_rounds = [
            r for r in all_rounds if getattr(r, "cycle_id", None) == cycle_id
        ]
        return filtered_rounds

    async def save_cycle_history(
        self,
        market: str,
        cycle_id: str,
        state: InfiniteBuyingState,
        result: InfiniteBuyingResult,
    ) -> bool:
        """사이클 히스토리를 저장합니다."""
        end_time = datetime.now()
        history_item = CycleHistoryItem(
            cycle_id=cycle_id,
            market=market,
            start_time=state.cycle_start_time or end_time,
            end_time=end_time,
            status=CycleStatus.COMPLETED,
            total_investment=state.total_investment,
            total_volume=state.total_volume,
            average_price=state.average_price,
            sell_price=result.trade_price,
            profit_rate=result.profit_rate,
            max_rounds=10,
            actual_rounds=state.current_round,
        )

        existing_data = await self.client.hget(self.KEY_HISTORY, market)

        if existing_data:
            histories = [
                CycleHistoryItem.from_cache_json(h)
                for h in existing_data.split("|")
                if h
            ]
        else:
            histories = []

        histories.append(history_item)

        if len(histories) > MAX_CYCLE_HISTORY_COUNT:
            histories = histories[-MAX_CYCLE_HISTORY_COUNT:]

        value = "|".join([h.to_cache_json() for h in histories])
        return await self.client.hset(self.KEY_HISTORY, market, value)

    async def get_cycle_history(
        self, market: str, limit: int = 100
    ) -> list[CycleHistoryItem]:
        """사이클 히스토리를 조회합니다."""
        data = await self.client.hget(self.KEY_HISTORY, market)
        if not data:
            return []

        histories = [CycleHistoryItem.from_cache_json(h) for h in data.split("|") if h]
        if not limit:
            return histories
        return histories[-limit:]

    async def get_trade_statistics(self, market: str) -> TradeStatistics:
        """거래 통계를 조회합니다."""
        data = await self.client.hget(self.KEY_STATS, market)
        if not data:
            return TradeStatistics.create_empty()
        return TradeStatistics.from_cache_json(data)

    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """통계를 업데이트합니다."""
        current_stats = await self.get_trade_statistics(market)
        updated_stats = current_stats.update_with_result(result)

        value = updated_stats.to_cache_json()
        return await self.client.hset(self.KEY_STATS, market, value)

    async def clear_market_data(self, market: str) -> bool:
        """마켓의 모든 데이터를 삭제합니다."""
        success = True

        keys = [
            self.KEY_CONFIG,
            self.KEY_STATE,
            self.KEY_HISTORY,
            self.KEY_STATS,
            self.KEY_ROUNDS,
        ]
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
            "history": self.KEY_HISTORY,
            "stats": self.KEY_STATS,
            "rounds": self.KEY_ROUNDS,
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
            "history": self.KEY_HISTORY,
            "stats": self.KEY_STATS,
            "rounds": self.KEY_ROUNDS,
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
