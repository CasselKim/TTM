from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provider
from app.application.usecase.get_account_balance_usecase import GetAccountBalanceUseCase, AccountBalanceDTO

router = APIRouter(prefix="/account", tags=["account"])

@router.get("/balance", response_model=AccountBalanceDTO)
@inject
async def get_balance(
    usecase: GetAccountBalanceUseCase = Depends(Provider[GetAccountBalanceUseCase])
) -> AccountBalanceDTO:
    """
    현재 보유한 자산 정보를 조회합니다.
    """
    return await usecase.execute() 