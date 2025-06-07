"""
Cache를 사용한 무한매수법 데이터 저장 어댑터
"""

import logging
from datetime import datetime
from typing import Any

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
            except (
                GlideTimeoutError,
                RequestError,
                GlideConnectionError,
                ClosingError,
            ) as e:
                logger.error(f"Cache 연결 실패: {e}")
                raise
            else:
                logger.info(
                    f"Cache 서버에 연결되었습니다: {self._config.host}:{self._config.port}"
                )

        return self._client

    async def _cache_set(
        self, key: str, value: str, expire_seconds: int | None = None
    ) -> None:
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
            raise
        else:
            logger.debug(f"캐시 저장 완료: {key}")

    async def _cache_get(self, key: str) -> str | None:
        """캐시에서 값을 조회합니다."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                logger.debug(f"캐시 조회 완료: {key} (값 없음)")
                return None

            logger.debug(f"캐시 조회 완료: {key}")
            return value.decode("utf-8") if isinstance(value, bytes) else str(value)
        except (
            GlideTimeoutError,
            RequestError,
            GlideConnectionError,
            ClosingError,
        ) as e:
            logger.error(f"캐시 조회 실패 - key: {key}, error: {e}")
            raise

    async def _cache_delete(self, key: str) -> None:
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
            raise
        else:
            logger.debug(f"캐시 삭제 완료: {key}")

    async def _cache_scan(self, pattern: str) -> list[str]:
        """패턴에 맞는 키 목록을 조회합니다."""
        # glide scan API는 정확하지 않으므로 임시로 빈 리스트 반환
        # 실제 구현에서는 적절한 스캔 방법을 사용해야 함
        keys: list[str] = []
        logger.debug(f"캐시 키 조회 완료: {pattern}, 개수: {len(keys)}")
        return keys

    async def save_config(self, market: str, config: InfiniteBuyingConfig) -> bool:
        """무한매수법 설정을 저장합니다."""
        try:
            key = f"infinite_buying:config:{market}"
            value = config.to_cache_json()
            await self._cache_set(key, value)
        except Exception as e:
            logger.error(f"무한매수법 설정 저장 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"무한매수법 설정 저장 완료: {market}")
            return True

    async def get_config(self, market: str) -> InfiniteBuyingConfig | None:
        """무한매수법 설정을 조회합니다."""
        try:
            key = f"infinite_buying:config:{market}"
            data = await self._cache_get(key)
            if data:
                config = InfiniteBuyingConfig.from_cache_json(data)
                logger.info(f"무한매수법 설정 조회 완료: {market}")
                return config
            else:
                return None
        except Exception as e:
            logger.error(f"무한매수법 설정 조회 실패: {market}, error: {e}")
            return None

    async def save_state(self, market: str, state: InfiniteBuyingState) -> bool:
        """무한매수법 상태를 저장합니다."""
        try:
            key = f"infinite_buying:state:{market}"
            value = state.to_cache_json()
            await self._cache_set(key, value)
        except Exception as e:
            logger.error(f"무한매수법 상태 저장 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"무한매수법 상태 저장 완료: {market}")
            return True

    async def get_state(self, market: str) -> InfiniteBuyingState | None:
        """무한매수법 상태를 조회합니다."""
        try:
            key = f"infinite_buying:state:{market}"
            data = await self._cache_get(key)
            if data:
                state = InfiniteBuyingState.from_cache_json(data)
                logger.info(f"무한매수법 상태 조회 완료: {market}")
                return state
            else:
                return None
        except Exception as e:
            logger.error(f"무한매수법 상태 조회 실패: {market}, error: {e}")
            return None

    async def get_state_with_rounds(self, market: str) -> InfiniteBuyingState | None:
        """매수 회차 정보를 포함한 상태를 조회합니다."""
        state = await self.get_state(market)
        if state:
            rounds = await self.get_buying_rounds(market, state.cycle_id)
            state.buying_rounds = rounds
        return state

    async def add_buying_round(self, market: str, buying_round: BuyingRound) -> bool:
        """매수 회차를 추가합니다."""
        try:
            key = f"infinite_buying:round:{market}:{buying_round.round_number}"
            value = buying_round.to_cache_json()
            await self._cache_set(key, value, expire_seconds=86400 * 30)  # 30일 보관
        except Exception as e:
            logger.error(f"매수 회차 저장 실패: {market}, error: {e}")
            return False
        else:
            logger.info(
                f"매수 회차 저장 완료: {market}, round: {buying_round.round_number}"
            )
            return True

    async def get_buying_rounds(
        self, market: str, cycle_id: str | None = None
    ) -> list[BuyingRound]:
        """매수 회차 목록을 조회합니다."""
        try:
            pattern = f"infinite_buying:round:{market}:*"
            keys = await self._cache_scan(pattern)
            rounds = []

            for key in keys:
                data = await self._cache_get(key)
                if data:
                    round_info = BuyingRound.from_cache_json(data)
                    rounds.append(round_info)

            # round_number 기준으로 정렬
            rounds.sort(key=lambda x: x.round_number)
        except Exception as e:
            logger.error(f"매수 회차 조회 실패: {market}, error: {e}")
            return []
        else:
            logger.info(f"매수 회차 조회 완료: {market}, 개수: {len(rounds)}")
            return rounds

    async def save_cycle_history(
        self,
        market: str,
        cycle_id: str,
        state: InfiniteBuyingState,
        result: InfiniteBuyingResult,
    ) -> bool:
        """완료된 사이클 히스토리를 저장합니다."""
        try:
            timestamp = datetime.now()
            key = f"infinite_buying:cycle:{market}:{cycle_id}:{timestamp.strftime('%Y%m%d_%H%M%S')}"

            # CycleHistoryItem 생성
            status = CycleStatus.COMPLETED if result.success else CycleStatus.FAILED
            cycle_item = CycleHistoryItem.from_state_and_result(
                state, result, timestamp, status
            )

            value = cycle_item.to_cache_json()
            await self._cache_set(key, value, expire_seconds=86400 * 30)  # 30일 보관
        except Exception as e:
            logger.error(f"사이클 히스토리 저장 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"사이클 히스토리 저장 완료: {market}, cycle: {cycle_id}")
            return True

    async def get_cycle_history(
        self, market: str, limit: int = 100
    ) -> list[CycleHistoryItem]:
        """완료된 사이클 히스토리를 조회합니다."""
        try:
            pattern = f"infinite_buying:cycle:{market}:*"
            keys = await self._cache_scan(pattern)

            # 시간순 정렬 (최신순)
            keys.sort(reverse=True)

            history = []
            for key in keys[:limit]:
                data = await self._cache_get(key)
                if data:
                    cycle_item = CycleHistoryItem.from_cache_json(data)
                    history.append(cycle_item)
        except Exception as e:
            logger.error(f"사이클 히스토리 조회 실패: {market}, error: {e}")
            return []
        else:
            logger.info(f"사이클 히스토리 조회 완료: {market}, 개수: {len(history)}")
            return history

    async def get_trade_statistics(self, market: str) -> TradeStatistics:
        """거래 통계를 조회합니다."""
        try:
            key = f"infinite_buying:stats:{market}"
            data = await self._cache_get(key)
            if data:
                stats = TradeStatistics.from_cache_json(data)
                logger.info(f"거래 통계 조회 완료: {market}")
                return stats
        except Exception as e:
            logger.error(f"거래 통계 조회 실패: {market}, error: {e}")

        # 기본 통계 반환
        return TradeStatistics.create_empty()

    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """거래 통계를 업데이트합니다."""
        try:
            key = f"infinite_buying:stats:{market}"
            current_stats = await self.get_trade_statistics(market)

            # 통계 업데이트 (불변 객체이므로 새 객체 생성)
            updated_stats = current_stats.update_with_result(result)

            value = updated_stats.to_cache_json()
            await self._cache_set(key, value)
        except Exception as e:
            logger.error(f"거래 통계 업데이트 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"거래 통계 업데이트 완료: {market}")
            return True

    async def clear_market_data(self, market: str) -> bool:
        """특정 마켓의 모든 데이터를 삭제합니다."""
        try:
            patterns = [
                f"infinite_buying:state:{market}",
                f"infinite_buying:config:{market}",
                f"infinite_buying:round:{market}:*",
                f"infinite_buying:cycle:{market}:*",
                f"infinite_buying:stats:{market}",
            ]

            for pattern in patterns:
                if "*" in pattern:
                    # 패턴으로 검색하여 삭제
                    keys = await self._cache_scan(pattern)
                    for key in keys:
                        await self._cache_delete(key)
                else:
                    # 단일 키 삭제
                    await self._cache_delete(pattern)
        except Exception as e:
            logger.error(f"마켓 데이터 삭제 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"마켓 데이터 삭제 완료: {market}")
            return True

    async def backup_state(self, market: str) -> dict[str, Any]:
        """현재 상태를 백업용 딕셔너리로 반환합니다."""
        backup_data: dict[str, Any] = {}
        try:
            # 설정 백업
            config = await self.get_config(market)
            if config:
                backup_data["config"] = config.model_dump()

            # 상태 백업 (회차 정보 포함)
            state = await self.get_state_with_rounds(market)
            if state:
                backup_data["state"] = state.model_dump()

            # 통계 백업
            stats = await self.get_trade_statistics(market)
            if stats:
                backup_data["statistics"] = stats.model_dump()

            # 히스토리 백업
            history = await self.get_cycle_history(
                market, limit=MAX_CYCLE_HISTORY_COUNT
            )
            if history:
                backup_data["history"] = [item.model_dump() for item in history]

            logger.info(f"상태 백업 완료: {market}")
        except Exception as e:
            logger.error(f"상태 백업 실패: {market}, error: {e}")

        return backup_data

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """백업 데이터로부터 상태를 복원합니다."""
        try:
            # 기존 데이터 삭제
            await self.clear_market_data(market)

            # 설정 복원
            if "config" in backup_data:
                config = InfiniteBuyingConfig.model_validate(backup_data["config"])
                await self.save_config(market, config)

            # 상태 복원
            if "state" in backup_data:
                state = InfiniteBuyingState.model_validate(backup_data["state"])
                await self.save_state(market, state)

                # 매수 회차 개별 저장
                for buying_round in state.buying_rounds:
                    await self.add_buying_round(market, buying_round)

            # 통계 복원
            if "statistics" in backup_data:
                stats = TradeStatistics.model_validate(backup_data["statistics"])
                key = f"infinite_buying:stats:{market}"
                await self._cache_set(key, stats.to_cache_json())

            # 히스토리 복원
            if "history" in backup_data:
                for item_data in backup_data["history"]:
                    item = CycleHistoryItem.model_validate(item_data)
                    timestamp_str = item.end_time.strftime("%Y%m%d_%H%M%S")
                    key = f"infinite_buying:cycle:{market}:{item.cycle_id}:{timestamp_str}"
                    await self._cache_set(
                        key, item.to_cache_json(), expire_seconds=86400 * 30
                    )

            logger.info(f"상태 복원 완료: {market}")
        except Exception as e:
            logger.error(f"상태 복원 실패: {market}, error: {e}")
            return False
        else:
            return True

    async def get_active_markets(self) -> list[str]:
        """현재 활성화된 무한매수법 마켓 목록을 반환합니다."""
        try:
            pattern = "infinite_buying:state:*"
            keys = await self._cache_scan(pattern)

            active_markets = []
            for key in keys:
                # key 형식: "infinite_buying:state:{market}"
                market = key.split(":")[-1]
                state = await self.get_state(market)
                if state and state.is_active:
                    active_markets.append(market)
        except Exception as e:
            logger.error(f"활성 마켓 조회 실패: {e}")
            return []
        else:
            logger.info(f"활성 마켓 조회 완료: {active_markets}")
            return active_markets

    async def close(self) -> None:
        """Cache 연결을 종료합니다."""
        if self._client:
            try:
                await self._client.close()
                logger.info("Cache 연결이 종료되었습니다.")
            except Exception as e:
                logger.error(f"Cache 연결 종료 실패: {e}")
            finally:
                self._client = None
