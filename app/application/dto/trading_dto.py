"""
매매 관련 DTO 정의

매매 실행 결과 등 데이터 전송을 위한 객체들을 정의합니다.
"""

from decimal import Decimal

from pydantic import BaseModel


class TradingResult(BaseModel):
    """거래 결과 (DTO)"""

    success: bool
    message: str
    order_uuid: str | None = None
    executed_amount: Decimal | None = None
    executed_price: Decimal | None = None
