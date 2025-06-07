from dependency_injector import containers, providers

from app.adapters.external.cache.adapter import (
    CacheInfiniteBuyingRepository,
)
from app.adapters.external.cache.config import CacheConfig
from app.adapters.external.discord.adapter import DiscordAdapter
from app.adapters.external.upbit.adapter import UpbitAdapter
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.application.usecase.trading_usecase import TradingUsecase


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

    discord_adapter = providers.Singleton(
        DiscordAdapter,
        bot_token=config.discord.bot_token,
        channel_id=config.discord.channel_id,
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
    )

    ticker_usecase = providers.Singleton(
        TickerUseCase,
        ticker_repository=upbit_adapter,
    )

    order_usecase = providers.Singleton(
        OrderUseCase,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
        discord_adapter=discord_adapter,
    )

    trading_usecase = providers.Singleton(
        TradingUsecase,
        account_repository=upbit_adapter,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
    )

    infinite_buying_usecase = providers.Singleton(
        InfiniteBuyingUsecase,
        account_repository=upbit_adapter,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
        infinite_buying_repository=infinite_buying_repository,
    )
