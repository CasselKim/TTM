from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from app.application.usecase.get_account_balance_usecase import AccountBalanceDTO, GetAccountBalanceUseCase
from app.infrastructure.container import Container

router = APIRouter(prefix="/account", tags=["account"])

@router.get("/balance", response_model=AccountBalanceDTO)
@inject
async def get_balance(
    usecase: GetAccountBalanceUseCase = Depends(Provide[Container.get_account_balance_usecase])
) -> AccountBalanceDTO:
    """
    현재 보유한 자산 정보를 조회합니다.
    """
    return await usecase.execute() 