from dependency_injector import containers, providers

from app.adapters.external.cache.dca_adapter import (
    CacheDcaRepository,
)
from app.adapters.external.cache.config import CacheConfig
from app.adapters.internal.discord_command import DiscordCommandAdapter
from app.adapters.external.discord.notification_adapter import (
    DiscordNotificationAdapter,
)
from app.adapters.external.upbit.adapter import UpbitAdapter
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.domain.repositories.notification import NotificationRepository
from common.discord.bot import DiscordBot


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Cache configuration
    cache_config = providers.Singleton(
        CacheConfig.from_env,
    )

    upbit_adapter = providers.Singleton(
        UpbitAdapter,
        access_key=config.upbit.access_key,
        secret_key=config.upbit.secret_key,
    )

    discord_bot = providers.Singleton(
        DiscordBot,
        bot_token=config.discord.bot_token,
        channel_id=config.discord.channel_id.as_int(),
        alert_channel_id=config.discord.alert_channel_id.as_int(),
        log_channel_id=config.discord.log_channel_id.as_int(),
        command_prefix=config.discord.command_prefix,
    )

    notification_adapter: providers.Provider[NotificationRepository] = (
        providers.Singleton(
            DiscordNotificationAdapter,
            bot=discord_bot,
        )
    )

    # Repositories
    dca_repository: providers.Singleton[CacheDcaRepository] = providers.Singleton(
        CacheDcaRepository,
        config=cache_config,
    )

    # Use cases
    account_usecase = providers.Singleton(
        AccountUseCase,
        account_repository=upbit_adapter,
        notification_repo=notification_adapter,
    )

    ticker_usecase = providers.Singleton(
        TickerUseCase,
        ticker_repository=upbit_adapter,
    )

    order_usecase = providers.Singleton(
        OrderUseCase,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
        notification_repo=notification_adapter,
    )

    dca_usecase = providers.Singleton(
        DcaUsecase,
        account_repository=upbit_adapter,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
        dca_repository=dca_repository,
        notification_repo=notification_adapter,
    )

    discord_ui_usecase = providers.Singleton(
        DiscordUIUseCase,
        account_usecase=account_usecase,
        dca_usecase=dca_usecase,
        ticker_usecase=ticker_usecase,
    )

    # Discord Adapters
    command_adapter = providers.Singleton(
        DiscordCommandAdapter,
        bot=discord_bot,
        account_usecase=account_usecase,
        ticker_usecase=ticker_usecase,
        order_usecase=order_usecase,
        dca_usecase=dca_usecase,
        ui_usecase=discord_ui_usecase,
    )
