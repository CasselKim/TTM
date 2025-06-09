from dependency_injector import containers, providers

from app.adapters.external.cache.adapter import (
    CacheInfiniteBuyingRepository,
)
from app.adapters.external.cache.config import CacheConfig
from app.adapters.external.discord.command_adapter import DiscordCommandAdapter
from app.adapters.external.discord.notification_adapter import (
    DiscordNotificationAdapter,
)
from app.adapters.external.upbit.adapter import UpbitAdapter
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.domain.repositories.notification import NotificationRepository
from resources.discord.bot import DiscordBot


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
    infinite_buying_repository: providers.Singleton[CacheInfiniteBuyingRepository] = (
        providers.Singleton(
            CacheInfiniteBuyingRepository,
            config=cache_config,
        )
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

    infinite_buying_usecase = providers.Singleton(
        InfiniteBuyingUsecase,
        account_repository=upbit_adapter,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
        infinite_buying_repository=infinite_buying_repository,
        notification_repo=notification_adapter,
    )

    discord_ui_usecase = providers.Singleton(
        DiscordUIUseCase,
        account_usecase=account_usecase,
        infinite_buying_usecase=infinite_buying_usecase,
    )

    # Discord Adapters
    command_adapter = providers.Singleton(
        DiscordCommandAdapter,
        bot=discord_bot,
        account_usecase=account_usecase,
        ticker_usecase=ticker_usecase,
        order_usecase=order_usecase,
        infinite_buying_usecase=infinite_buying_usecase,
        ui_usecase=discord_ui_usecase,
    )
