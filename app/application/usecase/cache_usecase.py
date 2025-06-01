import logging
from typing import Any, cast

from app.domain.repositories.cache_repository import CacheRepository

logger = logging.getLogger(__name__)


class CacheUseCase:
    """캐시 관련 유스케이스"""

    def __init__(self, cache_repository: CacheRepository):
        self.cache_repository = cache_repository

    async def cache_ticker_data(
        self, market: str, ticker_data: dict[str, Any], ttl: int = 300
    ) -> bool:
        """티커 데이터를 캐시에 저장합니다.

        Args:
            market: 마켓 코드 (예: KRW-BTC)
            ticker_data: 티커 데이터
            ttl: 캐시 유지 시간 (초, 기본 5분)
        """
        cache_key = f"ticker:{market}"
        try:
            result = await self.cache_repository.set(cache_key, ticker_data, ttl)
            if result:
                logger.info(f"티커 데이터 캐시 저장 성공 - market: {market}")
                return result
            else:
                logger.warning(f"티커 데이터 캐시 저장 실패 - market: {market}")
                return result
        except Exception as e:
            logger.error(
                f"티커 데이터 캐시 저장 중 오류 - market: {market}, error: {e}"
            )
            return False

    async def get_cached_ticker_data(self, market: str) -> dict[str, Any] | None:
        """캐시에서 티커 데이터를 조회합니다.

        Args:
            market: 마켓 코드 (예: KRW-BTC)

        Returns:
            캐시된 티커 데이터 또는 None
        """
        cache_key = f"ticker:{market}"
        try:
            data = await self.cache_repository.get(cache_key)
            if data:
                logger.debug(f"티커 데이터 캐시 조회 성공 - market: {market}")
                return cast(dict[str, Any], data)
            else:
                logger.debug(f"티커 데이터 캐시 없음 - market: {market}")
                return None
        except Exception as e:
            logger.error(
                f"티커 데이터 캐시 조회 중 오류 - market: {market}, error: {e}"
            )
            return None

    async def cache_account_info(
        self, user_id: str, account_data: dict[str, Any], ttl: int = 60
    ) -> bool:
        """계좌 정보를 캐시에 저장합니다.

        Args:
            user_id: 사용자 ID
            account_data: 계좌 데이터
            ttl: 캐시 유지 시간 (초, 기본 1분)
        """
        cache_key = f"account:{user_id}"
        try:
            result = await self.cache_repository.set(cache_key, account_data, ttl)
            if result:
                logger.info(f"계좌 정보 캐시 저장 성공 - user_id: {user_id}")
                return result
            else:
                logger.warning(f"계좌 정보 캐시 저장 실패 - user_id: {user_id}")
                return result
        except Exception as e:
            logger.error(
                f"계좌 정보 캐시 저장 중 오류 - user_id: {user_id}, error: {e}"
            )
            return False

    async def get_cached_account_info(self, user_id: str) -> dict[str, Any] | None:
        """캐시에서 계좌 정보를 조회합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            캐시된 계좌 정보 또는 None
        """
        cache_key = f"account:{user_id}"
        try:
            data = await self.cache_repository.get(cache_key)
            if data:
                logger.debug(f"계좌 정보 캐시 조회 성공 - user_id: {user_id}")
                return cast(dict[str, Any], data)
            else:
                logger.debug(f"계좌 정보 캐시 없음 - user_id: {user_id}")
                return None
        except Exception as e:
            logger.error(
                f"계좌 정보 캐시 조회 중 오류 - user_id: {user_id}, error: {e}"
            )
            return None

    async def clear_user_cache(self, user_id: str) -> bool:
        """사용자 관련 캐시를 삭제합니다.

        Args:
            user_id: 사용자 ID
        """
        cache_key = f"account:{user_id}"
        try:
            result = await self.cache_repository.delete(cache_key)
            if result:
                logger.info(f"사용자 캐시 삭제 성공 - user_id: {user_id}")
                return result
            else:
                logger.warning(f"사용자 캐시 삭제 실패 - user_id: {user_id}")
                return result
        except Exception as e:
            logger.error(f"사용자 캐시 삭제 중 오류 - user_id: {user_id}, error: {e}")
            return False

    async def health_check(self) -> bool:
        """캐시 서버 상태를 확인합니다."""
        try:
            return await self.cache_repository.ping()
        except Exception as e:
            logger.error(f"캐시 상태 확인 중 오류 - error: {e}")
            return False
