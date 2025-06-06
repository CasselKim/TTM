"""
매매 실행 서비스

알고리즘에서 생성된 신호를 바탕으로 실제 매매를 실행하는 서비스입니다.
"""

import logging
from decimal import Decimal

from app.application.dto.trading_dto import TradingResult
from app.domain.enums import OrderSide, OrderType, TradingAction
from app.domain.models.account import Account
from app.domain.models.order import OrderRequest
from app.domain.models.trading import MarketData, TradingConfig, TradingSignal
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.trade_algorithms.base import TradingAlgorithm


class TradeService:
    """
    매매 실행 서비스

    알고리즘과 분리되어 순수하게 매매 실행만을 담당합니다.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
    ) -> None:
        self.account_repository = account_repository
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_trading_cycle(
        self, algorithm: TradingAlgorithm, config: TradingConfig
    ) -> TradingResult:
        """
        매매 사이클 실행

        1. 계좌 상태 확인
        2. 시장 데이터 수집
        3. 알고리즘으로 신호 분석
        4. 매매 실행
        """
        try:
            # 1. 계좌 상태 확인
            account = await self.account_repository.get_account_balance()
            if not self._validate_account_status(account, config):
                return TradingResult(
                    success=False, message="계좌 상태가 거래에 적합하지 않습니다."
                )

            # 2. 시장 데이터 수집
            market_data = await self._collect_market_data(config)

            # 3. 알고리즘으로 매매 신호 분석
            signal = await algorithm.analyze_signal(account, market_data)

            # 4. 매매 실행
            if signal.action == TradingAction.BUY:
                return await self._execute_buy_order(
                    algorithm, account, market_data, signal, config
                )
            elif signal.action == TradingAction.SELL:
                return await self._execute_sell_order(
                    algorithm, account, market_data, signal, config
                )
            else:
                return TradingResult(
                    success=True, message=f"HOLD 신호: {signal.reason}"
                )

        except Exception as e:
            self.logger.error(f"매매 사이클 실행 중 오류 발생: {e}")
            return TradingResult(success=False, message=f"매매 사이클 실행 실패: {e!s}")

    async def _collect_market_data(self, config: TradingConfig) -> MarketData:
        """시장 데이터 수집"""
        market = f"{config.base_currency.value}-{config.target_currency.value}"
        ticker = await self.ticker_repository.get_ticker(market)

        return MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

    def _validate_account_status(self, account: Account, config: TradingConfig) -> bool:
        """계좌 상태 검증"""
        if account.total_balance_krw < config.min_order_amount:
            self.logger.warning("계좌 잔액이 최소 주문 금액보다 적습니다.")
            return False
        return True

    async def _execute_buy_order(
        self,
        algorithm: TradingAlgorithm,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
        config: TradingConfig,
    ) -> TradingResult:
        """매수 주문 실행"""
        try:
            # 알고리즘으로 매수 금액 계산
            buy_amount = await algorithm.calculate_buy_amount(
                account,
                market_data,
                signal,
                config.max_investment_ratio,
                config.min_order_amount,
            )

            if buy_amount < config.min_order_amount:
                return TradingResult(
                    success=False,
                    message=f"매수 금액이 최소 주문 금액({config.min_order_amount})보다 적습니다.",
                )

            # 실제 주문 실행
            order_request = OrderRequest(
                market=market_data.market,
                side=OrderSide.BID,
                ord_type=OrderType.PRICE,
                price=buy_amount,
            )

            order_result = await self.order_repository.place_order(order_request)

            if order_result.success and order_result.order:
                return TradingResult(
                    success=True,
                    message="매수 주문이 성공적으로 실행되었습니다.",
                    order_uuid=order_result.order.uuid,
                    executed_amount=buy_amount,
                    executed_price=market_data.current_price,
                )
            else:
                return TradingResult(
                    success=False,
                    message=f"매수 주문 실패: {order_result.error_message}",
                )

        except Exception as e:
            self.logger.error(f"매수 주문 실행 중 오류: {e}")
            return TradingResult(success=False, message=f"매수 주문 실행 실패: {e!s}")

    async def _execute_sell_order(
        self,
        algorithm: TradingAlgorithm,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
        config: TradingConfig,
    ) -> TradingResult:
        """매도 주문 실행"""
        try:
            # 알고리즘으로 매도 수량 계산
            sell_volume = await algorithm.calculate_sell_amount(
                account, market_data, signal
            )

            if sell_volume <= Decimal("0"):
                return TradingResult(success=False, message="매도할 수량이 없습니다.")

            # 실제 주문 실행
            order_request = OrderRequest(
                market=market_data.market,
                side=OrderSide.ASK,
                ord_type=OrderType.MARKET,
                volume=sell_volume,
            )

            order_result = await self.order_repository.place_order(order_request)

            if order_result.success and order_result.order:
                sell_amount = sell_volume * market_data.current_price
                return TradingResult(
                    success=True,
                    message="매도 주문이 성공적으로 실행되었습니다.",
                    order_uuid=order_result.order.uuid,
                    executed_amount=sell_amount,
                    executed_price=market_data.current_price,
                )
            else:
                return TradingResult(
                    success=False,
                    message=f"매도 주문 실패: {order_result.error_message}",
                )

        except Exception as e:
            self.logger.error(f"매도 주문 실행 중 오류: {e}")
            return TradingResult(success=False, message=f"매도 주문 실행 실패: {e!s}")
