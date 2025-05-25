from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.container import Container
from app.usecase.usecase.get_account_balance_usecase import (
    AccountBalanceDTO,
    GetAccountBalanceUseCase,
)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/balance", response_model=AccountBalanceDTO)
@inject
async def get_balance(
    usecase: GetAccountBalanceUseCase = Depends(
        Provide[Container.get_account_balance_usecase]
    ),
) -> AccountBalanceDTO:
    """
    현재 보유한 자산 정보를 조회합니다.
    """
    return await usecase.execute()
