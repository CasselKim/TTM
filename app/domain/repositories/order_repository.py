from abc import ABC, abstractmethod
from app.domain.models.order import Order, OrderRequest, OrderResult


class OrderRepository(ABC):
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResult:
        """주문을 실행합니다.
        
        Args:
            order_request: 주문 요청 정보
            
        Returns:
            OrderResult: 주문 결과
        """
        
    @abstractmethod
    async def get_order(self, uuid: str) -> Order:
        """특정 주문 정보를 조회합니다.
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            Order: 주문 정보
        """
        
    @abstractmethod
    async def cancel_order(self, uuid: str) -> OrderResult:
        """주문을 취소합니다.
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            OrderResult: 취소 결과
        """ 