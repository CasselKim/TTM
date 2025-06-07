"""
매매 알고리즘 실행 UseCase

매매 알고리즘을 실행하는 비즈니스 로직을 담당합니다.
"""

import logging
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.application.dto.trading_dto import TradingResult
from app.domain.constants import TradingConstants
from app.domain.exceptions import UnsupportedAlgorithmError
from app.domain.models.account import Currency
from app.domain.models.enums import TradingMode
from app.domain.models.trading import TradingConfig
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.services.trade_service import TradeService
from app.domain.trade_algorithms.base import TradingAlgorithm
from app.domain.trade_algorithms.simple import SimpleTradingAlgorithm


class AlgorithmType(StrEnum):
    """사용 가능한 알고리즘 타입"""

    SIMPLE = "simple"  # 간단한 변동률 기반 알고리즘
    # 향후 추가 가능: RSI = "rsi", MACD = "macd", etc.


class TradingUsecase:
    """매매 알고리즘 실행 UseCase"""

    def __init__(
        self,
        account_repository: AccountRepository,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
    ) -> None:
        self.trade_service = TradeService(
            account_repository=account_repository,
            order_repository=order_repository,
            ticker_repository=ticker_repository,
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_trading_algorithm(
        self,
        target_currency: Currency = Currency.BTC,
        mode: TradingMode = TradingMode.LIVE,
        algorithm_type: AlgorithmType = AlgorithmType.SIMPLE,
        max_investment_ratio: Decimal = TradingConstants.DEFAULT_MAX_INVESTMENT_RATIO,
        min_order_amount: Decimal = TradingConstants.DEFAULT_MIN_ORDER_AMOUNT,
    ) -> TradingResult:
        """
        매매 알고리즘 실행

        Args:
            target_currency: 거래 대상 통화
            mode: 거래 모드 (실거래)
            algorithm_type: 사용할 알고리즘 타입
            max_investment_ratio: 최대 투자 비율
            min_order_amount: 최소 주문 금액

        Returns:
            TradingResult: 매매 실행 결과
        """
        try:
            # 1. 거래 설정 생성
            config = TradingConfig(
                mode=mode,
                target_currency=target_currency,
                base_currency=Currency.KRW,
                max_investment_ratio=max_investment_ratio,
                min_order_amount=min_order_amount,
                stop_loss_ratio=TradingConstants.DEFAULT_STOP_LOSS_RATIO,
                take_profit_ratio=TradingConstants.DEFAULT_TAKE_PROFIT_RATIO,
            )

            # 2. 알고리즘 생성
            algorithm = self._create_algorithm(algorithm_type)

            # 3. 매매 사이클 실행 (TradeService 사용)
            result = await self.trade_service.execute_trading_cycle(algorithm, config)

            # 4. 결과 로깅
            self._log_trading_result(result, target_currency, mode, algorithm_type)

            return result

        except Exception as e:
            error_msg = f"매매 사이클 실행 실패: {e!s}"
            self.logger.exception(
                f"[{mode.value}] {target_currency.value} ({algorithm_type.value}) "
                "거래 실패"
            )
            return TradingResult(success=False, message=error_msg)

    def _create_algorithm(self, algorithm_type: AlgorithmType) -> TradingAlgorithm:
        """알고리즘 타입에 따라 적절한 알고리즘 인스턴스 생성"""

        match algorithm_type:
            case AlgorithmType.SIMPLE:
                return SimpleTradingAlgorithm()
            case _:
                # algorithm_type이 enum인지 확인해서 value 속성 사용
                error_value = (
                    algorithm_type.value
                    if hasattr(algorithm_type, "value")
                    else str(algorithm_type)
                )
                raise UnsupportedAlgorithmError(error_value)

    def _log_trading_result(
        self,
        result: TradingResult,
        target_currency: Currency,
        mode: TradingMode,
        algorithm_type: AlgorithmType,
    ) -> None:
        """매매 결과 로깅"""
        prefix = (
            f"[{mode.value.upper()}] {target_currency.value} ({algorithm_type.value})"
        )

        if result.success:
            if result.order_uuid:
                # 실제 거래 실행됨
                self.logger.info(f"{prefix} 거래 실행됨: {result.message}")
                self.logger.info(f"{prefix} 주문 UUID: {result.order_uuid}")
                if result.executed_amount:
                    self.logger.info(
                        f"{prefix} 실행 금액: {result.executed_amount:,.0f}원"
                    )
                if result.executed_price:
                    self.logger.info(
                        f"{prefix} 실행 가격: {result.executed_price:,.0f}원"
                    )
            else:
                # HOLD 신호 등
                self.logger.info(f"{prefix} {result.message}")
        else:
            # 거래 실패
            self.logger.error(f"{prefix} 거래 실패: {result.message}")

    def get_trading_status(self) -> dict[str, Any]:
        """매매 상태 정보 조회"""
        return {
            "service": "TradingUsecase",
            "available_currencies": [currency.value for currency in Currency],
            "available_modes": [mode.value for mode in TradingMode],
            "available_algorithms": [algo.value for algo in AlgorithmType],
            "default_config": {
                "max_investment_ratio": str(
                    TradingConstants.DEFAULT_MAX_INVESTMENT_RATIO
                ),
                "min_order_amount": str(TradingConstants.DEFAULT_MIN_ORDER_AMOUNT),
                "stop_loss_ratio": str(TradingConstants.DEFAULT_STOP_LOSS_RATIO),
                "take_profit_ratio": str(TradingConstants.DEFAULT_TAKE_PROFIT_RATIO),
            },
        }
