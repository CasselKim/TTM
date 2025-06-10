import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.usecase.account_usecase import AccountUseCase
    from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
    from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
    from app.application.usecase.order_usecase import OrderUseCase
    from app.application.usecase.ticker_usecase import TickerUseCase
    from resources.discord.bot import DiscordBot

logger = logging.getLogger(__name__)


class DiscordCommandAdapter:
    """Discord 명령어 어댑터 (인바운드 포트)"""

    def __init__(
        self,
        bot: "DiscordBot",
        account_usecase: "AccountUseCase",
        ticker_usecase: "TickerUseCase",
        order_usecase: "OrderUseCase",
        infinite_buying_usecase: "InfiniteBuyingUsecase",
        ui_usecase: "DiscordUIUseCase",
    ):
        self.bot = bot
        self.account_usecase = account_usecase
        self.ticker_usecase = ticker_usecase
        self.order_usecase = order_usecase
        self.infinite_buying_usecase = infinite_buying_usecase
        self.ui_usecase = ui_usecase

    async def setup_all_commands(self) -> None:
        """슬래시 커맨드 설정"""
        from resources.discord.commands import setup_commands

        logger.info("명령어 설정을 시작합니다.")
        await setup_commands(
            self.bot,
            account_usecase=self.account_usecase,
            ticker_usecase=self.ticker_usecase,
            order_usecase=self.order_usecase,
            infinite_buying_usecase=self.infinite_buying_usecase,
            ui_usecase=self.ui_usecase,
        )
