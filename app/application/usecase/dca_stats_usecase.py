import logging
from decimal import Decimal
from typing import Any

from app.domain.enums import DcaStatus
from app.domain.models.status import (
    BuyingRoundInfo,
    DcaMarketStatus,
    MarketName,
)
from app.domain.repositories.dca_repository import DcaRepository
from app.domain.repositories.ticker_repository import TickerRepository

logger = logging.getLogger(__name__)


class DcaStatsUsecase:
    def __init__(
        self,
        dca_repository: DcaRepository,
        ticker_repository: TickerRepository,
    ) -> None:
        self.dca_repository = dca_repository
        self.ticker_repository = ticker_repository

    async def get_active_dca_summary(self) -> list[dict[str, Any]]:
        active_markets = await self.dca_repository.get_active_markets()
        dca_summaries: list[dict[str, Any]] = []

        for market in active_markets:
            market_status = await self.get_dca_market_status(market=market)
            config = await self.dca_repository.get_config(market=market)

            if not market_status or not config:
                continue

            symbol = market.split("-")[1] if "-" in market else market

            dca_summaries.append(
                {
                    "market": market,
                    "symbol": symbol,
                    "current_round": market_status.current_round,
                    "max_rounds": config.max_buy_rounds,
                    "total_investment": float(market_status.total_investment),
                    "total_volume": (
                        float(market_status.total_volume)
                        if isinstance(
                            getattr(market_status, "total_volume", None),
                            (int, float, Decimal),
                        )
                        else 0.0
                    ),
                    "average_price": float(market_status.average_price),
                    "current_profit_rate": float(market_status.current_profit_rate)
                    if market_status.current_profit_rate
                    else 0.0,
                    "cycle_id": market_status.cycle_id
                    if hasattr(market_status, "cycle_id")
                    else "unknown",
                }
            )

        return dca_summaries

    async def get_dca_market_status(self, market: MarketName) -> DcaMarketStatus:
        config = await self.dca_repository.get_config(market)
        state = await self.dca_repository.get_state(market)

        if not config or not state:
            raise ValueError(f"마켓 {market}의 DCA 설정 또는 상태를 찾을 수 없습니다.")

        ticker = await self.ticker_repository.get_ticker(market)
        current_price = ticker.trade_price

        buying_rounds = []
        for buy_round in state.buying_rounds:
            buying_rounds.append(
                BuyingRoundInfo(
                    round_number=buy_round.round_number,
                    buy_price=buy_round.buy_price,
                    buy_amount=Decimal(buy_round.buy_amount),
                    buy_volume=buy_round.buy_volume,
                    timestamp=buy_round.timestamp,
                    reason=buy_round.reason,
                )
            )

        current_profit_rate = None
        current_value = None
        profit_loss_amount = None

        if current_price and state.total_volume > 0:
            current_value = state.total_volume * current_price
            total_inv_dec = Decimal(state.total_investment)
            profit_loss_amount = current_value - total_inv_dec

            if total_inv_dec > 0:
                current_profit_rate = (profit_loss_amount / total_inv_dec) * 100

        return DcaMarketStatus(
            market=market,
            status=DcaStatus.ACTIVE if state.is_active else DcaStatus.INACTIVE,
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
            statistics=None,
            recent_history=[],
        )
