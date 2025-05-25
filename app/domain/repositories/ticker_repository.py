from abc import ABC, abstractmethod

from app.domain.models.ticker import Ticker


class TickerRepository(ABC):
    @abstractmethod
    async def get_ticker(self, market: str) -> Ticker:
        """특정 종목의 현재가 정보를 조회합니다.

        Args:
            market: 종목 코드 (ex. KRW-BTC)

        Returns:
            Ticker: 현재가 정보
        """

    @abstractmethod
    async def get_tickers(self, markets: list[str]) -> list[Ticker]:
        """여러 종목의 현재가 정보를 조회합니다.

        Args:
            markets: 종목 코드 리스트 (ex. ["KRW-BTC", "KRW-ETH"])

        Returns:
            list[Ticker]: 현재가 정보 리스트
        """
