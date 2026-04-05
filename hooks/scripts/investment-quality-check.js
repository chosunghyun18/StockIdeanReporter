/**
 * Stop 훅 — 투자 분석 프로젝트 품질 체크 리마인더
 *
 * Claude가 응답을 완료할 때마다 자동으로 실행된다.
 * 핵심 품질 항목을 stderr로 출력 → Claude가 자체 점검하도록 유도.
 */

'use strict';

let data = '';
process.stdin.on('data', (chunk) => { data += chunk; });
process.stdin.on('end', () => {
  const checks = [
    '환경변수로 API 키/토큰/시크릿 관리했나요? (하드코딩 금지)',
    '에러 처리(try/except + 의미있는 메시지)를 추가했나요?',
    '타입 힌트(Type Hints)를 포함했나요?',
    '새 함수/모듈 작성 시 테스트를 작성했나요?',
    '함수 ≤50줄, 파일 ≤400줄 기준을 지켰나요?',
    'Slack Webhook URL이 코드에 노출되지 않았나요?',
  ];

  const list = checks.map((c) => `  □ ${c}`).join('\n');
  process.stderr.write(
    `[품질 체크] 완료 전 자체 점검사항:\n${list}\n`
  );

  process.stdout.write(data);
  process.exit(0);
});
