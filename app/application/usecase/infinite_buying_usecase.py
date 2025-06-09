"""
무한매수법 전용 UseCase

무한매수법 알고리즘의 실행, 조회, 종료를 담당하는 비즈니스 로직입니다.
"""

import logging
from decimal import Decimal

from app.domain.enums import OrderSide, OrderType, TradingAction
from app.domain.exceptions import ConfigSaveError, StateSaveError
from app.domain.models.account import Account
from app.domain.models.infinite_buying import (
    InfiniteBuyingConfig,
    InfiniteBuyingPhase,
    InfiniteBuyingResult,
)
from app.domain.models.order import OrderRequest
from app.domain.models.ticker import Ticker
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.infinite_buying_repository import InfiniteBuyingRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository
from app.domain.trade_algorithms.infinite_buying import InfiniteBuyingAlgorithm
from app.domain.types import (
    ActionTaken,
    BuyingRoundInfo,
    InfiniteBuyingMarketStatus,
    InfiniteBuyingOverallStatus,
    InfiniteBuyingStatus,
    MarketName,
)


class InfiniteBuyingUsecase:
    """무한매수법 전용 UseCase"""

    def __init__(
        self,
        account_repository: AccountRepository,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
        infinite_buying_repository: InfiniteBuyingRepository,
    ) -> None:
        self.account_repository = account_repository
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.infinite_buying_repository = infinite_buying_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    def _ticker_to_market_data(self, ticker: Ticker, market: MarketName) -> MarketData:
        """Ticker 객체를 MarketData로 변환"""
        return MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

    async def start_infinite_buying(
        self,
        market: MarketName,
        initial_buy_amount: Decimal,
        target_profit_rate: Decimal = Decimal("0.10"),
        price_drop_threshold: Decimal = Decimal("-0.05"),
        max_buy_rounds: int = 10,
    ) -> InfiniteBuyingResult:
        """
        무한매수법 시작

        Args:
            market: 거래 시장 (예: "KRW-BTC")
            initial_buy_amount: 초기 매수 금액
            target_profit_rate: 목표 수익률 (기본 10%)
            price_drop_threshold: 추가 매수 트리거 하락률 (기본 -5%)
            max_buy_rounds: 최대 매수 회차 (기본 10회)

        Returns:
            InfiniteBuyingResult: 시작 결과
        """
        # 이미 실행 중인지 확인
        existing_state = await self.infinite_buying_repository.get_state(market)
        if existing_state and existing_state.is_active:
            return InfiniteBuyingResult(
                success=False,
                action_taken=ActionTaken.START,
                message=f"{market} 무한매수법이 이미 실행 중입니다.",
            )

        # 설정 생성
        config = InfiniteBuyingConfig(
            initial_buy_amount=initial_buy_amount,
            target_profit_rate=target_profit_rate,
            price_drop_threshold=price_drop_threshold,
            max_buy_rounds=max_buy_rounds,
        )

        # 알고리즘 인스턴스 생성 (초기 상태 설정용)
        algorithm = InfiniteBuyingAlgorithm(config)

        # 상태를 첫 매수 대기 상태로 설정 (cycle_id 자동 생성)
        algorithm.state.reset_cycle(market)

        # 설정 저장
        config_saved = await self.infinite_buying_repository.save_config(market, config)
        if not config_saved:
            raise ConfigSaveError()

        # 초기 상태 저장
        state_saved = await self.infinite_buying_repository.save_state(
            market, algorithm.state
        )
        if not state_saved:
            raise StateSaveError()

        self.logger.info(
            f"무한매수법 시작: {market}, 초기금액: {initial_buy_amount:,.0f}원, "
            f"목표수익률: {target_profit_rate:.1%}"
        )

        return InfiniteBuyingResult(
            success=True,
            action_taken=ActionTaken.START,
            message=f"{market} 무한매수법이 시작되었습니다.",
            current_state=algorithm.state,
        )

    async def stop_infinite_buying(
        self, market: MarketName, *, force_sell: bool = False
    ) -> InfiniteBuyingResult:
        """
        무한매수법 종료

        Args:
            market: 거래 시장
            force_sell: 강제 매도 여부

        Returns:
            InfiniteBuyingResult: 종료 결과
        """
        # 실행 중인 알고리즘 확인
        config = await self.infinite_buying_repository.get_config(market)
        state = await self.infinite_buying_repository.get_state(market)

        if not config or not state or not state.is_active:
            return InfiniteBuyingResult(
                success=False,
                action_taken=ActionTaken.STOP,
                message=f"{market} 무한매수법이 실행 중이 아닙니다.",
            )

        # 임시 알고리즘 인스턴스 생성
        algorithm = InfiniteBuyingAlgorithm(config)
        algorithm.state = state

        # 강제 매도인 경우 현재 보유량 전량 매도
        if force_sell and algorithm.state.is_active:
            # 계좌 정보 조회
            account = await self.account_repository.get_account_balance()

            # 시장 데이터 조회
            ticker = await self.ticker_repository.get_ticker(market)
            market_data = self._ticker_to_market_data(ticker, market)

            # 보유 수량 확인
            target_balance = None
            target_currency = market.split("-")[1]

            for balance in account.balances:
                if balance.currency.value == target_currency:
                    target_balance = balance
                    break

            if target_balance and target_balance.balance > 0:
                # 전량 매도 실행
                sell_result = await algorithm.execute_sell(
                    account, market_data, target_balance.balance, is_force_sell=True
                )

                if sell_result.success:
                    self.logger.info(f"강제 매도 완료: {market}")
                else:
                    self.logger.warning(f"강제 매도 실패: {sell_result.message}")

        # 데이터 삭제
        await self.infinite_buying_repository.clear_market_data(market)

        action_msg = "강제 종료" if force_sell else "정상 종료"

        self.logger.info(f"무한매수법 {action_msg}: {market}")

        return InfiniteBuyingResult(
            success=True,
            action_taken=ActionTaken.STOP,
            message=f"{market} 무한매수법이 {action_msg}되었습니다.",
            current_state=algorithm.state,
        )

    async def get_infinite_buying_market_status(
        self, market: MarketName
    ) -> InfiniteBuyingMarketStatus:
        """
        특정 마켓의 무한매수법 상태 조회

        Args:
            market: 조회할 거래 시장

        Returns:
            InfiniteBuyingMarketStatus: 특정 마켓 상태 정보
        """
        # 상태 조회
        state = await self.infinite_buying_repository.get_state(market)

        if not state or not state.is_active:
            return InfiniteBuyingMarketStatus(
                market=market,
                status=InfiniteBuyingStatus.INACTIVE,
                phase=InfiniteBuyingPhase.INACTIVE,
                cycle_id=None,
                current_round=0,
                total_investment=Decimal("0"),
                total_volume=Decimal("0"),
                average_price=Decimal("0"),
                target_sell_price=Decimal("0"),
                last_buy_price=Decimal("0"),
                last_buy_time=None,
                cycle_start_time=None,
                buying_rounds=[],
                statistics=None,
                recent_history=[],
            )

        # 현재가 조회 및 수익률 계산 (활성 상태인 경우만)
        current_price = None
        current_profit_rate = None
        current_value = None
        profit_loss_amount = None

        if state.is_active:
            try:
                # 현재가 조회
                ticker = await self.ticker_repository.get_ticker(market)
                current_price = ticker.trade_price

                # 수익률 계산
                if state.average_price > 0:
                    current_profit_rate = state.calculate_current_profit_rate(
                        current_price
                    )

                # 현재 평가금액 계산 (보유수량 × 현재가)
                if state.total_volume > 0:
                    current_value = state.total_volume * current_price
                    profit_loss_amount = current_value - state.total_investment

            except Exception as e:
                self.logger.warning(f"현재가 조회 실패: {market}, 오류: {e}")

        # 매수 회차 정보 변환
        buying_rounds = []
        for r in state.buying_rounds:
            buying_rounds.append(
                BuyingRoundInfo(
                    round_number=r.round_number,
                    buy_price=r.buy_price,
                    buy_amount=r.buy_amount,
                    buy_volume=r.buy_volume,
                    timestamp=r.timestamp,
                )
            )

        return InfiniteBuyingMarketStatus(
            market=market,
            status=InfiniteBuyingStatus.ACTIVE
            if state.is_active
            else InfiniteBuyingStatus.INACTIVE,
            phase=state.phase,
            cycle_id=state.cycle_id,
            current_round=state.current_round,
            total_investment=state.total_investment,
            total_volume=state.total_volume,
            average_price=state.average_price,
            target_sell_price=state.target_sell_price,
            last_buy_price=state.last_buy_price,
            last_buy_time=state.last_buy_time,
            cycle_start_time=state.cycle_start_time,
            current_price=current_price,
            current_profit_rate=current_profit_rate,
            current_value=current_value,
            profit_loss_amount=profit_loss_amount,
            buying_rounds=buying_rounds,
            statistics=None,  # 통계 기능 제거
            recent_history=[],  # 히스토리 기능 제거
        )

    async def get_infinite_buying_overall_status(self) -> InfiniteBuyingOverallStatus:
        """
        무한매수법 전체 상태 조회

        Returns:
            InfiniteBuyingOverallStatus: 전체 상태 정보
        """
        # 활성 마켓 목록 조회
        active_markets = await self.infinite_buying_repository.get_active_markets()
        statuses = {}

        for market_name in active_markets:
            market_status = await self.get_infinite_buying_market_status(market_name)
            statuses[market_name] = market_status

        return InfiniteBuyingOverallStatus(
            total_active_markets=len(active_markets),
            active_markets=active_markets,
            statuses=statuses,
        )

    async def _execute_buy_order(
        self, market: MarketName, buy_amount: Decimal
    ) -> InfiniteBuyingResult | None:
        """매수 주문 실행"""
        # 시장가 매수 주문 생성 (KRW 금액 지정)
        buy_order_request = OrderRequest(
            market=market,
            side=OrderSide.BID,  # 매수
            ord_type=OrderType.PRICE,  # 시장가 매수 (KRW 금액 지정)
            price=buy_amount,  # 매수 금액 (KRW)
        )

        try:
            order_result = await self.order_repository.place_order(buy_order_request)
            if not order_result.success:
                self.logger.error(
                    f"매수 주문 실패: {market}, 금액: {buy_amount}, "
                    f"오류: {order_result.error_message}"
                )
                return InfiniteBuyingResult(
                    success=False,
                    action_taken=ActionTaken.BUY,
                    message=f"매수 주문 실패: {order_result.error_message}",
                )

            self.logger.info(f"매수 주문 성공: {market}, 금액: {buy_amount:,.0f}원")

        except Exception as e:
            self.logger.error(f"매수 주문 실행 중 오류: {market}, {e}", exc_info=True)
            return InfiniteBuyingResult(
                success=False,
                action_taken=ActionTaken.BUY,
                message=f"매수 주문 실행 중 오류: {e!s}",
            )

        return None  # 성공 시 None 반환

    async def _execute_sell_order(
        self, market: MarketName, sell_volume: Decimal
    ) -> InfiniteBuyingResult | None:
        """매도 주문 실행"""
        # 시장가 매도 주문 생성 (코인 수량 지정)
        sell_order_request = OrderRequest(
            market=market,
            side=OrderSide.ASK,  # 매도
            ord_type=OrderType.MARKET,  # 시장가 매도 (수량 지정)
            volume=sell_volume,  # 매도 수량 (코인)
        )

        try:
            order_result = await self.order_repository.place_order(sell_order_request)
            if not order_result.success:
                self.logger.error(
                    f"매도 주문 실패: {market}, 수량: {sell_volume}, "
                    f"오류: {order_result.error_message}"
                )
                return InfiniteBuyingResult(
                    success=False,
                    action_taken=ActionTaken.SELL,
                    message=f"매도 주문 실패: {order_result.error_message}",
                )

            self.logger.info(f"매도 주문 성공: {market}, 수량: {sell_volume}")

        except Exception as e:
            self.logger.error(f"매도 주문 실행 중 오류: {market}, {e}", exc_info=True)
            return InfiniteBuyingResult(
                success=False,
                action_taken=ActionTaken.SELL,
                message=f"매도 주문 실행 중 오류: {e!s}",
            )

        return None  # 성공 시 None 반환

    async def _handle_buy_signal(
        self,
        algorithm: InfiniteBuyingAlgorithm,
        market: MarketName,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
    ) -> InfiniteBuyingResult:
        """매수 신호 처리"""
        # 매수 실행
        buy_amount = await algorithm.calculate_buy_amount(
            account,
            market_data,
            signal,
            max_investment_ratio=Decimal("0.5"),
            min_order_amount=Decimal("5000"),
        )

        if buy_amount <= 0:
            return InfiniteBuyingResult(
                success=True,
                action_taken=ActionTaken.HOLD,
                message="매수 금액이 최소 주문 금액 미만입니다.",
                current_state=algorithm.state,
            )

        # 실거래 실행
        buy_result = await self._execute_buy_order(market, buy_amount)
        if buy_result is not None:  # 오류 발생한 경우
            return buy_result

        # 상태 업데이트
        result = await algorithm.execute_buy(account, market_data, buy_amount)

        # 상태 저장
        if result.success:
            await self.infinite_buying_repository.save_state(market, algorithm.state)

        return result

    async def _handle_sell_signal(
        self,
        algorithm: InfiniteBuyingAlgorithm,
        market: MarketName,
        account: Account,
        market_data: MarketData,
        signal: TradingSignal,
    ) -> InfiniteBuyingResult:
        """매도 신호 처리"""
        # 매도 실행
        sell_volume = await algorithm.calculate_sell_amount(
            account, market_data, signal
        )

        if sell_volume <= 0:
            return InfiniteBuyingResult(
                success=True,
                action_taken=ActionTaken.HOLD,
                message="매도 수량이 부족합니다.",
                current_state=algorithm.state,
            )

        # 실거래 실행
        sell_result = await self._execute_sell_order(market, sell_volume)
        if sell_result is not None:  # 오류 발생한 경우
            return sell_result

        # 상태 업데이트
        result = await algorithm.execute_sell(account, market_data, sell_volume)

        # 매도 성공 시 처리
        if result.success:
            await self._handle_sell_success(algorithm, market, result)

        return result

    async def _handle_sell_success(
        self,
        algorithm: InfiniteBuyingAlgorithm,
        market: MarketName,
        result: InfiniteBuyingResult,
    ) -> None:
        """매도 성공 시 후처리"""
        # 상태 저장
        await self.infinite_buying_repository.save_state(market, algorithm.state)

        # 사이클 완료 시 로그
        if algorithm.state.phase == InfiniteBuyingPhase.INACTIVE:
            self.logger.info(
                f"무한매수법 사이클 완료: {market}, 수익률: {result.profit_rate}"
            )

    async def execute_infinite_buying_cycle(
        self, market: MarketName
    ) -> InfiniteBuyingResult:
        """
        무한매수법 사이클 실행 (스케줄러에서 호출)

        Args:
            market: 거래 시장

        Returns:
            InfiniteBuyingResult: 실행 결과
        """
        # 설정과 상태 조회
        config = await self.infinite_buying_repository.get_config(market)
        state = await self.infinite_buying_repository.get_state(market)

        if not config or not state or not state.is_active:
            return InfiniteBuyingResult(
                success=False,
                action_taken=ActionTaken.EXECUTE,
                message=f"{market} 무한매수법이 실행 중이 아닙니다.",
            )

        # 임시 알고리즘 인스턴스 생성
        algorithm = InfiniteBuyingAlgorithm(config)
        algorithm.state = state

        # 계좌 정보 조회
        account = await self.account_repository.get_account_balance()

        # 시장 데이터 조회
        ticker = await self.ticker_repository.get_ticker(market)
        market_data = self._ticker_to_market_data(ticker, market)

        # 신호 분석
        signal = await algorithm.analyze_signal(account, market_data)

        # 신호에 따른 실행
        if signal.action == TradingAction.BUY:
            return await self._handle_buy_signal(
                algorithm, market, account, market_data, signal
            )
        elif signal.action == TradingAction.SELL:
            return await self._handle_sell_signal(
                algorithm, market, account, market_data, signal
            )

        # HOLD 신호
        return InfiniteBuyingResult(
            success=True,
            action_taken=ActionTaken.HOLD,
            message=signal.reason,
            current_state=algorithm.state,
        )

    async def get_active_markets(self) -> list[MarketName]:
        """실행 중인 시장 목록 반환"""
        return await self.infinite_buying_repository.get_active_markets()

    async def is_market_active(self, market: MarketName) -> bool:
        """특정 시장이 실행 중인지 확인"""
        state = await self.infinite_buying_repository.get_state(market)
        return state is not None and state.is_active
