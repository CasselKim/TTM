"""Discord UI 상호작용 유스케이스"""

import logging
from datetime import datetime
from typing import Any

from app.adapters.external.discord.ui.embeds import (
    create_balance_embed,
    create_dca_status_embed,
    create_profit_embed,
    create_trade_complete_embed,
    create_trade_stop_embed,
)
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase

logger = logging.getLogger(__name__)


class DiscordUIUseCase:
    """Discord UI 상호작용 처리 유스케이스"""

    def __init__(
        self,
        account_usecase: AccountUseCase,
        infinite_buying_usecase: InfiniteBuyingUsecase,
    ) -> None:
        self.account_usecase = account_usecase
        self.infinite_buying_usecase = infinite_buying_usecase

    async def get_balance_data(self, user_id: str) -> dict[str, Any]:
        """잔고 데이터 조회"""
        try:
            # TODO: 실제 계좌 유스케이스와 연동
            # account_data = await self.account_usecase.get_account_summary(user_id)

            # Mock 데이터 (실제 구현 시 제거)
            return {
                "total_value": 1500000,
                "available_cash": 250000,
                "holdings": [
                    {
                        "symbol": "BTC",
                        "quantity": 0.02150000,
                        "value": 850000,
                        "profit_loss": 50000,
                        "profit_rate": 6.25,
                    },
                    {
                        "symbol": "ETH",
                        "quantity": 0.85000000,
                        "value": 400000,
                        "profit_loss": -20000,
                        "profit_rate": -4.76,
                    },
                ],
            }

        except Exception as e:
            logger.exception(f"잔고 데이터 조회 중 오류 (user_id: {user_id}): {e}")
            raise

    async def get_dca_status_data(self, user_id: str) -> dict[str, Any]:
        """DCA 상태 데이터 조회"""
        try:
            # TODO: 실제 DCA 유스케이스와 연동
            # dca_data = await self.infinite_buying_usecase.get_status(user_id)

            # Mock 데이터 (실제 구현 시 제거)
            return {
                "symbol": "BTC",
                "current_count": 7,
                "total_count": 10,
                "next_buy_time": datetime(2024, 1, 15, 14, 30),
                "average_price": 42500000,
                "current_price": 44800000,
                "profit_rate": 5.41,
                "total_invested": 700000,
                "recent_trades": [
                    {"time": "2024-01-14 14:30", "price": 44200000, "amount": 100000},
                    {"time": "2024-01-13 14:30", "price": 43800000, "amount": 100000},
                ],
            }

        except Exception as e:
            logger.exception(f"DCA 상태 조회 중 오류 (user_id: {user_id}): {e}")
            raise

    async def get_profit_data(self, user_id: str) -> dict[str, Any]:
        """수익률 데이터 조회"""
        try:
            # TODO: 실제 수익률 계산 로직 구현

            # Mock 데이터 (실제 구현 시 제거)
            return {
                "total_profit": 125000,
                "total_profit_rate": 8.33,
                "24h": {"profit": 15000, "rate": 1.02},
                "7d": {"profit": 45000, "rate": 3.15},
                "30d": {"profit": 98000, "rate": 6.89},
                "ytd": {"profit": 125000, "rate": 8.33},
                "top_gainers": [
                    {"symbol": "BTC", "rate": 6.25},
                    {"symbol": "DOGE", "rate": 12.50},
                    {"symbol": "ADA", "rate": 8.75},
                ],
                "top_losers": [
                    {"symbol": "ETH", "rate": -4.76},
                    {"symbol": "XRP", "rate": -2.30},
                    {"symbol": "DOT", "rate": -1.85},
                ],
            }

        except Exception as e:
            logger.exception(f"수익률 데이터 조회 중 오류 (user_id: {user_id}): {e}")
            raise

    async def execute_trade(
        self,
        user_id: str,
        symbol: str,
        amount: float,
        total_count: int,
        interval_hours: int,
    ) -> dict[str, Any]:
        """매매 실행"""
        try:
            # TODO: 실제 DCA 유스케이스와 연동
            # result = await self.infinite_buying_usecase.start_dca(
            #     user_id=user_id,
            #     symbol=symbol,
            #     amount=amount,
            #     total_count=total_count,
            #     interval_hours=interval_hours
            # )

            logger.info(
                f"매매 실행 (user_id: {user_id}, symbol: {symbol}, "
                f"amount: {amount}, count: {total_count}, interval: {interval_hours})"
            )

            # Mock 응답 (실제 구현 시 제거)
            return {
                "symbol": symbol,
                "amount": amount,
                "total_count": total_count,
                "interval_hours": interval_hours,
                "trade_id": f"trade_{user_id}_{int(datetime.now().timestamp())}",
            }

        except Exception as e:
            logger.exception(
                f"매매 실행 중 오류 (user_id: {user_id}, symbol: {symbol}): {e}"
            )
            raise

    async def stop_trade(self, user_id: str) -> dict[str, Any]:
        """매매 중단"""
        try:
            # TODO: 실제 DCA 유스케이스와 연동
            # result = await self.infinite_buying_usecase.stop_dca(user_id)

            logger.info(f"매매 중단 (user_id: {user_id})")

            # Mock 응답 (실제 구현 시 제거)
            return {
                "completed_count": 7,
                "total_count": 10,
                "total_invested": 700000,
                "final_profit_rate": 5.41,
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
