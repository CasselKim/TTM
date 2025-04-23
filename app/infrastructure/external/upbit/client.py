import httpx
from typing import Dict, Any, Optional
from .auth import UpbitAuth
from .exceptions import UpbitAPIException

class UpbitClient:
    BASE_URL = "https://api.upbit.com/v1"

    def __init__(self, access_key: str, secret_key: str):
        self.auth = UpbitAuth(access_key=access_key, secret_key=secret_key)
        self.client = httpx.Client()

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": self.auth.create_jwt_token(params)}

        try:
            response = self.client.request(method, url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise UpbitAPIException(f"API request failed: {str(e)}")

    def get_market_all(self) -> Dict[str, Any]:
        """모든 마켓 정보 조회"""
        return self._request("GET", "/market/all")

    def get_ticker(self, markets: str) -> Dict[str, Any]:
        """현재가 정보 조회"""
        return self._request("GET", "/ticker", params={"markets": markets})

    def get_orderbook(self, markets: str) -> Dict[str, Any]:
        """호가 정보 조회"""
        return self._request("GET", "/orderbook", params={"markets": markets})

    def create_order(self, market: str, side: str, volume: str, price: str, ord_type: str) -> Dict[str, Any]:
        """주문 생성"""
        params = {
            "market": market,
            "side": side,
            "volume": volume,
            "price": price,
            "ord_type": ord_type
        }
        return self._request("POST", "/orders", params=params)

    def get_order(self, uuid: str) -> Dict[str, Any]:
        """주문 조회"""
        return self._request("GET", "/order", params={"uuid": uuid}) 