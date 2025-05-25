from typing import Any
import requests
from app.adapters.secondary.upbit.auth import UpbitAuth
import logging

logger = logging.getLogger(__name__)

class UpbitClient:
    def __init__(self, access_key: str, secret_key: str):
        self.auth = UpbitAuth(access_key, secret_key)
        self.base_url = "https://api.upbit.com/v1"

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.auth.create_jwt_token(params), "Content-Type": "application/json", "Charset": "UTF-8"}
        
        logger.info(f"Request: {url}, {params}, {headers}")
        response = requests.request(method, url, params=params, headers=headers)
        logger.info(f"Response: {response.json()}")
        response.raise_for_status()
        return response.json()

    def get_accounts(self) -> list[dict[str, Any]]:
        """계좌 정보 조회"""
        return self._request("GET", "/accounts")
    
    def get_ticker(self, markets: str) -> list[dict[str, Any]]:
        """종목별 현재가 정보 조회
        
        Args:
            markets: 반점으로 구분되는 종목 코드 (ex. "KRW-BTC,KRW-ETH")
            
        Returns:
            list[dict]: 현재가 정보 리스트
        """
        params = {"markets": markets}
        # 시세 정보는 인증이 필요 없으므로 auth 없이 요청
        url = f"{self.base_url}/ticker"
        headers = {"Content-Type": "application/json", "Charset": "UTF-8"}
        
        logger.info(f"Request: {url}, {params}, {headers}")
        response = requests.get(url, params=params, headers=headers)
        logger.info(f"Response: {response.json()}")
        response.raise_for_status()
        return response.json()
