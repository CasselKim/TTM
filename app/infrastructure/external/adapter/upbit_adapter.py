from typing import Dict, Any
from ..upbit.client import UpbitClient
from ..upbit.exceptions import UpbitAPIException
 
class UpbitAdapter:
    def __init__(self, access_key: str, secret_key: str):
        self.client = UpbitClient(access_key=access_key, secret_key=secret_key)

    async def get_market_price(self, market: str) -> Dict[str, Any]:
        """특정 마켓의 현재가 조회"""
        try:
            response = self.client.get_ticker(markets=market)
            if not response:
                raise UpbitAPIException("No price data available")
            return {
                "market": market,
                "price": response[0]["trade_price"],
                "timestamp": response[0]["timestamp"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to get market price: {str(e)}")

    async def create_market_order(self, market: str, side: str, volume: str) -> Dict[str, Any]:
        """시장가 주문 생성"""
        try:
            response = self.client.create_order(
                market=market,
                side=side,
                volume=volume,
                price=None,
                ord_type="market"
            )
            return {
                "order_id": response["uuid"],
                "market": response["market"],
                "status": response["state"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to create market order: {str(e)}")

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            response = self.client.get_order(uuid=order_id)
            return {
                "order_id": response["uuid"],
                "status": response["state"],
                "executed_volume": response["executed_volume"],
                "remaining_volume": response["remaining_volume"]
            }
        except UpbitAPIException as e:
            raise e
        except Exception as e:
            raise UpbitAPIException(f"Failed to get order status: {str(e)}") 