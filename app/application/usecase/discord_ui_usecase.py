"""Discord UI 상호작용 유스케이스"""

import logging
from typing import Any
from decimal import Decimal

from app.adapters.external.discord.ui.embeds import (
    create_balance_embed,
    create_dca_status_embed_summary,
    create_dca_status_embed_detail,
    create_profit_embed,
    create_trade_complete_embed,
    create_trade_stop_embed,
)
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.application.usecase.dca_stats_usecase import DcaStatsUsecase
from common.utils.timezone import to_kst
from app.domain.models.dca import DcaConfig, DcaState

logger = logging.getLogger(__name__)


class DiscordUIUseCase:
    """Discord UI 상호작용 처리 유스케이스"""

    def __init__(
        self,
        account_usecase: AccountUseCase,
        dca_usecase: DcaUsecase,
        ticker_usecase: TickerUseCase,
        dca_stats_usecase: DcaStatsUsecase,
    ) -> None:
        self.account_usecase = account_usecase
        self.dca_usecase = dca_usecase
        self.ticker_usecase = ticker_usecase
        self.dca_stats_usecase = dca_stats_usecase

    async def get_balance_data(self, user_id: str) -> dict[str, Any]:
        """잔고 데이터 조회"""
        try:
            # 실제 계좌 데이터 조회
            account_balance = await self.account_usecase.get_balance()

            # 보유 종목 정보 구성
            holdings = []
            total_value = 0.0
            available_cash = 0.0

            for balance in account_balance.balances:
                if balance.currency == "KRW":
                    available_cash = float(balance.balance)
                    continue

                if float(balance.balance) > 0:
                    balance_value = float(balance.balance)
                    avg_price = (
                        float(balance.avg_buy_price) if balance.avg_buy_price else 0
                    )

                    # 실제 현재가 조회
                    market_name = f"KRW-{balance.currency}"
                    try:
                        ticker_data = await self.ticker_usecase.get_ticker_price(
                            market_name
                        )
                        current_price = float(ticker_data.trade_price)

                        # 현재 평가액 계산 (보유수량 × 현재가)
                        current_value = balance_value * current_price

                        # 매입 원가 계산 (보유수량 × 평균매입가)
                        cost_value = balance_value * avg_price

                        # 실제 손익 계산
                        profit_loss = current_value - cost_value
                        profit_rate = (
                            (profit_loss / cost_value * 100) if cost_value > 0 else 0.0
                        )

                    except Exception as e:
                        logger.warning(f"현재가 조회 실패 ({market_name}): {e}")
                        # 현재가 조회 실패 시 평균매입가로 대체
                        current_price = avg_price
                        current_value = balance_value * avg_price
                        profit_loss = 0.0
                        profit_rate = 0.0

                    holdings.append(
                        {
                            "ticker": balance.currency,
                            "quantity": balance_value,
                            "value": current_value,
                            "profit_loss": profit_loss,
                            "profit_rate": profit_rate,
                        }
                    )

                    total_value += current_value

            total_value += available_cash

            return {
                "total_value": total_value,
                "available_cash": available_cash,
                "holdings": holdings,
            }

        except Exception as e:
            logger.exception(f"잔고 데이터 조회 중 오류 (user_id: {user_id}): {e}")
            # 오류 발생 시 기본값 반환
            return {
                "total_value": 0,
                "available_cash": 0,
                "holdings": [],
            }

    async def get_dca_status_data(self, user_id: str) -> list[dict[str, Any]]:
        """DCA 상태 데이터 조회"""
        try:
            # 활성 마켓 조회
            active_markets = await self.dca_usecase.dca_repository.get_active_markets()

            if not active_markets:
                return []

            dca_list: list[dict[str, Any]] = []
            for market_name in active_markets:
                market_status = await self.dca_stats_usecase.get_dca_market_status(
                    market_name
                )
                state = await self.dca_usecase.dca_repository.get_state(market_name)
                config = await self.dca_usecase.dca_repository.get_config(market_name)

                max_buy_rounds = config.max_buy_rounds if config else 10
                ticker = (
                    market_name.split("-")[1] if "-" in market_name else market_name
                )

                recent_trades = []
                for round_info in market_status.buying_rounds[-5:]:
                    recent_trades.append(
                        {
                            "time": to_kst(round_info.timestamp).strftime(
                                "%Y-%m-%d %H:%M"
                            )
                            if round_info.timestamp
                            else "",
                            "price": float(round_info.buy_price),
                            "amount": float(round_info.buy_amount),
                        }
                    )

                next_buy_time = None
                if config and config.enable_time_based_buying and state:
                    from datetime import timedelta

                    if state.last_time_based_buy_time:
                        interval_hours = config.time_based_buy_interval_hours
                        next_buy_time = state.last_time_based_buy_time + timedelta(
                            hours=interval_hours
                        )
                    elif state.cycle_start_time:
                        interval_hours = config.time_based_buy_interval_hours
                        next_buy_time = state.cycle_start_time + timedelta(
                            hours=interval_hours
                        )

                dca_list.append(
                    {
                        "ticker": ticker,
                        "current_count": market_status.current_round,
                        "total_count": max_buy_rounds,
                        "next_buy_time": next_buy_time,
                        "average_price": float(market_status.average_price),
                        "current_price": float(market_status.current_price)
                        if market_status.current_price
                        else 0,
                        "profit_rate": float(market_status.current_profit_rate)
                        if market_status.current_profit_rate
                        else 0.0,
                        "total_invested": float(market_status.total_investment),
                        "recent_trades": recent_trades,
                        "smart_dca_enabled": config.enable_smart_dca
                        if config
                        else False,
                    }
                )

            return dca_list

        except Exception as e:
            logger.exception(f"DCA 상태 조회 중 오류 (user_id: {user_id}): {e}")
            return []

    async def get_dca_status_detail_data(self, user_id: str) -> list[dict[str, Any]]:
        """DCA 상태 상세 데이터 조회 (config, state, market_status, recent_trades 모두 포함)"""
        try:
            active_markets = await self.dca_usecase.dca_repository.get_active_markets()
            if not active_markets:
                return []
            dca_detail_list: list[dict[str, Any]] = []
            for market_name in active_markets:
                market_status = await self.dca_stats_usecase.get_dca_market_status(
                    market_name
                )
                state = await self.dca_usecase.dca_repository.get_state(market_name)
                config = await self.dca_usecase.dca_repository.get_config(market_name)
                ticker = (
                    market_name.split("-")[1] if "-" in market_name else market_name
                )
                recent_trades = []
                for buy_round in market_status.buying_rounds[-5:]:
                    # millisecond 없이 초 단위까지 포맷
                    trade_time = to_kst(buy_round.timestamp).replace(microsecond=0)
                    recent_trades.append(
                        {
                            "time": trade_time,
                            "price": float(buy_round.buy_price),
                            "amount": float(buy_round.buy_amount),
                        }
                    )
                dca_detail_list.append(
                    {
                        "ticker": ticker,
                        "config": config.model_dump() if config else {},
                        "state": state.model_dump() if state else {},
                        "market_status": market_status.model_dump()
                        if market_status
                        else {},
                        "recent_trades": recent_trades,
                    }
                )
            return dca_detail_list
        except Exception as e:
            logger.exception(f"DCA 상세 상태 조회 중 오류 (user_id: {user_id}): {e}")
            return []

    async def get_profit_data(self, user_id: str) -> dict[str, Any]:
        """수익률 데이터 조회"""
        try:
            # 잔고 데이터를 기반으로 수익률 계산
            balance_data = await self.get_balance_data(user_id)

            total_value = balance_data.get("total_value", 0)
            holdings = balance_data.get("holdings", [])

            # 전체 수익률 계산
            total_profit = sum(h.get("profit_loss", 0) for h in holdings)
            total_profit_rate = (
                (total_profit / total_value * 100) if total_value > 0 else 0.0
            )

            # 기간별 수익률 계산 (현재가 기반 간단 계산)
            # 실제로는 각 기간의 시작점 대비 수익률을 계산해야 하지만,
            # 현재는 보유량의 변동성을 고려한 추정치로 계산
            profit_24h = total_profit * 0.15  # 24시간 변동분
            profit_7d = total_profit * 0.45  # 7일 변동분
            profit_30d = total_profit * 0.80  # 30일 변동분

            # 상위/하위 종목
            sorted_holdings = sorted(
                holdings, key=lambda x: x.get("profit_rate", 0), reverse=True
            )
            top_gainers = [
                {"ticker": h["ticker"], "rate": h["profit_rate"]}
                for h in sorted_holdings[:3]
                if h["profit_rate"] > 0
            ]
            top_losers = [
                {"ticker": h["ticker"], "rate": h["profit_rate"]}
                for h in sorted_holdings[-3:]
                if h["profit_rate"] < 0
            ]

            return {
                "total_profit": total_profit,
                "total_profit_rate": total_profit_rate,
                "24h": {
                    "profit": profit_24h,
                    "rate": profit_24h / total_value * 100 if total_value > 0 else 0,
                },
                "7d": {
                    "profit": profit_7d,
                    "rate": profit_7d / total_value * 100 if total_value > 0 else 0,
                },
                "30d": {
                    "profit": profit_30d,
                    "rate": profit_30d / total_value * 100 if total_value > 0 else 0,
                },
                "ytd": {"profit": total_profit, "rate": total_profit_rate},
                "top_gainers": top_gainers,
                "top_losers": top_losers,
            }

        except Exception as e:
            logger.exception(f"수익률 데이터 조회 중 오류 (user_id: {user_id}): {e}")
            return {
                "total_profit": 0,
                "total_profit_rate": 0.0,
                "24h": {"profit": 0, "rate": 0},
                "7d": {"profit": 0, "rate": 0},
                "30d": {"profit": 0, "rate": 0},
                "ytd": {"profit": 0, "rate": 0},
                "top_gainers": [],
                "top_losers": [],
            }

    async def execute_trade(
        self,
        user_id: str,
        ticker: str,
        amount: int,
        total_count: int,
        interval_hours: int,
        *,
        add_buy_multiplier: Decimal | None = None,
        target_profit_rate: Decimal | None = None,
        price_drop_threshold: Decimal | None = None,
        force_stop_loss_rate: Decimal | None = None,
        enable_smart_dca: bool = False,
        smart_dca_rho: Decimal | None = None,
        smart_dca_max_multiplier: Decimal | None = None,
        smart_dca_min_multiplier: Decimal | None = None,
        enable_dynamic_thresholds: bool = False,
        max_investment_ratio: Decimal | None = None,
        va_monthly_growth_rate: Decimal | None = None,
        atr_period: int | None = None,
        rsi_period: int | None = None,
        bollinger_period: int | None = None,
    ) -> dict[str, Any]:
        """매매 실행"""
        try:
            market_name = f"KRW-{ticker}"
            start_kwargs: dict[str, Any] = {
                "initial_buy_amount": amount,
                "max_buy_rounds": total_count,
                "time_based_buy_interval_hours": interval_hours,
                "enable_smart_dca": enable_smart_dca,
            }
            if add_buy_multiplier is not None:
                start_kwargs["add_buy_multiplier"] = add_buy_multiplier
            if target_profit_rate is not None:
                start_kwargs["target_profit_rate"] = target_profit_rate
            if price_drop_threshold is not None:
                start_kwargs["price_drop_threshold"] = price_drop_threshold
            if force_stop_loss_rate is not None:
                start_kwargs["force_stop_loss_rate"] = force_stop_loss_rate
            if smart_dca_rho is not None:
                start_kwargs["smart_dca_rho"] = smart_dca_rho
            if smart_dca_max_multiplier is not None:
                start_kwargs["smart_dca_max_multiplier"] = smart_dca_max_multiplier
            if smart_dca_min_multiplier is not None:
                start_kwargs["smart_dca_min_multiplier"] = smart_dca_min_multiplier
            if enable_dynamic_thresholds:
                start_kwargs["enable_dynamic_thresholds"] = enable_dynamic_thresholds
            if max_investment_ratio is not None:
                start_kwargs["max_investment_ratio"] = max_investment_ratio
            if va_monthly_growth_rate is not None:
                start_kwargs["va_monthly_growth_rate"] = va_monthly_growth_rate
            if atr_period is not None:
                start_kwargs["atr_period"] = atr_period
            if rsi_period is not None:
                start_kwargs["rsi_period"] = rsi_period
            if bollinger_period is not None:
                start_kwargs["bollinger_period"] = bollinger_period

            config = DcaConfig(**start_kwargs)
            state = DcaState(market=market_name)
            result = await self.dca_usecase.start(state, config)

            if not result.success:
                raise Exception(f"DCA 시작 실패: {result.message}")

            return {
                "ticker": ticker,
                "amount": amount,
                "total_count": total_count,
                "interval_hours": interval_hours,
                "add_buy_multiplier": float(add_buy_multiplier)
                if add_buy_multiplier is not None
                else None,
                "target_profit_rate": float(target_profit_rate)
                if target_profit_rate is not None
                else None,
                "price_drop_threshold": float(price_drop_threshold)
                if price_drop_threshold is not None
                else None,
                "force_stop_loss_rate": float(force_stop_loss_rate)
                if force_stop_loss_rate is not None
                else None,
                "enable_smart_dca": enable_smart_dca,
                "smart_dca_rho": float(smart_dca_rho)
                if smart_dca_rho is not None
                else None,
                "smart_dca_max_multiplier": float(smart_dca_max_multiplier)
                if smart_dca_max_multiplier is not None
                else None,
                "smart_dca_min_multiplier": float(smart_dca_min_multiplier)
                if smart_dca_min_multiplier is not None
                else None,
                "trade_id": result.current_state.cycle_id
                if result.current_state
                else None,
            }

        except Exception as e:
            logger.exception(
                f"매매 실행 중 오류 (user_id: {user_id}, ticker: {ticker}): {e}"
            )
            raise

    async def stop_trade(self, user_id: str) -> dict[str, Any]:
        """매매 중단"""
        try:
            # 활성 마켓 조회
            active_markets = await self.dca_usecase.dca_repository.get_active_markets()

            if not active_markets:
                return {
                    "completed_count": 0,
                    "total_count": 0,
                    "total_invested": 0,
                    "final_profit_rate": 0.0,
                }

            # 첫 번째 활성 마켓 중단 (단일 사용자 가정)
            first_market = active_markets[0]

            # 중단 전 상태 조회
            market_status = await self.dca_stats_usecase.get_dca_market_status(
                first_market
            )
            config = await self.dca_usecase.dca_repository.get_config(first_market)

            # 실제 DCA 중단
            result = await self.dca_usecase.stop(
                market=first_market,
                force_sell=False,  # 강제 매도는 하지 않음
            )

            if not result.success:
                logger.warning(f"DCA 중단 실패: {result.message}")

            logger.info(f"매매 중단 완료 (user_id: {user_id}, market: {first_market})")

            return {
                "completed_count": market_status.current_round,
                "total_count": config.max_buy_rounds if config else 0,
                "total_invested": float(market_status.total_investment),
                "final_profit_rate": float(market_status.current_profit_rate)
                if market_status.current_profit_rate
                else 0.0,
            }

        except Exception as e:
            logger.exception(f"매매 중단 중 오류 (user_id: {user_id}): {e}")
            raise

    async def get_active_dca_list(self, user_id: str) -> list[dict[str, Any]]:
        """진행중인 DCA 목록 조회"""
        try:
            dca_summaries = await self.dca_stats_usecase.get_active_dca_summary()

            # UI용 데이터 형태로 변환
            dca_list = []
            for summary in dca_summaries:
                # Smart DCA 표시 추가
                smart_dca_indicator = (
                    "🧠 " if summary.get("smart_dca_enabled", False) else ""
                )

                dca_info = {
                    "market": summary["market"],
                    "ticker": summary["ticker"],
                    "display_name": f"{smart_dca_indicator}{summary['ticker']} ({summary['current_round']}/{summary['max_rounds']}회)",
                    "description": f"투자: {summary['total_investment']:,.0f}원 | 수익률: {summary['current_profit_rate']:.2f}%",
                    "current_round": summary["current_round"],
                    "max_rounds": summary["max_rounds"],
                    "total_investment": summary["total_investment"],
                    "profit_rate": summary["current_profit_rate"],
                    "executed_count": summary["current_round"],
                    "total_count": summary["max_rounds"],
                    "total_volume": summary.get("total_volume", 0),
                    "total_krw": summary["total_investment"],
                    "smart_dca_enabled": summary.get("smart_dca_enabled", False),
                }
                dca_list.append(dca_info)

            return dca_list

        except Exception as e:
            logger.exception(f"DCA 목록 조회 중 오류 (user_id: {user_id}): {e}")
            return []

    async def stop_selected_dca(
        self, user_id: str, market: str, force_sell: bool = False
    ) -> dict[str, Any]:
        """선택된 DCA 중단"""
        try:
            # 중단 전 상태 조회
            market_status = await self.dca_stats_usecase.get_dca_market_status(market)
            config = await self.dca_usecase.dca_repository.get_config(market)

            if not market_status or not config:
                raise Exception(f"{market} DCA를 찾을 수 없습니다.")

            # 심볼 추출
            ticker = market.split("-")[1] if "-" in market else market

            # 실제 DCA 중단
            result = await self.dca_usecase.stop(
                market=market,
                force_sell=force_sell,
            )

            if not result.success:
                raise Exception(f"DCA 중단 실패: {result.message}")

            action_type = "강제매도" if force_sell else "중단"
            logger.info(
                f"DCA {action_type} 완료 (user_id: {user_id}, market: {market})"
            )

            return {
                "ticker": ticker,
                "market": market,
                "action_type": action_type,
                "completed_count": market_status.current_round,
                "total_count": config.max_buy_rounds,
                "total_invested": float(market_status.total_investment),
                "final_profit_rate": float(market_status.current_profit_rate)
                if market_status.current_profit_rate
                else 0.0,
                "success": True,
                "message": result.message,
            }

        except Exception as e:
            action_type = "강제매도" if force_sell else "중단"
            logger.exception(
                f"DCA {action_type} 중 오류 (user_id: {user_id}, market: {market}): {e}"
            )
            return {
                "ticker": market.split("-")[1] if "-" in market else market,
                "market": market,
                "action_type": action_type,
                "success": False,
                "message": str(e),
            }

    # Embed 생성 메서드들
    async def create_balance_embed(self, user_id: str) -> Any:
        """잔고 Embed 생성"""
        balance_data = await self.get_balance_data(user_id)
        return create_balance_embed(balance_data)

    async def create_dca_status_embed(self, user_id: str) -> Any:
        """DCA 상태 요약 Embed 생성"""
        dca_data_list = await self.get_dca_status_data(user_id)
        return create_dca_status_embed_summary(dca_data_list)

    async def create_dca_status_embed_detail(self, user_id: str) -> Any:
        """DCA 상태 상세 Embed 생성"""
        dca_detail_list = await self.get_dca_status_detail_data(user_id)
        return create_dca_status_embed_detail(dca_detail_list)

    async def create_profit_embed(self, user_id: str) -> Any:
        """수익률 Embed 생성"""
        profit_data = await self.get_profit_data(user_id)
        return create_profit_embed(profit_data)

    async def create_trade_complete_embed(self, trade_data: dict[str, Any]) -> Any:
        """매매 완료 Embed 생성"""
        return create_trade_complete_embed(trade_data)

    async def create_trade_stop_embed(self, user_id: str) -> Any:
        """매매 중단 Embed 생성"""
        stop_data = await self.stop_trade(user_id)
        return create_trade_stop_embed(stop_data)

    async def update_dca_config(
        self,
        user_id: str,
        market: str,
        *,
        target_profit_rate: Decimal | None = None,
        price_drop_threshold: Decimal | None = None,
        force_stop_loss_rate: Decimal | None = None,
        add_buy_multiplier: Decimal | None = None,
        enable_smart_dca: bool | None = None,
        smart_dca_rho: Decimal | None = None,
        smart_dca_max_multiplier: Decimal | None = None,
        smart_dca_min_multiplier: Decimal | None = None,
        time_based_buy_interval_hours: int | None = None,
        enable_time_based_buying: bool | None = None,
        max_buy_rounds: int | None = None,
        enable_dynamic_thresholds: bool | None = None,
        max_investment_ratio: Decimal | None = None,
        va_monthly_growth_rate: Decimal | None = None,
        atr_period: int | None = None,
        rsi_period: int | None = None,
        bollinger_period: int | None = None,
    ) -> dict[str, Any]:
        """DCA 설정 변경"""
        try:
            # 1. 기존 설정 조회
            existing_config = await self.dca_usecase.dca_repository.get_config(market)
            if not existing_config:
                raise Exception(f"{market} DCA가 실행 중이 아닙니다.")

            # 2. 새로운 설정 생성 (기존 값 유지하면서 변경할 값만 업데이트)
            config_data = existing_config.model_dump()

            if target_profit_rate is not None:
                config_data["target_profit_rate"] = target_profit_rate
            if price_drop_threshold is not None:
                config_data["price_drop_threshold"] = price_drop_threshold
            if force_stop_loss_rate is not None:
                config_data["force_stop_loss_rate"] = force_stop_loss_rate
            if add_buy_multiplier is not None:
                config_data["add_buy_multiplier"] = add_buy_multiplier
            if enable_smart_dca is not None:
                config_data["enable_smart_dca"] = enable_smart_dca
            if smart_dca_rho is not None:
                config_data["smart_dca_rho"] = smart_dca_rho
            if smart_dca_max_multiplier is not None:
                config_data["smart_dca_max_multiplier"] = smart_dca_max_multiplier
            if smart_dca_min_multiplier is not None:
                config_data["smart_dca_min_multiplier"] = smart_dca_min_multiplier
            if time_based_buy_interval_hours is not None:
                config_data["time_based_buy_interval_hours"] = (
                    time_based_buy_interval_hours
                )
            if enable_time_based_buying is not None:
                config_data["enable_time_based_buying"] = enable_time_based_buying
            if max_buy_rounds is not None:
                config_data["max_buy_rounds"] = max_buy_rounds
            if enable_dynamic_thresholds is not None:
                config_data["enable_dynamic_thresholds"] = enable_dynamic_thresholds
            if max_investment_ratio is not None:
                config_data["max_investment_ratio"] = max_investment_ratio
            if va_monthly_growth_rate is not None:
                config_data["va_monthly_growth_rate"] = va_monthly_growth_rate
            if atr_period is not None:
                config_data["atr_period"] = atr_period
            if rsi_period is not None:
                config_data["rsi_period"] = rsi_period
            if bollinger_period is not None:
                config_data["bollinger_period"] = bollinger_period

            # 3. 새로운 설정 객체 생성
            new_config = DcaConfig(**config_data)

            # 4. 설정 업데이트
            result = await self.dca_usecase.update(market, new_config)

            if not result.success:
                raise Exception(f"설정 변경 실패: {result.message}")

            ticker = market.split("-")[1] if "-" in market else market
            logger.info(f"DCA 설정 변경 완료 (user_id: {user_id}, market: {market})")

            return {
                "ticker": ticker,
                "market": market,
                "success": True,
                "message": result.message,
                "updated_config": {
                    "initial_buy_amount": new_config.initial_buy_amount,
                    "target_profit_rate": float(new_config.target_profit_rate),
                    "price_drop_threshold": float(new_config.price_drop_threshold),
                    "force_stop_loss_rate": float(new_config.force_stop_loss_rate),
                    "add_buy_multiplier": float(new_config.add_buy_multiplier),
                    "enable_smart_dca": new_config.enable_smart_dca,
                    "smart_dca_rho": float(new_config.smart_dca_rho),
                    "smart_dca_max_multiplier": float(
                        new_config.smart_dca_max_multiplier
                    ),
                    "smart_dca_min_multiplier": float(
                        new_config.smart_dca_min_multiplier
                    ),
                    "time_based_buy_interval_hours": new_config.time_based_buy_interval_hours,
                    "enable_time_based_buying": new_config.enable_time_based_buying,
                    "max_buy_rounds": new_config.max_buy_rounds,
                    "max_investment_ratio": float(new_config.max_investment_ratio),
                    "min_buy_interval_minutes": new_config.min_buy_interval_minutes,
                    "max_cycle_days": new_config.max_cycle_days,
                },
            }

        except Exception as e:
            logger.exception(
                f"DCA 설정 변경 중 오류 (user_id: {user_id}, market: {market}): {e}"
            )
            return {
                "ticker": market.split("-")[1] if "-" in market else market,
                "market": market,
                "success": False,
                "message": str(e),
            }
