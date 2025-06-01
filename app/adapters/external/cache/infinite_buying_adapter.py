"""
Redis를 사용한 무한매수법 데이터 저장 어댑터
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.adapters.external.cache.config import CacheConfig
from app.domain.models.infinite_buying import (
    BuyingRound,
    InfiniteBuyingConfig,
    InfiniteBuyingPhase,
    InfiniteBuyingResult,
    InfiniteBuyingState,
)
from app.domain.repositories.infinite_buying_repository import InfiniteBuyingRepository

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Decimal 타입을 JSON으로 직렬화하기 위한 인코더"""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class RedisInfiniteBuyingAdapter(InfiniteBuyingRepository):
    """Redis를 사용한 무한매수법 데이터 저장 어댑터"""

    def __init__(self, cache_adapter: Any) -> None:
        """
        Args:
            cache_adapter: ValkeyAdapter 인스턴스
        """
        self.cache = cache_adapter

    def _get_config_key(self, market: str) -> str:
        """설정 키 생성"""
        return f"infinite_buying:{market}:config"

    def _get_state_key(self, market: str) -> str:
        """상태 키 생성"""
        return f"infinite_buying:{market}:state"

    def _get_rounds_key(self, market: str) -> str:
        """매수 회차 키 생성"""
        return f"infinite_buying:{market}:rounds"

    def _get_cycle_key(self, market: str, cycle_id: str) -> str:
        """사이클 히스토리 키 생성"""
        return f"infinite_buying:{market}:cycles:{cycle_id}"

    def _get_cycle_index_key(self, market: str) -> str:
        """사이클 인덱스 키 생성"""
        return f"infinite_buying:{market}:cycle_index"

    def _get_stats_key(self, market: str) -> str:
        """통계 키 생성"""
        return f"infinite_buying:stats:{market}"

    def _serialize_config(self, config: InfiniteBuyingConfig) -> dict[str, Any]:
        """설정을 직렬화"""
        return {
            "initial_buy_amount": str(config.initial_buy_amount),
            "add_buy_multiplier": str(config.add_buy_multiplier),
            "target_profit_rate": str(config.target_profit_rate),
            "price_drop_threshold": str(config.price_drop_threshold),
            "force_stop_loss_rate": str(config.force_stop_loss_rate),
            "max_buy_rounds": config.max_buy_rounds,
            "max_investment_ratio": str(config.max_investment_ratio),
            "min_buy_interval_minutes": config.min_buy_interval_minutes,
            "max_cycle_days": config.max_cycle_days,
        }

    def _deserialize_config(self, data: dict[str, Any]) -> InfiniteBuyingConfig:
        """설정을 역직렬화"""
        return InfiniteBuyingConfig(
            initial_buy_amount=Decimal(data["initial_buy_amount"]),
            add_buy_multiplier=Decimal(data["add_buy_multiplier"]),
            target_profit_rate=Decimal(data["target_profit_rate"]),
            price_drop_threshold=Decimal(data["price_drop_threshold"]),
            force_stop_loss_rate=Decimal(data["force_stop_loss_rate"]),
            max_buy_rounds=data["max_buy_rounds"],
            max_investment_ratio=Decimal(data["max_investment_ratio"]),
            min_buy_interval_minutes=data["min_buy_interval_minutes"],
            max_cycle_days=data["max_cycle_days"],
        )

    def _serialize_state(self, state: InfiniteBuyingState) -> dict[str, Any]:
        """상태를 직렬화"""
        return {
            "market": state.market,
            "phase": state.phase.value,
            "cycle_id": state.cycle_id,
            "current_round": state.current_round,
            "total_investment": str(state.total_investment),
            "total_volume": str(state.total_volume),
            "average_price": str(state.average_price),
            "last_buy_price": str(state.last_buy_price),
            "last_buy_time": state.last_buy_time.isoformat() if state.last_buy_time else None,
            "cycle_start_time": state.cycle_start_time.isoformat() if state.cycle_start_time else None,
            "target_sell_price": str(state.target_sell_price),
        }

    def _deserialize_state(self, data: dict[str, Any]) -> InfiniteBuyingState:
        """상태를 역직렬화"""
        state = InfiniteBuyingState(
            market=data["market"],
            phase=InfiniteBuyingPhase(data["phase"]),
            cycle_id=data["cycle_id"],
            current_round=data["current_round"],
            total_investment=Decimal(data["total_investment"]),
            total_volume=Decimal(data["total_volume"]),
            average_price=Decimal(data["average_price"]),
            last_buy_price=Decimal(data["last_buy_price"]),
            target_sell_price=Decimal(data["target_sell_price"]),
        )

        if data["last_buy_time"]:
            state.last_buy_time = datetime.fromisoformat(data["last_buy_time"])
        if data["cycle_start_time"]:
            state.cycle_start_time = datetime.fromisoformat(data["cycle_start_time"])

        return state

    def _serialize_buying_round(self, round_data: BuyingRound) -> dict[str, Any]:
        """매수 회차를 직렬화"""
        return {
            "round_number": round_data.round_number,
            "buy_price": str(round_data.buy_price),
            "buy_amount": str(round_data.buy_amount),
            "buy_volume": str(round_data.buy_volume),
            "timestamp": round_data.timestamp.isoformat(),
        }

    def _deserialize_buying_round(self, data: dict[str, Any]) -> BuyingRound:
        """매수 회차를 역직렬화"""
        return BuyingRound(
            round_number=data["round_number"],
            buy_price=Decimal(data["buy_price"]),
            buy_amount=Decimal(data["buy_amount"]),
            buy_volume=Decimal(data["buy_volume"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    async def save_config(self, market: str, config: InfiniteBuyingConfig) -> bool:
        """무한매수법 설정을 저장합니다."""
        try:
            key = self._get_config_key(market)
            data = self._serialize_config(config)
            result = await self.cache.set(key, data, ttl=None)  # 설정은 TTL 없이 저장
            logger.info(f"무한매수법 설정 저장 완료 - market: {market}")
            return bool(result)
        except Exception as e:
            logger.error(f"무한매수법 설정 저장 실패 - market: {market}, error: {e}")
            return False

    async def get_config(self, market: str) -> InfiniteBuyingConfig | None:
        """무한매수법 설정을 조회합니다."""
        try:
            key = self._get_config_key(market)
            data = await self.cache.get(key)
            if data is None:
                return None
            return self._deserialize_config(data)
        except Exception as e:
            logger.error(f"무한매수법 설정 조회 실패 - market: {market}, error: {e}")
            return None

    async def save_state(self, market: str, state: InfiniteBuyingState) -> bool:
        """현재 무한매수법 상태를 저장합니다."""
        try:
            key = self._get_state_key(market)
            data = self._serialize_state(state)
            result = await self.cache.set(key, data, ttl=86400)  # 24시간 TTL
            logger.debug(f"무한매수법 상태 저장 완료 - market: {market}, phase: {state.phase.value}")
            return bool(result)
        except Exception as e:
            logger.error(f"무한매수법 상태 저장 실패 - market: {market}, error: {e}")
            return False

    async def get_state(self, market: str) -> InfiniteBuyingState | None:
        """현재 무한매수법 상태를 조회합니다. buying_rounds는 별도 메서드로 조회 권장."""
        try:
            key = self._get_state_key(market)
            data = await self.cache.get(key)
            if data is None:
                return None

            state = self._deserialize_state(data)
            # 성능상 이유로 buying_rounds는 빈 리스트로 초기화
            # 필요시 get_buying_rounds() 메서드를 별도 호출
            state.buying_rounds = []
            
            return state
        except Exception as e:
            logger.error(f"무한매수법 상태 조회 실패 - market: {market}, error: {e}")
            return None

    async def get_state_with_rounds(self, market: str) -> InfiniteBuyingState | None:
        """매수 회차 정보를 포함한 상태를 조회합니다."""
        try:
            state = await self.get_state(market)
            if state is None:
                return None
                
            # 매수 회차 정보도 함께 로드
            rounds = await self.get_buying_rounds(market)
            state.buying_rounds = rounds
            
            return state
        except Exception as e:
            logger.error(f"무한매수법 상태(회차 포함) 조회 실패 - market: {market}, error: {e}")
            return None

    async def add_buying_round(self, market: str, buying_round: BuyingRound) -> bool:
        """매수 회차를 추가합니다."""
        try:
            key = self._get_rounds_key(market)
            round_data = self._serialize_buying_round(buying_round)

            # 기존 회차들 조회
            existing_rounds = await self.cache.get(key) or []
            
            # 중복 회차 체크
            for existing_round in existing_rounds:
                if existing_round.get("round_number") == buying_round.round_number:
                    logger.warning(f"중복 매수 회차 감지 - market: {market}, round: {buying_round.round_number}")
                    return False
            
            existing_rounds.append(round_data)

            result = await self.cache.set(key, existing_rounds, ttl=86400)  # 24시간 TTL
            logger.info(f"매수 회차 추가 완료 - market: {market}, round: {buying_round.round_number}")
            return bool(result)
        except Exception as e:
            logger.error(f"매수 회차 추가 실패 - market: {market}, error: {e}")
            return False

    async def get_buying_rounds(
        self, market: str, cycle_id: str | None = None
    ) -> list[BuyingRound]:
        """매수 회차 목록을 조회합니다."""
        try:
            if cycle_id:
                # 특정 사이클의 히스토리에서 조회
                cycle_key = self._get_cycle_key(market, cycle_id)
                cycle_data = await self.cache.get(cycle_key)
                if cycle_data and "buying_rounds" in cycle_data:
                    rounds_data = cycle_data["buying_rounds"]
                else:
                    return []
            else:
                # 현재 활성 사이클의 회차들 조회
                key = self._get_rounds_key(market)
                rounds_data = await self.cache.get(key) or []

            return [self._deserialize_buying_round(round_data) for round_data in rounds_data]
        except Exception as e:
            logger.error(f"매수 회차 조회 실패 - market: {market}, error: {e}")
            return []

    async def save_cycle_history(
        self,
        market: str,
        cycle_id: str,
        state: InfiniteBuyingState,
        result: InfiniteBuyingResult,
    ) -> bool:
        """완료된 사이클 히스토리를 저장합니다."""
        try:
            # 현재 매수 회차들 조회 (삭제 전에)
            rounds = await self.get_buying_rounds(market)
            
            cycle_key = self._get_cycle_key(market, cycle_id)
            
            history_data = {
                "cycle_id": cycle_id,
                "market": market,
                "state": self._serialize_state(state),
                "result": {
                    "success": result.success,
                    "action_taken": result.action_taken,
                    "message": result.message,
                    "trade_price": str(result.trade_price) if result.trade_price else None,
                    "trade_amount": str(result.trade_amount) if result.trade_amount else None,
                    "trade_volume": str(result.trade_volume) if result.trade_volume else None,
                    "profit_rate": str(result.profit_rate) if result.profit_rate else None,
                },
                "buying_rounds": [self._serialize_buying_round(r) for r in rounds],
                "completed_at": datetime.now().isoformat(),
            }

            # 사이클 히스토리 저장
            cycle_save_result = await self.cache.set(cycle_key, history_data, ttl=2592000)  # 30일 TTL
            
            # 사이클 인덱스에 추가 (최신 순으로 관리)
            index_key = self._get_cycle_index_key(market)
            cycle_index = await self.cache.get(index_key) or []
            
            # 새 사이클을 맨 앞에 추가 (최신 순)
            cycle_index.insert(0, {
                "cycle_id": cycle_id,
                "completed_at": history_data["completed_at"],
                "success": result.success,
                "profit_rate": str(result.profit_rate) if result.profit_rate else None,
            })
            
            # 인덱스 크기 제한 (최대 1000개)
            if len(cycle_index) > 1000:
                cycle_index = cycle_index[:1000]
            
            index_save_result = await self.cache.set(index_key, cycle_index, ttl=2592000)
            
            # 사이클 완료 시에만 현재 활성 데이터 정리
            if result.success:
                await self.cache.delete(self._get_rounds_key(market))
                logger.info(f"성공한 사이클 완료로 활성 데이터 정리 - market: {market}")

            logger.info(f"사이클 히스토리 저장 완료 - market: {market}, cycle_id: {cycle_id}")
            return bool(cycle_save_result and index_save_result)
        except Exception as e:
            logger.error(f"사이클 히스토리 저장 실패 - market: {market}, error: {e}")
            return False

    async def get_cycle_history(
        self, market: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """완료된 사이클 히스토리를 조회합니다."""
        try:
            index_key = self._get_cycle_index_key(market)
            cycle_index = await self.cache.get(index_key) or []
            
            # limit 적용
            limited_index = cycle_index[:limit]
            
            # 각 사이클의 상세 정보 조회
            history_list = []
            for cycle_info in limited_index:
                cycle_id = cycle_info["cycle_id"]
                cycle_key = self._get_cycle_key(market, cycle_id)
                cycle_data = await self.cache.get(cycle_key)
                
                if cycle_data:
                    history_list.append(cycle_data)
                else:
                    # 인덱스에는 있지만 실제 데이터가 없는 경우 (TTL 만료 등)
                    logger.warning(f"사이클 데이터 불일치 - market: {market}, cycle_id: {cycle_id}")
            
            logger.info(f"사이클 히스토리 조회 완료 - market: {market}, count: {len(history_list)}")
            return history_list
        except Exception as e:
            logger.error(f"사이클 히스토리 조회 실패 - market: {market}, error: {e}")
            return []

    async def get_trade_statistics(self, market: str) -> dict[str, Any]:
        """거래 통계를 조회합니다."""
        try:
            key = self._get_stats_key(market)
            stats = await self.cache.get(key)
            if stats is None:
                # 기본 통계 구조 반환
                return {
                    "total_cycles": 0,
                    "successful_cycles": 0,
                    "total_profit_rate": "0",
                    "average_profit_rate": "0",
                    "max_profit_rate": "0",
                    "min_profit_rate": "0",
                    "last_updated": datetime.now().isoformat(),
                }
            return dict(stats)
        except Exception as e:
            logger.error(f"거래 통계 조회 실패 - market: {market}, error: {e}")
            return {}

    async def update_statistics(
        self, market: str, result: InfiniteBuyingResult
    ) -> bool:
        """거래 통계를 업데이트합니다."""
        try:
            stats = await self.get_trade_statistics(market)

            stats["total_cycles"] += 1
            if result.success and result.profit_rate:
                stats["successful_cycles"] += 1

                profit_rate = Decimal(str(result.profit_rate))
                current_total = Decimal(stats["total_profit_rate"])
                stats["total_profit_rate"] = str(current_total + profit_rate)
                stats["average_profit_rate"] = str(
                    Decimal(stats["total_profit_rate"]) / stats["successful_cycles"]
                )

                max_profit = Decimal(stats["max_profit_rate"])
                min_profit = Decimal(stats["min_profit_rate"])

                if profit_rate > max_profit:
                    stats["max_profit_rate"] = str(profit_rate)
                if stats["successful_cycles"] == 1 or profit_rate < min_profit:
                    stats["min_profit_rate"] = str(profit_rate)

            stats["last_updated"] = datetime.now().isoformat()

            key = self._get_stats_key(market)
            result_save = await self.cache.set(key, stats, ttl=None)  # 통계는 영구 저장
            return bool(result_save)
        except Exception as e:
            logger.error(f"거래 통계 업데이트 실패 - market: {market}, error: {e}")
            return False

    async def clear_market_data(self, market: str) -> bool:
        """특정 마켓의 모든 데이터를 삭제합니다."""
        try:
            keys_to_delete = [
                self._get_config_key(market),
                self._get_state_key(market),
                self._get_rounds_key(market),
                self._get_cycle_index_key(market),
                self._get_stats_key(market),
            ]

            delete_count = 0
            for key in keys_to_delete:
                if await self.cache.delete(key):
                    delete_count += 1

            logger.info(f"마켓 데이터 삭제 완료 - market: {market}, deleted: {delete_count}/{len(keys_to_delete)}")
            return delete_count > 0
        except Exception as e:
            logger.error(f"마켓 데이터 삭제 실패 - market: {market}, error: {e}")
            return False

    async def backup_state(self, market: str) -> dict[str, Any]:
        """현재 상태를 백업용 딕셔너리로 반환합니다."""
        try:
            backup_data: dict[str, Any] = {
                "market": market,
                "timestamp": datetime.now().isoformat(),
                "config": None,
                "state": None,
                "rounds": [],
                "statistics": None,
                "cycle_index": [],
            }

            # 설정 백업
            config = await self.get_config(market)
            if config:
                backup_data["config"] = self._serialize_config(config)

            # 상태 백업
            state = await self.get_state(market)
            if state:
                backup_data["state"] = self._serialize_state(state)

            # 매수 회차 백업
            rounds = await self.get_buying_rounds(market)
            backup_data["rounds"] = [self._serialize_buying_round(r) for r in rounds]

            # 통계 백업
            stats = await self.get_trade_statistics(market)
            backup_data["statistics"] = stats
            
            # 사이클 인덱스 백업
            index_key = self._get_cycle_index_key(market)
            cycle_index = await self.cache.get(index_key) or []
            backup_data["cycle_index"] = cycle_index

            logger.info(f"상태 백업 완료 - market: {market}")
            return backup_data
        except Exception as e:
            logger.error(f"상태 백업 실패 - market: {market}, error: {e}")
            return {}

    async def restore_state(self, market: str, backup_data: dict[str, Any]) -> bool:
        """백업 데이터로부터 상태를 복원합니다."""
        try:
            # 기존 데이터 삭제
            await self.clear_market_data(market)

            success_count = 0
            total_operations = 0

            # 설정 복원
            if backup_data.get("config"):
                config_data = backup_data["config"]
                if isinstance(config_data, dict):
                    config = self._deserialize_config(config_data)
                    if await self.save_config(market, config):
                        success_count += 1
                total_operations += 1

            # 상태 복원
            if backup_data.get("state"):
                state_data = backup_data["state"]
                if isinstance(state_data, dict):
                    state = self._deserialize_state(state_data)
                    if await self.save_state(market, state):
                        success_count += 1
                total_operations += 1

            # 매수 회차 복원
            if backup_data.get("rounds"):
                rounds_key = self._get_rounds_key(market)
                if await self.cache.set(rounds_key, backup_data["rounds"], ttl=86400):
                    success_count += 1
                total_operations += 1

            # 통계 복원
            if backup_data.get("statistics"):
                stats_data = backup_data["statistics"]
                if isinstance(stats_data, dict):
                    stats_key = self._get_stats_key(market)
                    if await self.cache.set(stats_key, stats_data, ttl=None):
                        success_count += 1
                total_operations += 1
                        
            # 사이클 인덱스 복원
            if backup_data.get("cycle_index"):
                index_key = self._get_cycle_index_key(market)
                if await self.cache.set(index_key, backup_data["cycle_index"], ttl=2592000):
                    success_count += 1
                total_operations += 1

            logger.info(f"상태 복원 완료 - market: {market}, success: {success_count}/{total_operations}")
            return success_count == total_operations
        except Exception as e:
            logger.error(f"상태 복원 실패 - market: {market}, error: {e}")
            return False
