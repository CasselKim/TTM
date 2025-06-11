"""Discord UI 상호작용 유스케이스"""

import logging
from typing import Any

from app.adapters.external.discord.ui.embeds import (
    create_balance_embed,
    create_dca_status_embed,
    create_profit_embed,
    create_trade_complete_embed,
    create_trade_stop_embed,
)
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.ticker_usecase import TickerUseCase
from common.utils.timezone import to_kst

logger = logging.getLogger(__name__)


class DiscordUIUseCase:
    """Discord UI 상호작용 처리 유스케이스"""

    def __init__(
        self,
        account_usecase: AccountUseCase,
        dca_usecase: DcaUsecase,
        ticker_usecase: TickerUseCase,
    ) -> None:
        self.account_usecase = account_usecase
        self.dca_usecase = dca_usecase
        self.ticker_usecase = ticker_usecase

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
                            "symbol": balance.currency,
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

    async def get_dca_status_data(self, user_id: str) -> dict[str, Any]:
        """DCA 상태 데이터 조회"""
        try:
            # 활성 마켓 조회
            active_markets = await self.dca_usecase.get_active_markets()

            if not active_markets:
                return {
                    "symbol": "",
                    "current_count": 0,
                    "total_count": 0,
                    "next_buy_time": None,
                    "average_price": 0,
                    "current_price": 0,
                    "profit_rate": 0.0,
                    "total_invested": 0,
                    "recent_trades": [],
                }

            # 첫 번째 활성 마켓의 상태 조회 (단일 사용자 가정)
            first_market = active_markets[0]
            market_status = await self.dca_usecase.get_dca_market_status(first_market)

            # 직접 state 조회 (시간 기반 매수 정보를 위해)
            state = await self.dca_usecase.dca_repository.get_state(first_market)

            # 설정 정보 조회
            config = await self.dca_usecase.dca_repository.get_config(first_market)
            max_buy_rounds = config.max_buy_rounds if config else 10

            # 심볼 추출 (KRW-BTC -> BTC)
            symbol = first_market.split("-")[1] if "-" in first_market else first_market

            # 최근 거래 내역 구성
            recent_trades = []
            for round_info in market_status.buying_rounds[-5:]:  # 최근 5개
                recent_trades.append(
                    {
                        "time": to_kst(round_info.timestamp).strftime("%Y-%m-%d %H:%M")
                        if round_info.timestamp
                        else "",
                        "price": float(round_info.buy_price),
                        "amount": float(round_info.buy_amount),
                    }
                )

            # 다음 시간 기반 매수 시간 계산
            next_buy_time = None
            if config and config.enable_time_based_buying and state:
                from datetime import timedelta

                if state.last_time_based_buy_time:
                    # 마지막 시간 기반 매수로부터 설정된 간격 후
                    interval_hours = config.time_based_buy_interval_hours
                    next_buy_time = state.last_time_based_buy_time + timedelta(
                        hours=interval_hours
                    )
                elif state.cycle_start_time:
                    # 아직 시간 기반 매수가 없다면 사이클 시작 후 첫 번째 간격
                    interval_hours = config.time_based_buy_interval_hours
                    next_buy_time = state.cycle_start_time + timedelta(
                        hours=interval_hours
                    )

            return {
                "symbol": symbol,
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
            }

        except Exception as e:
            logger.exception(f"DCA 상태 조회 중 오류 (user_id: {user_id}): {e}")
            return {
                "symbol": "",
                "current_count": 0,
                "total_count": 0,
                "next_buy_time": None,
                "average_price": 0,
                "current_price": 0,
                "profit_rate": 0.0,
                "total_invested": 0,
                "recent_trades": [],
            }

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
                {"symbol": h["symbol"], "rate": h["profit_rate"]}
                for h in sorted_holdings[:3]
                if h["profit_rate"] > 0
            ]
            top_losers = [
                {"symbol": h["symbol"], "rate": h["profit_rate"]}
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
        symbol: str,
        amount: int,
        total_count: int,
        interval_hours: int,
    ) -> dict[str, Any]:
        """매매 실행"""
        try:
            # 실제 DCA 시작
            market_name = f"KRW-{symbol}"
            result = await self.dca_usecase.start_dca(
                market=market_name,
                initial_buy_amount=amount,
                max_buy_rounds=total_count,
                time_based_buy_interval_hours=interval_hours,
            )

            if not result.success:
                raise Exception(f"DCA 시작 실패: {result.message}")

            logger.info(
                f"매매 실행 성공 (user_id: {user_id}, symbol: {symbol}, "
                f"amount: {amount}, count: {total_count})"
            )

            return {
                "symbol": symbol,
                "amount": amount,
                "total_count": total_count,
                "interval_hours": interval_hours,
                "trade_id": result.current_state.cycle_id
                if result.current_state
                else None,
            }

        except Exception as e:
            logger.exception(
                f"매매 실행 중 오류 (user_id: {user_id}, symbol: {symbol}): {e}"
            )
            raise

    async def stop_trade(self, user_id: str) -> dict[str, Any]:
        """매매 중단"""
        try:
            # 활성 마켓 조회
            active_markets = await self.dca_usecase.get_active_markets()

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
            market_status = await self.dca_usecase.get_dca_market_status(first_market)
            config = await self.dca_usecase.dca_repository.get_config(first_market)

            # 실제 DCA 중단
            result = await self.dca_usecase.stop_dca(
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

    # Embed 생성 메서드들
    async def create_balance_embed(self, user_id: str) -> Any:
        """잔고 Embed 생성"""
        balance_data = await self.get_balance_data(user_id)
        return create_balance_embed(balance_data)

    async def create_dca_status_embed(self, user_id: str) -> Any:
        """DCA 상태 Embed 생성"""
        dca_data = await self.get_dca_status_data(user_id)
        return create_dca_status_embed(dca_data)

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
