from decimal import Decimal
from typing import Any

from app.application.dto.trading_dto import TradingResult
from app.domain.models.account import Account
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.services.trading_algorithm_service import TradingAlgorithmService


class SimpleTradingAlgorithm(TradingAlgorithmService):
    """
    간단한 변동률 기반 매매 알고리즘

    매매 로직:
    - 24시간 변동률이 -5% 이하면 매수 신호
    - 24시간 변동률이 +10% 이상이면 매도 신호
    - 그 외에는 HOLD
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.buy_threshold = Decimal("-0.05")  # -5%
        self.sell_threshold = Decimal("0.10")  # +10%

    async def analyze_trading_signal(
        self, account: Account, market_data: MarketData
    ) -> TradingSignal:
        """
        변동률 기반 매매 신호 분석
        """
        change_rate = market_data.change_rate_24h

        # 매수 신호: 24시간 변동률이 -5% 이하
        if change_rate <= self.buy_threshold:
            return TradingSignal(
                action="BUY",
                confidence=min(
                    abs(change_rate) / abs(self.buy_threshold), Decimal("1.0")
                ),
                reason=f"24시간 변동률 {change_rate:.2%}로 매수 임계값({self.buy_threshold:.2%}) 이하",
            )

        # 매도 신호: 24시간 변동률이 +10% 이상이고 보유 중인 경우
        elif change_rate >= self.sell_threshold:
            target_balance = self._get_target_currency_balance(account)
            if target_balance and target_balance.balance > Decimal("0"):
                return TradingSignal(
                    action="SELL",
                    confidence=min(change_rate / self.sell_threshold, Decimal("1.0")),
                    reason=f"24시간 변동률 {change_rate:.2%}로 매도 임계값({self.sell_threshold:.2%}) 이상",
                )

        # HOLD 신호
        return TradingSignal(
            action="HOLD",
            confidence=Decimal("1.0"),
            reason=f"24시간 변동률 {change_rate:.2%}로 매매 조건 미충족",
        )

    async def calculate_buy_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매수 금액 계산: 사용 가능한 KRW 잔액의 설정된 비율만큼 매수
        """
        available_krw = self._get_available_krw_balance(account)

        # 신뢰도에 따라 투자 비율 조정
        investment_ratio = self.config.max_investment_ratio * signal.confidence
        buy_amount = available_krw * investment_ratio

        # 최소 주문 금액 확인
        if buy_amount < self.config.min_order_amount:
            return Decimal("0")

        self.logger.info(
            f"매수 금액 계산: 사용가능 KRW {available_krw}, "
            f"투자비율 {investment_ratio:.2%}, 매수금액 {buy_amount}"
        )

        return buy_amount

    async def calculate_sell_amount(
        self, account: Account, market_data: MarketData, signal: TradingSignal
    ) -> Decimal:
        """
        매도 수량 계산: 보유 중인 대상 통화의 전량 매도
        """
        target_balance = self._get_target_currency_balance(account)

        if not target_balance:
            return Decimal("0")

        # 사용 가능한 수량 (locked 제외)
        available_volume = target_balance.balance - target_balance.locked

        # 신뢰도에 따라 매도 비율 조정 (최소 50%)
        sell_ratio = max(Decimal("0.5"), signal.confidence)
        sell_volume = available_volume * sell_ratio

        self.logger.info(
            f"매도 수량 계산: 보유량 {target_balance.balance}, "
            f"사용가능 {available_volume}, 매도비율 {sell_ratio:.2%}, "
            f"매도수량 {sell_volume}"
        )

        return sell_volume

    async def pre_trading_hook(self, account: Account, market_data: MarketData) -> bool:
        """
        매매 실행 전 추가 검증
        """
        # 시장 상태 확인 (거래 가능한 상태인지)
        if hasattr(market_data, "market_state"):
            # Ticker에서 market_state를 가져올 수 있다면
            pass

        # 급격한 변동 시 거래 중단 (예: 20% 이상 변동)
        if abs(market_data.change_rate_24h) > Decimal("0.20"):
            self.logger.warning(
                f"급격한 변동 감지 ({market_data.change_rate_24h:.2%}), 거래 중단"
            )
            return False

        return True

    async def post_trading_hook(
        self, result: TradingResult, account: Account, market_data: MarketData
    ) -> None:
        """
        매매 실행 후 로깅 및 알림
        """
        if result.success:
            self.logger.info(
                f"매매 성공: {result.message}, "
                f"실행금액: {result.executed_amount}, "
                f"실행가격: {result.executed_price}"
            )
        else:
            self.logger.error(f"매매 실패: {result.message}")

        # 여기에 슬랙 알림, 이메일 발송 등 추가 가능
