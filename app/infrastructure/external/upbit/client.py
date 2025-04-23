from typing import Any
import requests
from app.infrastructure.external.upbit.auth import UpbitAuth

class UpbitClient:
    def __init__(self, access_key: str, secret_key: str):
        self.auth = UpbitAuth(access_key, secret_key)
        self.base_url = "https://api.upbit.com/v1"

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.auth.create_jwt_token(params)}"}
        
        response = requests.request(method, url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_accounts(self) -> list[dict[str, Any]]:
        """계좌 정보 조회"""
        return self._request("GET", "/accounts")

    def get_market_all(self) -> dict[str, Any]:
        """모든 마켓 정보 조회"""
        return self._request("GET", "/market/all")

    def get_ticker(self, markets: str) -> dict[str, Any]:
        """현재가 정보 조회"""
        return self._request("GET", "/ticker", {"markets": markets})

    def get_orderbook(self, markets: str) -> dict[str, Any]:
        """호가 정보 조회"""
        return self._request("GET", "/orderbook", {"markets": markets})

    def create_order(self, market: str, side: str, volume: str, price: str, ord_type: str) -> dict[str, Any]:
        """주문 생성"""
        params = {
            "market": market,
            "side": side,
            "volume": volume,
            "price": price,
            "ord_type": ord_type
        }
        return self._request("POST", "/orders", params)

    def get_order(self, uuid: str) -> dict[str, Any]:
        """주문 조회"""
        return self._request("GET", "/order", {"uuid": uuid}) 