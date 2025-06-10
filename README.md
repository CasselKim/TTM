# TTM 자동매매 봇

> 업비트 API를 사용한 DCA(분할매수) 자동매매 시스템

## 📈 주요 기능

### DCA (Dollar Cost Averaging)
- **분할 매수**: 가격 하락 시 추가 매수로 평균 단가 낮추기
- **자동 익절**: 목표 수익률 달성 시 자동 매도
- **실시간 수익률**: 현재 손익 상황 실시간 확인

### Discord 봇 지원
- Discord를 통한 매매 현황 조회
- 실시간 알림 및 상태 업데이트
- 간편한 명령어로 봇 제어

## 🛠 설치 및 실행

### 1. 프로젝트 다운로드
```bash
git clone https://github.com/CasselKim/TTM.git
cd TTM
```

### 2. Poetry 설치
```bash
# Poetry가 없다면 설치
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. 의존성 설치
```bash
poetry install
```

### 4. Docker로 실행
```bash
docker build -f docker/Dockerfile . -t ttm-image
docker compose -f docker/docker-compose-local.yml -p ttm up -d
```

## ⚙️ 환경 설정

다음 환경변수들을 설정해야 합니다:

```bash
# 업비트 API
export UPBIT_ACCESS_KEY="your_access_key"
export UPBIT_SECRET_KEY="your_secret_key"

# Discord 봇
export DISCORD_BOT_TOKEN="your_bot_token"
export DISCORD_HISTORY_CHANNEL_ID="channel_id"

# DCA 설정
export ENABLE_DCA_SCHEDULER="true"
export DCA_INTERVAL_SECONDS="30"
```

## 📊 사용 예시

```python
# DCA 상태 조회
market_status = await dca_usecase.get_dca_market_status("KRW-BTC")

print(f"시장: {market_status.market}")
print(f"총 투자금액: {market_status.total_investment:,.0f}원")
print(f"평균 매수가: {market_status.average_price:,.0f}원")
print(f"현재 수익률: {market_status.current_profit_rate:.2%}")
```

## 🏗 기술 스택

- **언어**: Python 3.12+
- **웹**: FastAPI
- **데이터베이스**: MySQL
- **캐시**: Valkey (Redis 호환)
- **컨테이너**: Docker
- **아키텍처**: Domain-Driven Design (DDD)

## 📋 요구사항

- Python 3.12+
- Poetry 1.6.1+
- Docker & Docker Compose

## 🚀 배포

GitHub Actions를 통한 자동 배포:
1. PR 생성
2. 자동 테스트 실행
3. 테스트 통과 시 자동 머지
4. Docker 이미지 빌드 및 Docker Hub 푸시
5. AWS EC2에 자동 배포

## 📄 라이선스

MIT License

---

© 2024 TTM Trading Bot
