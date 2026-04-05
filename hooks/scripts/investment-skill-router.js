/**
 * UserPromptSubmit 훅 — 투자 분석 프로젝트 스킬 자동 라우터
 *
 * 사용자 프롬프트의 키워드를 분석해 관련 스킬/에이전트 매뉴얼을 Claude에게 안내한다.
 * stderr 출력 → Claude Code가 시스템 리마인더로 Claude에게 전달.
 */

'use strict';

let data = '';
process.stdin.on('data', (chunk) => { data += chunk; });
process.stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(data);
  } catch {
    process.stdout.write(data);
    process.exit(0);
  }

  const prompt = (input.prompt || '').toLowerCase();

  const skillMap = [
    {
      keywords: ['test', '테스트', 'pytest', 'coverage', '커버리지', 'tdd', 'unit'],
      label: 'Python 테스트 패턴',
      path: 'skills/python-testing/SKILL.md',
    },
    {
      keywords: ['market', 'research', '시장', '종목', '주가', 'stock', '산업', 'industry', 'sector', '섹터', '리서치'],
      label: '시장 리서치 패턴',
      path: 'skills/market-research/SKILL.md',
    },
    {
      keywords: ['security', '보안', 'api key', '환경변수', 'secret', 'token', 'credential', '토큰', '취약'],
      label: '보안 스캔 가이드',
      path: 'skills/security-scan/SKILL.md',
    },
    {
      keywords: ['api', 'endpoint', 'server', '데이터 수집', 'yfinance', 'krx', 'pykrx', 'webhook', 'slack', 'financedata'],
      label: '백엔드 패턴',
      path: 'skills/backend-patterns/SKILL.md',
    },
    {
      keywords: ['agent', 'orchestrat', '에이전트', '오케스트레이터', 'pipeline', '파이프라인'],
      label: '에이전트 오케스트레이터',
      path: 'agents/orchestrator.md',
    },
    {
      keywords: ['deep research', 'research agent', '심층 분석', '리서치 에이전트', 'deep-research'],
      label: '심층 리서치 에이전트',
      path: 'skills/deep-research/SKILL.md',
    },
    {
      keywords: ['분석 아이디어', 'idea', '투자 아이디어', 'investment idea'],
      label: '투자 아이디어 생성 에이전트',
      path: 'agents/idea-generator.md',
    },
    {
      keywords: ['code review', '코드 리뷰', 'refactor', '리팩터', 'clean'],
      label: '코드 리뷰 에이전트',
      path: 'agents/code-reviewer.md',
    },
    {
      keywords: [
        'it-orchestrator', '서비스 만들', '서비스 개발', '서비스 구현',
        '웹앱', '웹 앱', 'web app', 'rest api', '백엔드 구현', '백엔드 만들',
        'tech stack', '기술 스택', '스택 선정', '아키텍처 설계',
        'service builder', 'service designer', 'qa engineer', 'security dev',
      ],
      label: 'IT 서비스 개발 팀 오케스트레이터',
      path: 'agents/it-orchestrator.md',
    },
  ];

  const matched = skillMap.filter((s) =>
    s.keywords.some((kw) => prompt.includes(kw))
  );

  if (matched.length > 0) {
    const list = matched.map((s) => `  - [${s.label}](${s.path})`).join('\n');
    process.stderr.write(
      `[스킬 라우터] 작업 시작 전 아래 매뉴얼을 Read 도구로 먼저 확인하세요:\n${list}\n`
    );
  }

  process.stdout.write(data);
  process.exit(0);
});
