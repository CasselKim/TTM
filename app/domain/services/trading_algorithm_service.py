import logging
from abc import ABC, abstractmethod
from decimal import Decimal

from app.application.dto.trading_dto import TradingResult
from app.domain.models.account import Account, Balance, Currency
from app.domain.models.enums import TradingMode
from app.domain.models.order import OrderRequest, OrderSide, OrderType
from app.domain.models.trading import MarketData, TradingConfig, TradingSignal
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.ticker_repository import TickerRepository


class TradingAlgorithmService(ABC):
    """
    매매 알고리즘의 추상 기본 클래스

    템플릿 메서드 패턴을 사용하여 매매 알고리즘의 기본 흐름을 정의하고,
    구체적인 매매 로직은 하위 클래스에서 구현하도록 추상화
    """

    def __init__(
        self,
        config: TradingConfig,
        account_repository: AccountRepository,
        order_repository: OrderRepository,
        ticker_repository: TickerRepository,
    ) -> None:
        self.config = config
        self.account_repository = account_repository
        self.order_repository = order_repository
        self.ticker_repository = ticker_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    # ========== 템플릿 메서드 (기본 흐름 정의) ==========

    async def run_trading_cycle(self) -> TradingResult:
        """
        매매 사이클 실행 (템플릿 메서드)

        1. 계좌 상태 확인
        2. 시장 데이터 수집
        3. 매매 신호 분석
        4. 매매 실행
        """
        try:
            # 1. 계좌 상태 확인
            account = await self._get_account_status()
            if not self._validate_account_status(account):
                return TradingResult(
                    success=False, message="계좌 상태가 거래에 적합하지 않습니다."
                )

            # 2. 시장 데이터 수집
            market_data = await self._collect_market_data()

            # 3. 매매 신호 분석 (하위 클래스에서 구현)
            signal = await self.analyze_trading_signal(account, market_data)

            # 4. 매매 실행
            if signal.action == "BUY":
                return await self._execute_buy_order(account, market_data, signal)
            elif signal.action == "SELL":
                return await self._execute_sell_order(account, market_data, signal)
            else:
                return TradingResult(
                    success=True, message=f"HOLD 신호: {signal.reason}"
                )

        except Exception as e:
            self.logger.error(f"매매 사이클 실행 중 오류 발생: {e}")
            return TradingResult(success=False, message=f"매매 사이클 실행 실패: {e!s}")

    # ========== 추상 메서드 (하위 클래스에서 구현 필수) ==========

    @abstractmethod
    async def analyze_trading_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """
        매매 신호 분석 (하위 클래스에서 구현)

        Args:
            account: 계좌 정보
            market_data: 시장 데이터

        Returns:
            TradingSignal: 매매 신호
        """
        pass

    @abstractmethod
    async def calculate_buy_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매수 금액 계산 (하위 클래스에서 구현)

        Args:
            account: 계좌 정보
            market_data: 시장 데이터
            signal: 매매 신호

        Returns:
            Decimal: 매수 금액
        """
        pass

    @abstractmethod
    async def calculate_sell_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매도 수량 계산 (하위 클래스에서 구현)

        Args:
            account: 계좌 정보
            market_data: 시장 데이터
            signal: 매매 신호

        Returns:
            Decimal: 매도 수량
        """
        pass

    # ========== 훅 메서드 (하위 클래스에서 선택적 오버라이드) ==========

    async def pre_trading_hook(self, account: Account, market_data: MarketData) -> bool:
        """
        매매 실행 전 훅 메서드 (선택적 오버라이드)

        Returns:
            bool: 매매 진행 여부
        """
        return True

    async def post_trading_hook(
        self, result: TradingResult, account: Account, market_data: MarketData
    ) -> None:
        """
        매매 실행 후 훅 메서드 (선택적 오버라이드)
        """
        # 기본 구현: 로깅만 수행
        if result.success:
            self.logger.info(f"매매 성공: {result.message}")
        else:
            self.logger.warning(f"매매 실패: {result.message}")

    # ========== 공통 유틸리티 메서드 ==========

    async def _get_account_status(self) -> Account:
        """계좌 상태 조회"""
        return await self.account_repository.get_account_balance()

    async def _collect_market_data(self) -> MarketData:
        """시장 데이터 수집"""
        market = (
            f"{self.config.base_currency.value}-{self.config.target_currency.value}"
        )
        ticker = await self.ticker_repository.get_ticker(market)

        return MarketData(
            market=market,
            current_price=ticker.trade_price,
            volume_24h=ticker.acc_trade_volume_24h,
            change_rate_24h=ticker.signed_change_rate,
        )

    def _validate_account_status(self, account: Account) -> bool:
        """계좌 상태 검증"""
        # 기본 검증 로직
        if account.total_balance_krw < self.config.min_order_amount:
            self.logger.warning("계좌 잔액이 최소 주문 금액보다 적습니다.")
            return False
        return True

    def _get_available_krw_balance(self, account: Account) -> Decimal:
        """사용 가능한 KRW 잔액 조회"""
        for balance in account.balances:
            if balance.currency == Currency.KRW:
                return balance.balance - balance.locked
        return Decimal("0")

    def _get_target_currency_balance(self, account: Account) -> Balance | None:
        """대상 통화 잔액 조회"""
        for balance in account.balances:
            if balance.currency == self.config.target_currency:
                return balance
        return None

    async def _execute_buy_order(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> TradingResult:
        """매수 주문 실행"""
        try:
            # 매수 금액 계산
            buy_amount = await self.calculate_buy_amount(account, market_data, signal)

            if buy_amount < self.config.min_order_amount:
                return TradingResult(
                    success=False,
                    message=f"매수 금액이 최소 주문 금액({self.config.min_order_amount})보다 적습니다.",
                )

            # 시뮬레이션 모드 체크
            if self.config.mode == TradingMode.SIMULATION:
                return TradingResult(
                    success=True,
                    message=f"[시뮬레이션] 매수 주문: {buy_amount}원",
                    executed_amount=buy_amount,
                    executed_price=market_data.current_price,
                )

            # 실제 주문 실행
            order_request = OrderRequest(
                market=market_data.market,
                side=OrderSide.매수,
                ord_type=OrderType.시장가매수,
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
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> TradingResult:
        """매도 주문 실행"""
        try:
            # 매도 수량 계산
            sell_volume = await self.calculate_sell_amount(account, market_data, signal)

            if sell_volume <= Decimal("0"):
                return TradingResult(success=False, message="매도할 수량이 없습니다.")

            # 시뮬레이션 모드 체크
            if self.config.mode == TradingMode.SIMULATION:
                sell_amount = sell_volume * market_data.current_price
                return TradingResult(
                    success=True,
                    message=f"[시뮬레이션] 매도 주문: {sell_volume} {self.config.target_currency.value}",
                    executed_amount=sell_amount,
                    executed_price=market_data.current_price,
                )

            # 실제 주문 실행
            order_request = OrderRequest(
                market=market_data.market,
                side=OrderSide.매도,
                ord_type=OrderType.시장가매도,
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
