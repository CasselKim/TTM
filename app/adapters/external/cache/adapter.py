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

# 상수 정의
MAX_CYCLE_HISTORY_COUNT = 1000  # 최대 사이클 히스토리 보관 개수


class CacheInfiniteBuyingRepository(InfiniteBuyingRepository):
    """Cache 기반 무한매수법 데이터 저장소"""

    def __init__(self, config: CacheConfig):
        self._client = CacheClient(config)

    async def save_config(self, market: str, config: InfiniteBuyingConfig) -> bool:
        """무한매수법 설정을 저장합니다."""
        key = f"infinite_buying:config:{market}"
        value = config.to_cache_json()
        success = await self._client.set(key, value)
        if success:
            logger.info(f"무한매수법 설정 저장 완료: {market}")
        return success

    async def get_config(self, market: str) -> InfiniteBuyingConfig | None:
        """무한매수법 설정을 조회합니다."""
        key = f"infinite_buying:config:{market}"
        data = await self._client.get(key)
        if data:
            config = InfiniteBuyingConfig.from_cache_json(data)
            logger.info(f"무한매수법 설정 조회 완료: {market}")
            return config
        return None

    async def save_state(self, market: str, state: InfiniteBuyingState) -> bool:
        """무한매수법 상태를 저장합니다."""
        key = f"infinite_buying:state:{market}"
        value = state.to_cache_json()
        success = await self._client.set(key, value)
        if success:
            logger.info(f"무한매수법 상태 저장 완료: {market}")
        return success

    async def get_state(self, market: str) -> InfiniteBuyingState | None:
        """무한매수법 상태를 조회합니다."""
        key = f"infinite_buying:state:{market}"
        data = await self._client.get(key)
        if data:
            state = InfiniteBuyingState.from_cache_json(data)
            logger.info(f"무한매수법 상태 조회 완료: {market}")
            return state
        return None

    async def get_state_with_rounds(self, market: str) -> InfiniteBuyingState | None:
        """매수 회차 정보를 포함한 상태를 조회합니다."""
        state = await self.get_state(market)
        if state and state.cycle_id:
            # 현재 사이클의 매수 회차들을 조회해서 state에 포함
            rounds = await self.get_buying_rounds(market, state.cycle_id)
            state.buying_rounds = rounds
        return state

    async def add_buying_round(self, market: str, buying_round: BuyingRound) -> bool:
        """매수 라운드를 추가합니다."""
        # BuyingRound는 cycle_id가 없으므로 market과 round_number를 조합하여 키 생성
        key = f"infinite_buying:rounds:{market}:{buying_round.round_number}"
        existing_data = await self._client.get(key)

        if existing_data:
            rounds = [
                BuyingRound.from_cache_json(r) for r in existing_data.split("|") if r
            ]
        else:
            rounds = []

        rounds.append(buying_round)
        value = "|".join([r.to_cache_json() for r in rounds])
        success = await self._client.set(key, value)
        if success:
            logger.info(f"매수 라운드 추가 완료: {market}")
        return success

    async def get_buying_rounds(
        self, market: str, cycle_id: str | None = None
    ) -> list[BuyingRound]:
        """매수 라운드 목록을 조회합니다."""
        if cycle_id:
            key = f"infinite_buying:rounds:{market}:{cycle_id}"
            data = await self._client.get(key)
            if data:
                return [BuyingRound.from_cache_json(r) for r in data.split("|") if r]
        else:
            # 모든 사이클의 라운드 조회
            keys = await self._client.scan(f"infinite_buying:rounds:{market}:*")
            rounds = []
            for key in keys:
                data = await self._client.get(key)
                if data:
                    rounds.extend(
                        [BuyingRound.from_cache_json(r) for r in data.split("|") if r]
                    )
            return rounds
        return []

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
            max_rounds=10,  # 설정에서 가져와야 하지만 임시로 하드코딩
            actual_rounds=state.current_round,
        )

        key = f"infinite_buying:history:{market}"
        existing_data = await self._client.get(key)

        if existing_data:
            histories = [
                CycleHistoryItem.from_cache_json(h)
                for h in existing_data.split("|")
                if h
            ]
        else:
            histories = []

        histories.append(history_item)

        # 최대 개수 제한
        if len(histories) > MAX_CYCLE_HISTORY_COUNT:
            histories = histories[-MAX_CYCLE_HISTORY_COUNT:]

        value = "|".join([h.to_cache_json() for h in histories])
        success = await self._client.set(key, value)
        if success:
            logger.info(f"사이클 히스토리 저장 완료: {market}")
        return success

    async def get_cycle_history(
        self, market: str, limit: int = 100
    ) -> list[CycleHistoryItem]:
        """사이클 히스토리를 조회합니다."""
        key = f"infinite_buying:history:{market}"
        data = await self._client.get(key)
        if data:
            histories = [
                CycleHistoryItem.from_cache_json(h) for h in data.split("|") if h
            ]
            return histories[-limit:] if limit else histories
        return []

    async def get_trade_statistics(self, market: str) -> TradeStatistics:
        """거래 통계를 조회합니다."""
        key = f"infinite_buying:stats:{market}"
        data = await self._client.get(key)
        if data:
            return TradeStatistics.from_cache_json(data)
        return TradeStatistics.create_empty()

    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """통계를 업데이트합니다."""
        current_stats = await self.get_trade_statistics(market)

        # TradeStatistics의 update_with_result 메서드 사용
        updated_stats = current_stats.update_with_result(result)

        key = f"infinite_buying:stats:{market}"
        value = updated_stats.to_cache_json()
        success = await self._client.set(key, value)
        if success:
            logger.info(f"통계 업데이트 완료: {market}")
        return success

    async def clear_market_data(self, market: str) -> bool:
        """마켓의 모든 데이터를 삭제합니다."""
        keys_to_delete = [
            f"infinite_buying:config:{market}",
            f"infinite_buying:state:{market}",
            f"infinite_buying:history:{market}",
            f"infinite_buying:stats:{market}",
        ]

        # 모든 라운드 키들도 찾아서 삭제
        round_keys = await self._client.scan(f"infinite_buying:rounds:{market}:*")
        keys_to_delete.extend(round_keys)

        success = True
        for key in keys_to_delete:
            if not await self._client.delete(key):
                success = False

        if success:
            logger.info(f"마켓 데이터 삭제 완료: {market}")
        return success

    async def backup_state(self, market: str) -> dict[str, Any]:
        """상태를 백업합니다."""
        backup_data: dict[str, Any] = {}

        # 설정 백업
        config_key = f"infinite_buying:config:{market}"
        config_data = await self._client.get(config_key)
        if config_data:
            backup_data["config"] = config_data

        # 상태 백업
        state_key = f"infinite_buying:state:{market}"
        state_data = await self._client.get(state_key)
        if state_data:
            backup_data["state"] = state_data

        # 히스토리 백업
        history_key = f"infinite_buying:history:{market}"
        history_data = await self._client.get(history_key)
        if history_data:
            backup_data["history"] = history_data

        # 통계 백업
        stats_key = f"infinite_buying:stats:{market}"
        stats_data = await self._client.get(stats_key)
        if stats_data:
            backup_data["stats"] = stats_data

        # 라운드 백업
        round_keys = await self._client.scan(f"infinite_buying:rounds:{market}:*")
        rounds_data = {}
        for key in round_keys:
            data = await self._client.get(key)
            if data:
                rounds_data[key] = data
        if rounds_data:
            backup_data["rounds"] = rounds_data

        logger.info(f"상태 백업 완료: {market}")
        return backup_data

    async def _restore_config(self, market: str, config_data: str) -> bool:
        """설정을 복원합니다."""
        config_key = f"infinite_buying:config:{market}"
        return await self._client.set(config_key, config_data)

    async def _restore_state_data(self, market: str, state_data: str) -> bool:
        """상태 데이터를 복원합니다."""
        state_key = f"infinite_buying:state:{market}"
        return await self._client.set(state_key, state_data)

    async def _restore_history(self, market: str, history_data: str) -> bool:
        """히스토리를 복원합니다."""
        history_key = f"infinite_buying:history:{market}"
        return await self._client.set(history_key, history_data)

    async def _restore_stats(self, market: str, stats_data: str) -> bool:
        """통계를 복원합니다."""
        stats_key = f"infinite_buying:stats:{market}"
        return await self._client.set(stats_key, stats_data)

    async def _restore_rounds(self, rounds_data: dict[str, str]) -> bool:
        """라운드 데이터를 복원합니다."""
        for key, data in rounds_data.items():
            if not await self._client.set(key, data):
                return False
        return True

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """상태를 복원합니다."""
        success = True

        # 각 데이터 타입별로 복원
        if "config" in backup_data:
            success &= await self._restore_config(market, backup_data["config"])

        if "state" in backup_data:
            success &= await self._restore_state_data(market, backup_data["state"])

        if "history" in backup_data:
            success &= await self._restore_history(market, backup_data["history"])

        if "stats" in backup_data:
            success &= await self._restore_stats(market, backup_data["stats"])

        if "rounds" in backup_data:
            success &= await self._restore_rounds(backup_data["rounds"])

        if success:
            logger.info(f"상태 복원 완료: {market}")
        return success

    async def get_active_markets(self) -> list[str]:
        """활성화된 마켓 목록을 조회합니다."""
        config_keys = await self._client.scan("infinite_buying:config:*")
        markets = []
        for key in config_keys:
            if key.startswith("infinite_buying:config:"):
                market = key.replace("infinite_buying:config:", "")
                markets.append(market)
        return markets

    async def close(self) -> None:
        """연결을 종료합니다."""
        await self._client.close()
