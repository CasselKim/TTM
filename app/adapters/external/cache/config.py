import os

from pydantic import BaseModel


class CacheConfig(BaseModel):
    """캐시 연결 설정"""

    host: str
    port: int
    db: int = 0
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    decode_responses: bool = True
    use_tls: bool = False

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """환경변수에서 설정을 읽어옵니다."""
        host = os.getenv("CACHE_ADDRESS", "localhost")
        port = int(os.getenv("CACHE_PORT", "6379"))

        return cls(
            host=host,
            port=port,
        )
