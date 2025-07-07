from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.enums import TradingAction
from app.domain.models.account import Account
from app.domain.models.dca import (
    BuyingRound,
    BuyType,
    DcaConfig,
    DcaState,
)
from app.domain.models.trading import MarketData, TradingSignal
from app.domain.enums import DcaPhase
from app.domain.constants import ALGORITHM_MAX_CONFIDENCE


class DcaService:
    """
    DCA 도메인 서비스
    도메인 엔티티들 간의 복잡한 비즈니스 로직을 담당
    """

    def analyze_signal(
        self,
        account: Account,
        market_data: MarketData,
        config: DcaConfig,
        state: DcaState,
    ) -> TradingSignal:
        """
        DCA 신호 분석

        현재 상태에 따라 매수/매도/홀드 신호를 생성합니다.
        """
        # 초기 매수 or 비활성 상태
        if state.phase == DcaPhase.INITIAL_BUY or not state.is_active:
            if account.available_krw < config.initial_buy_amount:
                return TradingSignal(
                    action=TradingAction.HOLD,
                    confidence=ALGORITHM_MAX_CONFIDENCE,
                    reason=f"초기 매수 불가: 필요금액 {config.initial_buy_amount:,.0f}원, 보유금액 {account.available_krw:,.0f}원",
                )

            return TradingSignal(
                action=TradingAction.BUY,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason="DCA 초기 매수 신호",
            )

        # 현재 수익률 계산
        current_profit_rate = state.calculate_current_profit_rate(
            market_data.current_price
        )

        # 강제 손절 확인
        if self.should_force_sell(current_profit_rate, config, state):
            return TradingSignal(
                action=TradingAction.SELL,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"강제 손절: 수익률 {current_profit_rate:.2%}",
            )

        # 익절 확인
        if self.should_take_profit(current_profit_rate, config):
            return TradingSignal(
                action=TradingAction.SELL,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"목표 수익률 달성: {current_profit_rate:.2%}",
            )

        # 추가 매수 확인
        should_buy, buy_reason = self.should_add_buy(
            account=account,
            market_data=market_data,
            config=config,
            state=state,
        )

        # 추가 매수 신호 생성
        if should_buy:
            current_price = market_data.current_price
            drop_rate = (state.average_price - current_price) / state.average_price

            return TradingSignal(
                action=TradingAction.BUY,
                confidence=ALGORITHM_MAX_CONFIDENCE,
                reason=f"{buy_reason} (평균단가: {state.average_price:,.0f}, 현재가: {current_price:,.0f}, 하락률: {drop_rate:.2%})",
            )

        # 매수/매도 신호가 없으면 홀드
        return TradingSignal(
            action=TradingAction.HOLD,
            confidence=ALGORITHM_MAX_CONFIDENCE,
            reason=f"DCA 대기 중 (평균단가: {state.average_price:,.0f}, 현재가: {market_data.current_price:,.0f}, 수익률: {current_profit_rate:.2%})",
        )

    def calculate_buy_amount(
        self,
        account: Account,
        config: DcaConfig,
        state: DcaState,
        market_data: MarketData,
    ) -> int:
        """
        DCA 매수 금액 계산
        """

        # Decimal -> int
        available_krw_int = int(account.available_krw)

        if state.current_round == 0:
            # 초기 매수
            buy_amount = min(config.initial_buy_amount, available_krw_int)
        else:
            # 추가 매수: 기존 DCA vs SmartDCA
            if not state.buying_rounds:
                # 데이터 불일치 상황: current_round > 0이지만 buying_rounds가 비어있음
                # 이 경우 초기 매수 금액을 기준으로 계산
                buy_amount = min(config.initial_buy_amount, available_krw_int)
            else:
                if config.enable_smart_dca:
                    # SmartDCA: 평균 단가 기준 가격 레벨 조정
                    reference_price = state.average_price
                    current_price = market_data.current_price
                    smart_multiplier = config.calculate_smart_dca_multiplier(
                        current_price, reference_price
                    )
                    buy_amount = int(config.initial_buy_amount * smart_multiplier)
                else:
                    # 기존 DCA: 이전 매수 금액의 배수
                    last_round = state.buying_rounds[-1]
                    buy_amount = int(last_round.buy_amount * config.add_buy_multiplier)

                buy_amount = min(buy_amount, available_krw_int)

        # 총 투자 한도 확인 (전체 KRW 잔액 대비)
        total_krw = sum(
            balance.balance for balance in account.balances if balance.currency == "KRW"
        )
        max_total_investment = total_krw * config.max_investment_ratio

        total_investment_decimal = Decimal(str(state.total_investment))
        if total_investment_decimal + Decimal(buy_amount) > max_total_investment:
            buy_amount = int(max_total_investment - total_investment_decimal)

        return buy_amount

    def calculate_sell_amount(
        self,
        account: Account,
        market_data: MarketData,
        state: DcaState,
    ) -> Decimal:
        """
        DCA 매도 수량 계산 (전량 매도)
        """

        currency = market_data.market.split("-")[1]
        target_balance = account.get_balance(currency)
        if not target_balance:
            return Decimal("0")

        # 사용 가능한 전량 매도
        return target_balance.balance - target_balance.locked

    def execute_buy(
        self,
        market_data: MarketData,
        buy_amount: int,
        config: DcaConfig,
        state: DcaState,
        buy_type: BuyType | None = None,
        reason: str | None = None,
    ) -> BuyingRound:
        """
        매수 실행 - 새로운 매수 회차 생성
        """
        current_price = market_data.current_price
        buy_volume = Decimal(str(buy_amount)) / current_price

        new_round = BuyingRound(
            round_number=state.current_round + 1,
            buy_price=current_price,
            buy_amount=buy_amount,
            buy_volume=buy_volume,
            timestamp=datetime.now(),
            buy_type=buy_type if buy_type is not None else BuyType.PRICE_DROP,
            reason=reason,
        )

        # 상태 업데이트
        if not state.is_active:
            state.start_new_cycle(market_data.market)

        state.add_buying_round(new_round, config)
        state.phase = DcaPhase.ACCUMULATING

        return new_round

    def execute_sell(
        self,
        market_data: MarketData,
        sell_volume: Decimal,
        state: DcaState,
    ) -> Decimal:
        """
        매도 실행 - 수익 계산 후 사이클 완료
        """
        current_price = market_data.current_price
        sell_amount = sell_volume * current_price
        profit_amount = sell_amount - Decimal(str(state.total_investment))

        # 사이클 완료
        state.complete_cycle()

        return profit_amount

    def should_force_sell(
        self, current_profit_rate: Decimal, config: DcaConfig, state: DcaState
    ) -> bool:
        """
        강제 손절 조건 확인
        """
        # 최대 회차 도달 시 강제 손절
        if state.current_round >= config.max_buy_rounds:
            return True

        # 최대 손실률 초과
        if current_profit_rate <= config.force_stop_loss_rate:
            return True

        return False

    def should_take_profit(
        self, current_profit_rate: Decimal, config: DcaConfig
    ) -> bool:
        """익절 조건 확인"""
        return current_profit_rate >= config.target_profit_rate

    def should_add_buy(
        self,
        account: Account,
        market_data: MarketData,
        config: DcaConfig,
        state: DcaState,
    ) -> tuple[bool, str]:
        """
        추가 매수 조건 확인

        Returns:
            tuple[bool, str]: (추가 매수 여부, 사유)
        """
        current_price = market_data.current_price

        # 사용 가능한 KRW 확인
        available_krw = account.available_krw
        if available_krw < config.initial_buy_amount:
            return False, "사용 가능한 KRW 부족"

        # 시간 기반 매수 조건
        if self.should_time_based_buy(config, state):
            return True, "시간 기반 추가 매수"

        # 가격 하락 기반 매수 조건
        if self.should_price_drop_buy(market_data, config, state):
            drop_rate = (state.average_price - current_price) / state.average_price
            return True, f"가격 하락 기반 추가 매수 (하락률: {drop_rate:.2%})"

        return False, "추가 매수 조건 미충족"

    def should_time_based_buy(self, config: DcaConfig, state: DcaState) -> bool:
        """
        시간 기반 추가 매수 조건 확인
        """
        if not config.enable_time_based_buying:
            return False

        if not state.buying_rounds:
            return False

        last_buy_time = state.buying_rounds[-1].timestamp
        time_diff = datetime.now() - last_buy_time

        interval_hours: int = config.time_based_buy_interval_hours
        return time_diff >= timedelta(hours=interval_hours)

    def should_price_drop_buy(
        self, market_data: MarketData, config: DcaConfig, state: DcaState
    ) -> bool:
        """
        가격 하락 기반 추가 매수 조건 확인
        """
        current_price = market_data.current_price

        # 최소 매수 간격 확인
        if state.buying_rounds:
            last_buy_time = state.buying_rounds[-1].timestamp
            time_diff = datetime.now() - last_buy_time
            if time_diff < timedelta(minutes=config.min_buy_interval_minutes):
                return False

        # 평균 단가 대비 하락률 계산
        drop_rate = (state.average_price - current_price) / state.average_price

        return drop_rate >= abs(config.price_drop_threshold)

    def can_buy_more(
        self, config: DcaConfig, state: DcaState, current_time: datetime
    ) -> tuple[bool, str]:
        """
        추가 매수 가능 여부 확인
        """
        if state.current_round >= config.max_buy_rounds:
            return False, f"최대 매수 회차({config.max_buy_rounds})에 도달했습니다."

        # 최근 매수 간격 확인
        if state.last_buy_time:
            time_diff = (current_time - state.last_buy_time).total_seconds() / 60
            if time_diff < config.min_buy_interval_minutes:
                remaining_minutes = config.min_buy_interval_minutes - int(time_diff)
                return False, f"최소 매수 간격까지 {remaining_minutes}분 남았습니다."

        return True, "추가 매수 가능합니다."
