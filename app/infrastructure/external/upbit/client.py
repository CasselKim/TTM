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
