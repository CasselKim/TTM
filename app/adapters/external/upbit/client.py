import logging
from typing import Any, cast

import requests

from app.adapters.external.upbit.auth import UpbitAuth
from app.domain.constants import NetworkConstants

logger = logging.getLogger(__name__)


class UpbitClient:
    def __init__(self, access_key: str, secret_key: str):
        self.auth = UpbitAuth(access_key=access_key, secret_key=secret_key)
        self.base_url = NetworkConstants.UPBIT_API_BASE_URL

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, str] | None = None,
        json_data: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": self.auth.create_jwt_token(params or json_data),
            "Content-Type": "application/json",
            "Charset": "UTF-8",
        }

        # logger.info(f"Request: {method} {url}, params: {params}, json: {json_data}")

        if method.upper() == "GET":
            response = requests.request(method, url, params=params, headers=headers)
        else:
            response = requests.request(
                method, url, params=params, headers=headers, json=json_data
            )

        # logger.info(f"Response: {response.json()}")

        # HTTP 오류 상태 확인
        if not response.ok:
            try:
                error_data = response.json()
                # Upbit API 오류 응답에서 상세 메시지 추출
                if "error" in error_data:
                    error_info = error_data["error"]
                    error_message = error_info.get("message", "Unknown error")
                    error_name = error_info.get("name", "unknown_error")

                    # 한국어 메시지와 영어 코드를 모두 포함한 상세 오류 메시지 생성
                    detailed_message = f"{error_message} ({error_name})"
                    logger.error(f"Upbit API Error: {detailed_message}")
                    raise requests.HTTPError(detailed_message, response=response)
                else:
                    # error 필드가 없는 경우 기본 HTTP 오류 처리
                    response.raise_for_status()
            except ValueError:
                # JSON 파싱 실패 시 기본 HTTP 오류 처리
                response.raise_for_status()

        return response.json()

    def get_accounts(self) -> list[dict[str, Any]]:
        """계좌 정보 조회"""
        return cast(list[dict[str, Any]], self._request("GET", "/accounts"))

    def get_ticker(self, markets: str) -> list[dict[str, Any]]:
        """종목별 현재가 정보 조회

        Args:
            markets: 반점으로 구분되는 종목 코드 (ex. "KRW-BTC,KRW-ETH")

        Returns:
            list[dict[str, Any]]: 현재가 정보 리스트
        """
        params = {"markets": markets}
        # 시세 정보는 인증이 필요 없으므로 auth 없이 요청
        url = f"{self.base_url}/ticker"
        headers = {"Content-Type": "application/json", "Charset": "UTF-8"}

        logger.info(f"Request: {url}, {params}, {headers}")
        response = requests.get(url, params=params, headers=headers)
        logger.info(f"Response: {response.json()}")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def place_order(
        self,
        market: str,
        side: str,
        ord_type: str,
        volume: str | None = None,
        price: str | None = None,
    ) -> dict[str, Any]:
        """주문하기

        Args:
            market: 마켓 ID (ex. "KRW-BTC")
            side: 주문 종류 ("bid": 매수, "ask": 매도)
            ord_type: 주문 타입 ("limit": 지정가, "price": 시장가 매수, "market": 시장가 매도)
            volume: 주문량 (지정가, 시장가 매도 시 필수)
            price: 주문 가격 (지정가, 시장가 매수 시 필수)

        Returns:
            dict[str, Any]: 주문 결과
        """
        order_data = {"market": market, "side": side, "ord_type": ord_type}

        if volume is not None:
            order_data["volume"] = volume
        if price is not None:
            order_data["price"] = price

        return cast(
            dict[str, Any], self._request("POST", "/orders", json_data=order_data)
        )

    def get_order(self, uuid: str) -> dict[str, Any]:
        """개별 주문 조회

        Args:
            uuid: 주문 UUID

        Returns:
            dict[str, Any]: 주문 정보
        """
        params = {"uuid": uuid}
        return cast(dict[str, Any], self._request("GET", "/order", params=params))

    def cancel_order(self, uuid: str) -> dict[str, Any]:
        """주문 취소

        Args:
            uuid: 주문 UUID

        Returns:
            dict[str, Any]: 취소 결과
        """
        params = {"uuid": uuid}
        return cast(dict[str, Any], self._request("DELETE", "/order", params=params))
