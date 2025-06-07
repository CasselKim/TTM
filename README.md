# TTM Trading Application

> 업비트 API를 활용한 자동 거래 시스템

## 주요 기능

### 무한매수법 (Infinite Buying Strategy)
- 분할 매수를 통한 평균 단가 하락 전략
- 목표 수익률 달성 시 자동 익절
- **실시간 수익률 조회 기능 추가** ✨

#### 수익률 조회 기능
무한매수법 조회 시 다음 정보를 실시간으로 확인할 수 있습니다:
- **현재가**: 실시간 시장 가격
- **현재 수익률**: 평균 매수가 대비 수익률 (%)
- **현재 평가금액**: 보유수량 × 현재가
- **수익/손실 금액**: 현재평가금액 - 총투자금액

```python
# 예시: 무한매수법 상태 조회
market_status = await infinite_buying_usecase.get_infinite_buying_market_status("KRW-BTC")

print(f"시장: {market_status.market}")
print(f"총 투자금액: {market_status.total_investment:,.0f}원")
print(f"평균 매수가: {market_status.average_price:,.0f}원")
print(f"현재가: {market_status.current_price:,.0f}원")
print(f"현재 수익률: {market_status.current_profit_rate:.2%}")
print(f"현재 평가금액: {market_status.current_value:,.0f}원")
print(f"수익/손실: {market_status.profit_loss_amount:,.0f}원")
```

### 기술 스택
- Python 3.11+
- FastAPI
- PostgreSQL
- Redis
- Docker

### 개발 가이드라인
- 타입 힌트 필수 (mypy --strict)
- 코드 포맷팅: ruff
- 테스트 커버리지 유지
- 도메인 주도 설계 (DDD) 적용

---

© 2024 TTM Trading Application

## Requirements
- python 12.0
- poetry 1.6.1
- fastapi 0.104.1


## Installation
### 1. Download repo
```
git clone https://github.com/CasselKim/TTM.git`
```

### 2. Download poetry
https://python-poetry.org/docs/#installing-with-the-official-installer

### 3. Create venv
```
poetry install
```

### 4. Execute docker
```
docker build -f docker/Dockerfile . -t ttm-image
docker compose -f docker/docker-compose-local.yml -p ttm up -d
```

## Configuration

### 환경변수 설정

#### 한글 폰트 설정 (선택사항)
Discord 봇의 이미지 생성 기능에서 한글 폰트를 사용하려면 다음 환경변수를 설정할 수 있습니다:

```bash
# 특정 폰트 파일 경로 지정
export TTM_KOREAN_FONT_PATH="/path/to/your/korean/font.ttf"
```

**자동 폰트 검색 순서:**
1. 환경변수 `TTM_KOREAN_FONT_PATH`로 지정된 폰트
2. 프로젝트 번들 폰트 (`assets/fonts/NotoSansKR-*.ttf`)
3. 시스템 폰트 경로에서 한글 지원 폰트 자동 탐색
   - Linux: Noto Sans CJK, 나눔고딕, DejaVu 등
   - macOS: Apple Gothic, Noto Sans KR 등
   - Windows: 맑은고딕, Noto Sans KR 등

**Docker 환경에서의 한글 폰트:**
Dockerfile에 다음 폰트들이 자동으로 설치됩니다:
- `fonts-noto-cjk`: Noto Sans CJK 폰트 패밀리
- `fonts-nanum`: 나눔고딕 폰트 패밀리

## Deployment - Github Action
1. PR open
2. Test by github action
3. Auto-merge when test pass
4. Build as image and push to Docker hub
5. Run the image on the AWS EC2 through github action

## License
This project is licensed under the terms of the MIT license.
