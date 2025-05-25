from dependency_injector import containers, providers

from app.adapters.secondary.adapter.upbit_adapter import UpbitAdapter
from app.usecase.usecase.get_account_balance_usecase import GetAccountBalanceUseCase
from app.usecase.usecase.get_ticker_price_usecase import GetTickerPriceUseCase
from app.usecase.usecase.order_usecase import OrderUseCase


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Adapters
    upbit_adapter = providers.Singleton(
        UpbitAdapter,
        access_key=config.upbit.access_key,
        secret_key=config.upbit.secret_key,
    )

    # Use cases
    get_account_balance_usecase = providers.Singleton(
        GetAccountBalanceUseCase,
        account_repository=upbit_adapter,
    )

    get_ticker_price_usecase = providers.Singleton(
        GetTickerPriceUseCase,
        ticker_repository=upbit_adapter,
    )

    order_usecase = providers.Singleton(
        OrderUseCase,
        order_repository=upbit_adapter,
        ticker_repository=upbit_adapter,
    )
