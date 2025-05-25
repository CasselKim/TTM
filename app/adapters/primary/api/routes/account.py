from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.application.dto.account_dto import AccountBalanceDTO
from app.application.usecase.account_usecase import AccountUseCase
from app.container import Container

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/balance", response_model=AccountBalanceDTO)
@inject
async def get_balance(
    usecase: AccountUseCase = Depends(Provide[Container.account_usecase]),
) -> AccountBalanceDTO:
    """
    현재 보유한 자산 정보를 조회합니다.
    """
    return await usecase.get_balance()
