/**
 * 이메일 본문에서 보안코드를 추출하는 유틸
 * 한국어/영어 패턴 모두 지원
 */

/**
 * 코드 앞에 오는 레이블 패턴 (한국어 + 영어)
 */
const LABEL_PATTERNS = [
  // 한국어
  /인증\s*번호\s*[：:는은이가]?\s*(\d{4,8})/i,
  /보안\s*코드\s*[：:는은이가]?\s*(\d{4,8})/i,
  /인증\s*코드\s*[：:는은이가]?\s*(\d{4,8})/i,
  /확인\s*코드\s*[：:는은이가]?\s*(\d{4,8})/i,
  /일회용\s*비밀번호\s*[：:는은이가]?\s*(\d{4,8})/i,
  /OTP\s*[：:는은이가]?\s*(\d{4,8})/i,
  /코드\s*[：:는은이가]?\s*(\d{4,8})/i,

  // 영어
  /verification\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /security\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /one[\s-]?time\s*(password|code|passcode)\s*[：:is]?\s*(\d{4,8})/i,
  /confirmation\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /access\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /login\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /auth(entication)?\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /your\s*code\s*[：:is]?\s*(\d{4,8})/i,
  /code\s*[：:is]\s*(\d{4,8})/i,

  // 굵은 텍스트 스타일 (HTML 파싱 후)
  /is\s+(\d{6})\b/i,
  /use\s+(\d{6})\b/i,
];

/**
 * 단독으로 강조된 6자리 숫자 패턴 (줄 전체가 숫자인 경우)
 */
const STANDALONE_CODE_PATTERN = /^\s*(\d{6})\s*$/m;

/**
 * 이메일 제목에서 보안코드 메일 여부 판단
 * @param {string} subject
 * @returns {boolean}
 */
export function isSecurityCodeEmail(subject) {
  const keywords = [
    '인증', '보안코드', '보안 코드', 'verification', 'security code',
    'one-time', 'OTP', '확인코드', '확인 코드', 'confirmation',
    'login code', 'sign in', 'signin', '로그인 코드',
  ];
  const lower = subject.toLowerCase();
  return keywords.some((kw) => lower.includes(kw.toLowerCase()));
}

/**
 * 이메일 본문에서 보안코드 추출
 * @param {string} body - 이메일 본문 (plain text 또는 HTML 태그 제거 후)
 * @returns {string | null} 추출된 코드 또는 null
 */
export function extractSecurityCode(body) {
  if (!body) return null;

  // HTML 태그 제거
  const text = body.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ');

  // 1순위: 레이블 패턴 매칭
  for (const pattern of LABEL_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      // 그룹 중 숫자만 있는 마지막 캡처 그룹 반환
      const code = match[match.length - 1];
      if (code && /^\d{4,8}$/.test(code)) {
        return code;
      }
    }
  }

  // 2순위: 줄 단독 6자리 숫자
  const standaloneMatch = text.match(STANDALONE_CODE_PATTERN);
  if (standaloneMatch) {
    return standaloneMatch[1];
  }

  return null;
}

/**
 * 추출된 코드 유효성 검증
 * @param {string} code
 * @returns {boolean}
 */
export function isValidCode(code) {
  if (!code) return false;
  // 4~8자리 숫자
  if (!/^\d{4,8}$/.test(code)) return false;
  // 모두 같은 숫자(1111, 000000)는 제외
  if (/^(\d)\1+$/.test(code)) return false;
  return true;
}
