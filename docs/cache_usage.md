# 캐시 사용 가이드

## 개요

이 프로젝트는 AWS ElastiCache Valkey를 활용한 캐시 시스템을 지원합니다. Redis 호환 인터페이스를 통해 고성능 캐싱을 제공합니다.

## 환경 설정

### 필수 환경변수

`.env` 파일에 다음 설정을 추가하세요:

```bash
# 캐시 서버 설정
CACHE_ADDRESS=your-valkey-cluster.xxxxx.cache.amazonaws.com
CACHE_PORT=6379
CACHE_PASSWORD=your-password  # 선택사항
```

### AWS ElastiCache Valkey 설정

1. AWS Console에서 ElastiCache 서비스로 이동
2. Valkey 클러스터 생성
3. 보안 그룹에서 6379 포트 허용
4. 엔드포인트 주소를 `CACHE_ADDRESS`에 설정

## 코드 구조

```
app/
├── domain/
│   └── repositories/
│       └── cache_repository.py      # 캐시 리포지토리 인터페이스
├── adapters/
│   └── external/
│       └── cache/
│           ├── adapter.py           # Valkey 어댑터 구현
│           └── config.py            # 캐시 설정
└── application/
    └── usecase/
        └── cache_usecase.py         # 캐시 유스케이스 예제
```

## 사용법

### 1. 의존성 주입을 통한 사용

```python
from app.container import Container

# 컨테이너 초기화
container = Container()

# 캐시 유스케이스 가져오기
cache_usecase = container.cache_usecase()

# 캐시 상태 확인
is_healthy = await cache_usecase.health_check()
```

### 2. 직접 어댑터 사용

```python
from app.adapters.external.cache.adapter import ValkeyAdapter
from app.adapters.external.cache.config import CacheConfig

# 설정 로드
config = CacheConfig.from_env()

# 어댑터 생성
cache_adapter = ValkeyAdapter(config)

# 기본 작업
await cache_adapter.set("key", "value", ttl=300)
value = await cache_adapter.get("key")
exists = await cache_adapter.exists("key")
deleted = await cache_adapter.delete("key")
```

### 3. 캐시 유스케이스 활용

```python
# 티커 데이터 캐싱
await cache_usecase.cache_ticker_data(
    market="KRW-BTC",
    ticker_data={"price": 50000000, "volume": 123.45},
    ttl=300  # 5분
)

# 캐시된 데이터 조회
cached_data = await cache_usecase.get_cached_ticker_data("KRW-BTC")

# 계좌 정보 캐싱
await cache_usecase.cache_account_info(
    user_id="user123",
    account_data={"balance": 1000000, "currency": "KRW"},
    ttl=60  # 1분
)
```

## 연결 테스트

캐시 연결을 테스트하려면 다음 스크립트를 실행하세요:

```bash
python scripts/test_cache_connection.py
```

## 성능 최적화

### 연결 풀 설정

```python
# config.py에서 설정 조정
@dataclass
class CacheConfig:
    max_connections: int = 20        # 연결 풀 크기
    socket_timeout: int = 5          # 소켓 타임아웃
    socket_connect_timeout: int = 5  # 연결 타임아웃
```

### 재시도 정책

- 자동 exponential backoff 적용
- 최대 3회 재시도
- 타임아웃 시 자동 재시도

## 모니터링

### 로그 확인

```python
import logging

# 캐시 관련 로그 레벨 설정
logging.getLogger('app.adapters.external.cache').setLevel(logging.DEBUG)
```

### 헬스체크

```python
# 정기적인 상태 확인
is_healthy = await cache_usecase.health_check()
if not is_healthy:
    logger.error("캐시 서버 연결 불가")
```

## 주의사항

### 1. 직렬화

- 딕셔너리, 리스트는 자동으로 JSON 직렬화
- 문자열, 숫자는 문자열로 저장
- 복잡한 객체는 사전에 직렬화 필요

### 2. TTL 관리

- 기본 TTL은 설정하지 않으면 무제한
- 메모리 효율을 위해 적절한 TTL 설정 권장
- 데이터 특성에 따라 TTL 조정

### 3. 키 네이밍 컨벤션

```python
# 권장 키 네이밍
"ticker:{market}"           # 티커 데이터
"account:{user_id}"         # 계좌 정보
"order:{order_id}"          # 주문 정보
"user_session:{session_id}" # 세션 정보
```

### 4. 에러 핸들링

- 캐시 장애 시 애플리케이션이 중단되지 않도록 처리
- 캐시 실패 시 원본 데이터 소스 사용
- 적절한 로깅과 모니터링 필수

## 트러블슈팅

### 연결 실패

1. 환경변수 확인
2. 보안 그룹 설정 확인
3. 네트워크 연결 상태 확인
4. ElastiCache 클러스터 상태 확인

### 성능 저하

1. 연결 풀 크기 조정
2. TTL 설정 최적화
3. 키 분산 확인
4. 메모리 사용량 모니터링

### 메모리 부족

1. TTL 설정으로 자동 만료
2. 사용하지 않는 키 정리
3. 클러스터 스케일링 고려
