"""
Cache를 사용한 무한매수법 데이터 저장 어댑터
"""

import dataclasses
import json
import logging
from datetime import datetime
from decimal import Decimal
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
    TradeStatistics,
)

logger = logging.getLogger(__name__)

# 상수 정의
MAX_CYCLE_HISTORY_COUNT = 1000  # 최대 사이클 히스토리 보관 개수


class DecimalEncoder(json.JSONEncoder):
    """Decimal을 JSON으로 인코딩하기 위한 커스텀 엔코더"""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


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
            value = json.dumps(dataclasses.asdict(config), cls=DecimalEncoder)
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
                config_dict = json.loads(data)
                config = InfiniteBuyingConfig(
                    initial_buy_amount=Decimal(str(config_dict["initial_buy_amount"])),
                    add_buy_multiplier=Decimal(str(config_dict["add_buy_multiplier"])),
                    target_profit_rate=Decimal(str(config_dict["target_profit_rate"])),
                    price_drop_threshold=Decimal(
                        str(config_dict["price_drop_threshold"])
                    ),
                    force_stop_loss_rate=Decimal(
                        str(config_dict["force_stop_loss_rate"])
                    ),
                    max_buy_rounds=config_dict["max_buy_rounds"],
                    max_investment_ratio=Decimal(
                        str(config_dict["max_investment_ratio"])
                    ),
                    min_buy_interval_minutes=config_dict["min_buy_interval_minutes"],
                    max_cycle_days=config_dict["max_cycle_days"],
                )
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
            value = json.dumps(dataclasses.asdict(state), cls=DecimalEncoder)
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
                state_dict = json.loads(data)

                # buying_rounds 리스트 변환
                buying_rounds = []
                if state_dict.get("buying_rounds"):
                    for round_data in state_dict["buying_rounds"]:
                        # datetime 변환
                        timestamp_str = round_data["timestamp"]
                        timestamp = (
                            datetime.fromisoformat(timestamp_str)
                            if isinstance(timestamp_str, str)
                            else datetime.now()
                        )

                        buying_round = BuyingRound(
                            round_number=round_data["round_number"],
                            buy_price=Decimal(str(round_data["buy_price"])),
                            buy_amount=Decimal(str(round_data["buy_amount"])),
                            buy_volume=Decimal(str(round_data["buy_volume"])),
                            timestamp=timestamp,
                        )
                        buying_rounds.append(buying_round)

                # datetime 필드 변환 (nullable 필드만 별도 처리)
                last_buy_time = None
                if state_dict.get("last_buy_time"):
                    last_buy_time_str = state_dict["last_buy_time"]
                    if isinstance(last_buy_time_str, str):
                        last_buy_time = datetime.fromisoformat(last_buy_time_str)

                cycle_start_time = None
                if state_dict.get("cycle_start_time"):
                    cycle_start_time_str = state_dict["cycle_start_time"]
                    if isinstance(cycle_start_time_str, str):
                        cycle_start_time = datetime.fromisoformat(cycle_start_time_str)

                state = InfiniteBuyingState(
                    market=state_dict["market"],
                    phase=state_dict["phase"],
                    cycle_id=state_dict["cycle_id"],
                    current_round=state_dict["current_round"],
                    total_investment=Decimal(str(state_dict["total_investment"])),
                    total_volume=Decimal(str(state_dict["total_volume"])),
                    average_price=Decimal(str(state_dict["average_price"])),
                    last_buy_price=Decimal(str(state_dict["last_buy_price"])),
                    last_buy_time=last_buy_time,
                    cycle_start_time=cycle_start_time,
                    target_sell_price=Decimal(str(state_dict["target_sell_price"])),
                    buying_rounds=buying_rounds,
                )
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
            value = json.dumps(dataclasses.asdict(buying_round), cls=DecimalEncoder)
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
                    round_dict = json.loads(data)

                    # datetime 변환
                    timestamp_str = round_dict["timestamp"]
                    timestamp = (
                        datetime.fromisoformat(timestamp_str)
                        if isinstance(timestamp_str, str)
                        else datetime.now()
                    )

                    round_info = BuyingRound(
                        round_number=round_dict["round_number"],
                        buy_price=Decimal(str(round_dict["buy_price"])),
                        buy_amount=Decimal(str(round_dict["buy_amount"])),
                        buy_volume=Decimal(str(round_dict["buy_volume"])),
                        timestamp=timestamp,
                    )
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"infinite_buying:cycle:{market}:{cycle_id}:{timestamp}"

            cycle_item = {
                "cycle_id": cycle_id,
                "market": market,
                "state": dataclasses.asdict(state) if state else {},
                "result": dataclasses.asdict(result) if result else {},
                "timestamp": timestamp,
            }

            value = json.dumps(cycle_item, cls=DecimalEncoder)
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
                    cycle_item = json.loads(data)
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
                stats_dict = json.loads(data)

                # datetime 변환
                last_updated_str = stats_dict["last_updated"]
                last_updated = (
                    datetime.fromisoformat(last_updated_str)
                    if isinstance(last_updated_str, str)
                    else datetime.now()
                )

                # dict를 TradeStatistics로 변환
                stats = TradeStatistics(
                    total_cycles=stats_dict["total_cycles"],
                    success_cycles=stats_dict["success_cycles"],
                    total_profit=Decimal(str(stats_dict["total_profit"])),
                    total_profit_rate=Decimal(str(stats_dict["total_profit_rate"])),
                    average_profit_rate=Decimal(str(stats_dict["average_profit_rate"])),
                    best_profit_rate=Decimal(str(stats_dict["best_profit_rate"])),
                    worst_profit_rate=Decimal(str(stats_dict["worst_profit_rate"])),
                    last_updated=last_updated,
                )
                logger.info(f"거래 통계 조회 완료: {market}")
                return stats
        except Exception as e:
            logger.error(f"거래 통계 조회 실패: {market}, error: {e}")

        # 기본 통계 반환
        return TradeStatistics(
            total_cycles=0,
            success_cycles=0,
            total_profit=Decimal("0"),
            total_profit_rate=Decimal("0"),
            average_profit_rate=Decimal("0"),
            best_profit_rate=Decimal("0"),
            worst_profit_rate=Decimal("0"),
            last_updated=datetime.now(),
        )

    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """거래 통계를 업데이트합니다."""
        try:
            key = f"infinite_buying:stats:{market}"
            current_stats = await self.get_trade_statistics(market)

            # 새로운 TradeStatistics 객체 생성
            updated_stats = TradeStatistics(
                total_cycles=current_stats.total_cycles + 1,
                success_cycles=current_stats.success_cycles,
                total_profit=current_stats.total_profit,
                total_profit_rate=current_stats.total_profit_rate,
                average_profit_rate=current_stats.average_profit_rate,
                best_profit_rate=current_stats.best_profit_rate,
                worst_profit_rate=current_stats.worst_profit_rate,
                last_updated=datetime.now(),
            )

            # 성공한 경우 수익 통계 업데이트
            if result.success and result.profit_rate and result.profit_rate > 0:
                updated_stats.success_cycles += 1
                updated_stats.total_profit += result.profit_rate
                updated_stats.total_profit_rate += result.profit_rate

                # 최고/최악 수익률 업데이트
                updated_stats.best_profit_rate = max(
                    updated_stats.best_profit_rate, result.profit_rate
                )
                if (
                    result.profit_rate < updated_stats.worst_profit_rate
                    or updated_stats.worst_profit_rate == 0
                ):
                    updated_stats.worst_profit_rate = result.profit_rate

            # 평균 수익률 재계산
            if updated_stats.total_cycles > 0:
                updated_stats.average_profit_rate = (
                    updated_stats.total_profit_rate
                    / Decimal(updated_stats.total_cycles)
                )

            value = json.dumps(dataclasses.asdict(updated_stats), cls=DecimalEncoder)
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
                    keys = await self._cache_scan(pattern)
                    for key in keys:
                        await self._cache_delete(key)
                else:
                    await self._cache_delete(pattern)
        except Exception as e:
            logger.error(f"마켓 데이터 삭제 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"마켓 데이터 삭제 완료: {market}")
            return True

    async def backup_state(self, market: str) -> dict[str, Any]:
        """현재 상태를 백업용 딕셔너리로 반환합니다."""
        try:
            state = await self.get_state_with_rounds(market)
            config = await self.get_config(market)
            stats = await self.get_trade_statistics(market)

            backup = {
                "market": market,
                "state": dataclasses.asdict(state) if state else None,
                "config": dataclasses.asdict(config) if config else None,
                "statistics": dataclasses.asdict(stats) if stats else None,
                "backup_time": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"상태 백업 실패: {market}, error: {e}")
            return {}
        else:
            logger.info(f"상태 백업 완료: {market}")
            return backup

    def _restore_buying_rounds(self, state_dict: dict[str, Any]) -> list[BuyingRound]:
        """매수 회차 리스트를 복원합니다."""
        buying_rounds = []
        if state_dict.get("buying_rounds"):
            for round_data in state_dict["buying_rounds"]:
                # datetime 변환
                timestamp_str = round_data["timestamp"]
                timestamp = (
                    datetime.fromisoformat(timestamp_str)
                    if isinstance(timestamp_str, str)
                    else datetime.now()
                )

                buying_round = BuyingRound(
                    round_number=round_data["round_number"],
                    buy_price=Decimal(str(round_data["buy_price"])),
                    buy_amount=Decimal(str(round_data["buy_amount"])),
                    buy_volume=Decimal(str(round_data["buy_volume"])),
                    timestamp=timestamp,
                )
                buying_rounds.append(buying_round)
        return buying_rounds

    def _restore_datetime_field(
        self, state_dict: dict[str, Any], field_name: str
    ) -> datetime | None:
        """datetime 필드를 복원합니다."""
        if state_dict.get(field_name):
            datetime_str = state_dict[field_name]
            if isinstance(datetime_str, str):
                return datetime.fromisoformat(datetime_str)
        return None

    async def _restore_state_data(
        self, market: str, state_dict: dict[str, Any]
    ) -> None:
        """상태 데이터를 복원합니다."""
        buying_rounds = self._restore_buying_rounds(state_dict)
        last_buy_time = self._restore_datetime_field(state_dict, "last_buy_time")
        cycle_start_time = self._restore_datetime_field(state_dict, "cycle_start_time")

        state = InfiniteBuyingState(
            market=state_dict["market"],
            phase=state_dict["phase"],
            cycle_id=state_dict["cycle_id"],
            current_round=state_dict["current_round"],
            total_investment=Decimal(str(state_dict["total_investment"])),
            total_volume=Decimal(str(state_dict["total_volume"])),
            average_price=Decimal(str(state_dict["average_price"])),
            last_buy_price=Decimal(str(state_dict["last_buy_price"])),
            last_buy_time=last_buy_time,
            cycle_start_time=cycle_start_time,
            target_sell_price=Decimal(str(state_dict["target_sell_price"])),
            buying_rounds=buying_rounds,
        )
        await self.save_state(market, state)

    async def _restore_config_data(
        self, market: str, config_dict: dict[str, Any]
    ) -> None:
        """설정 데이터를 복원합니다."""
        config = InfiniteBuyingConfig(
            initial_buy_amount=Decimal(str(config_dict["initial_buy_amount"])),
            add_buy_multiplier=Decimal(str(config_dict["add_buy_multiplier"])),
            target_profit_rate=Decimal(str(config_dict["target_profit_rate"])),
            price_drop_threshold=Decimal(str(config_dict["price_drop_threshold"])),
            force_stop_loss_rate=Decimal(str(config_dict["force_stop_loss_rate"])),
            max_buy_rounds=config_dict["max_buy_rounds"],
            max_investment_ratio=Decimal(str(config_dict["max_investment_ratio"])),
            min_buy_interval_minutes=config_dict["min_buy_interval_minutes"],
            max_cycle_days=config_dict["max_cycle_days"],
        )
        await self.save_config(market, config)

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """백업 데이터로부터 상태를 복원합니다."""
        try:
            if backup_data.get("state"):
                await self._restore_state_data(market, backup_data["state"])

            if backup_data.get("config"):
                await self._restore_config_data(market, backup_data["config"])
        except Exception as e:
            logger.error(f"상태 복원 실패: {market}, error: {e}")
            return False
        else:
            logger.info(f"상태 복원 완료: {market}")
            return True

    async def get_active_markets(self) -> list[str]:
        """현재 활성화된 무한매수법 마켓 목록을 반환합니다."""
        try:
            pattern = "infinite_buying:state:*"
            keys = await self._cache_scan(pattern)

            markets = []
            for key in keys:
                # "infinite_buying:state:KRW-BTC" -> "KRW-BTC"
                market = key.split(":")[-1]
                # 상태가 active인지 확인
                state = await self.get_state(market)
                if state and state.is_active:
                    markets.append(market)
        except Exception as e:
            logger.error(f"활성화된 마켓 목록 조회 실패: {e}")
            return []
        else:
            logger.info(f"활성화된 마켓 목록 조회 완료: {len(markets)}개")
            return markets

    async def close(self) -> None:
        """연결을 종료합니다."""
        if self._client:
            try:
                await self._client.close()
            except ClosingError as e:
                logger.error(f"Cache 연결 종료 중 오류: {e}")
            else:
                logger.info("Cache 연결이 종료되었습니다.")
            finally:
                self._client = None
