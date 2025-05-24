from dependency_injector import containers, providers
from app.infrastructure.external.adapter.upbit_adapter import UpbitAdapter
from app.application.usecase.get_account_balance_usecase import GetAccountBalanceUseCase

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