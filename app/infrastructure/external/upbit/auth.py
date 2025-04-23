import uuid
import jwt
import hashlib
from urllib.parse import urlencode
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class UpbitAuth:
    access_key: str
    secret_key: str

    def create_jwt_token(self, query_params: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }

        if query_params:
            query_string = urlencode(query_params)
            m = hashlib.sha512()
            m.update(query_string.encode())
            query_hash = m.hexdigest()
            
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return f'Bearer {jwt_token}' 