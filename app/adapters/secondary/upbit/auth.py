import hashlib
import logging
import uuid
from dataclasses import dataclass
from urllib.parse import urlencode

import jwt

logger = logging.getLogger(__name__)


@dataclass
class UpbitAuth:
    access_key: str
    secret_key: str

    def create_jwt_token(self, query_params: dict[str, str] | None = None) -> str:
        payload = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
        }

        if query_params:
            m = hashlib.sha512()
            m.update(urlencode(query_params).encode())
            query_hash = m.hexdigest()

            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        jwt_token = jwt.encode(payload, self.secret_key)
        return f"Bearer {jwt_token}"
