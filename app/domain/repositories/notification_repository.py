from abc import ABC, abstractmethod
from datetime import datetime


class NotificationRepository(ABC):
    """알림 리포지토리 인터페이스"""

    @abstractmethod
    async def send_trade_notification(
        self,
        market: str,
        side: str,
        price: float,
        volume: float,
        total_price: float,
        fee: float,
        executed_at: datetime,
    ) -> bool:
        """거래 체결 알림 전송"""
        ...

    @abstractmethod
    async def send_error_notification(
        self, error_type: str, error_message: str, details: str | None = None
    ) -> bool:
        """에러 알림 전송"""
        ...

    @abstractmethod
    async def send_info_notification(
        self,
        title: str,
        message: str,
        fields: list[tuple[str, str, bool]] | None = None,
    ) -> bool:
        """정보 알림 전송"""
        ...
