# Quality Score

## 코드 품질 기준

| 항목 | 목표 | 현재 |
|------|------|------|
| 테스트 커버리지 | ≥ 80% | ~80% |
| 함수당 최대 줄 수 | ≤ 50줄 | - |
| 파일당 최대 줄 수 | ≤ 400줄 | - |
| 타입 힌트 적용 | 100% | - |

## 테스트 실행

```bash
cd StockIdeaReporter
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 품질 게이트 (CI)

`.github/workflows/analysis.yml` 에서 자동 실행:

- [ ] pytest 통과
- [ ] 커버리지 ≥ 80%
- [ ] 린트 통과 (ruff / flake8)

## 리뷰 체크리스트

- [ ] 타입 힌트 작성됨
- [ ] docstring (Google 스타일) 작성됨
- [ ] 단위 테스트 존재
- [ ] 환경변수로 민감 정보 관리
