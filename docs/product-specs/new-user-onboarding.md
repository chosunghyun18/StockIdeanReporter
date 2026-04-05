# 신규 사용자 온보딩

## 목표

사용자가 처음 설치 후 10분 이내에 첫 분석 결과를 Slack에서 받아볼 수 있도록 한다.

## 온보딩 단계

### 1. 환경 설정 (3분)

```bash
pip install -r requirements.txt
cp StockIdeaReporter/.env.example StockIdeaReporter/.env
# .env에 API 키 입력
```

### 2. 연결 확인 (2분)

```bash
python StockIdeaReporter/main.py --ticker AAPL --market US --dry-run
```

### 3. 첫 분석 실행 (5분)

```bash
python StockIdeaReporter/main.py --ticker AAPL --market US
```

## 필수 환경변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 | ✅ |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | ✅ |
| `SLACK_CHANNEL` | Slack 채널명 | 선택 |

## 성공 기준

- [ ] Slack에서 분석 리포트 수신 확인
- [ ] `output/` 에 분석 파일 생성 확인
