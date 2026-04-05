# Reliability

## 장애 시나리오 및 대응

| 시나리오 | 현재 대응 | 목표 대응 |
|----------|-----------|-----------|
| yfinance 데이터 없음 | 예외 처리 후 종료 | 재시도 3회 후 알림 |
| Claude API 타임아웃 | 예외 전파 | 지수 백오프 재시도 |
| Slack Webhook 실패 | 재시도 3회 | Dead Letter Queue |
| 분석 파이프라인 중단 | 로그 출력 | 부분 결과 저장 후 재개 |

## 모니터링

현재 모니터링 방법:
- `output/slack_sent_*.log` — Slack 전송 이력
- `AgentDashBoard/` — 에이전트 실행 UI

## SLO (목표)

- 분석 파이프라인 성공률 ≥ 95%
- Slack 전송 성공률 ≥ 99%
- 분석 완료 시간 ≤ 3분/종목
