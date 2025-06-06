# Discord 봇 잔고 조회 개선 예시

## 🏦 개선된 잔고 조회 화면

### 1. 기본 잔고 조회 (!잔고)

```
💰 **계좌 잔고**

💵 KRW (원화)
────────────────────────────────────────
항목           금액
────────────────────────────────────────
사용가능       85만
거래중         15만
총 보유        100만

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🪙 암호화폐
─────────────────────────────────────────────────────────────────────────────────────
통화     수량        현재가       평가금액      평균단가     수익률        손익
─────────────────────────────────────────────────────────────────────────────────────
BTC      0.001       9500만       95만         9000만       🟢+5.56%     +5만
ETH      0.1         320만        32만         300만        🟢+6.67%     +2만
DOT      50          3만          150만        2.8만        🟢+7.14%     +1만
─────────────────────────────────────────────────────────────────────────────────────

💎 **포트폴리오 요약**
• **총 평가금액**: 377만원 (KRW: 100만원 + 암호화폐: 277만원)
• **총 투자금액**: 369만원
• **총 수익률**: 🟢+2.17% (+8만원) 📈
```

### 2. 무한매수법 조회 (!무한매수조회 KRW-BTC)

```
🔄 KRW-BTC 무한매수법 상태

상태: BUYING              현재 회차: 3회             사이클 ID: cyc_2024...

총 투자액: 35만원          평균 단가: 8800만원        목표 가격: 9680만원

현재가: 9500만원          현재 평가금액: 38만원       현재 수익률: 🟢+7.95%

손익 금액: 🟢+3만원

최근 매수 히스토리:
1회: 9000만원 (10만원)
2회: 8500만원 (15만원)
3회: 8000만원 (10만원)
```

### 3. 시세 조회 (!시세 KRW-BTC)

```
📈 **KRW-BTC 시세 정보**

**현재가**: 9500만원
**전일 대비**: 🟢 300만원 (+3%)
**고가**: 9600만원
**저가**: 9200만원
**거래량**: 450
**거래대금**: 4275억원
```

## ✨ 주요 개선사항

### 1. 숫자 표기법 개선
- **기존**: 95,000,000 KRW
- **개선**: 9500만원

### 2. 암호화폐별 상세 정보 추가
- 현재가 실시간 조회
- 평가금액 계산 (수량 × 현재가)
- 수익률 계산 (현재가 vs 평균매수가)
- 손익 금액 표시

### 3. 총 포트폴리오 분석
- KRW 포함한 전체 평가금액
- 총 투자금액 대비 수익률
- 시각적 이모지로 수익/손실 표시

### 4. 무한매수법 수익률 표시
- 실시간 현재가 조회
- 평균매수가 대비 수익률
- 현재 평가금액과 손익 표시

### 5. 컬럼 정렬 최적화
- 고정폭 표 형태로 정렬
- 긴 숫자는 한국식 단위로 단축
- 이모지로 시각적 구분

## 📱 사용법

```bash
# 전체 잔고 조회 (수익률 포함)
!잔고

# 특정 암호화폐 시세 조회 (한국 단위)
!시세 KRW-BTC

# 무한매수법 수익률 조회
!무한매수조회 KRW-BTC
```

모든 금액은 한국식 단위(만, 억)로 표시되어 가독성이 크게 향상되었습니다! 💫
