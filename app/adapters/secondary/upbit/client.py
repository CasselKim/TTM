from typing import Any
import requests
from app.adapters.secondary.upbit.auth import UpbitAuth
import logging

logger = logging.getLogger(__name__)

class UpbitClient:
    def __init__(self, access_key: str, secret_key: str):
        self.auth = UpbitAuth(access_key, secret_key)
        self.base_url = "https://api.upbit.com/v1"

    def _request(self, method: str, endpoint: str, params: dict[str, str] | None = None, json_data: dict[str, str] | None = None):
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.auth.create_jwt_token(params or json_data), "Content-Type": "application/json", "Charset": "UTF-8"}
        
        logger.info(f"Request: {method} {url}, params: {params}, json: {json_data}")
        
        if method.upper() == "GET":
            response = requests.request(method, url, params=params, headers=headers)
        else:
            response = requests.request(method, url, params=params, headers=headers, json=json_data)
            
        logger.info(f"Response: {response.json()}")
        response.raise_for_status()
        return response.json()

    def get_accounts(self) -> list[dict]:
        """계좌 정보 조회"""
        return self._request("GET", "/accounts")
    
    def get_ticker(self, markets: str) -> list[dict]:
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

    def place_order(self, market: str, side: str, ord_type: str, volume: str | None = None, price: str | None = None) -> dict:
        """주문하기
        
        Args:
            market: 마켓 ID (ex. "KRW-BTC")
            side: 주문 종류 ("bid": 매수, "ask": 매도)
            ord_type: 주문 타입 ("limit": 지정가, "price": 시장가 매수, "market": 시장가 매도)
            volume: 주문량 (지정가, 시장가 매도 시 필수)
            price: 주문 가격 (지정가, 시장가 매수 시 필수)
            
        Returns:
            dict: 주문 결과
        """
        order_data = {
            "market": market,
            "side": side,
            "ord_type": ord_type
        }
        
        if volume is not None:
            order_data["volume"] = volume
        if price is not None:
            order_data["price"] = price
            
        return self._request("POST", "/orders", json_data=order_data)

    def get_order(self, uuid: str) -> dict:
        """개별 주문 조회
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            dict: 주문 정보
        """
        params = {"uuid": uuid}
        return self._request("GET", "/order", params=params)

    def cancel_order(self, uuid: str) -> dict:
        """주문 취소
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            dict: 취소 결과
        """
        params = {"uuid": uuid}
        return self._request("DELETE", "/order", params=params)
