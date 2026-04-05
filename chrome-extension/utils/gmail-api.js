/**
 * Gmail REST API 래퍼
 * OAuth2 토큰은 chrome.identity를 통해 획득
 */

const GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1/users/me';

/**
 * Gmail OAuth2 토큰 획득
 * @param {boolean} interactive - true이면 로그인 팝업 표시
 * @returns {Promise<string>} access token
 */
export async function getAuthToken(interactive = false) {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!token) {
        reject(new Error('토큰을 가져올 수 없습니다.'));
        return;
      }
      resolve(token);
    });
  });
}

/**
 * OAuth2 토큰 해제 (로그아웃)
 * @returns {Promise<void>}
 */
export async function revokeAuthToken() {
  return new Promise((resolve) => {
    chrome.identity.getAuthToken({ interactive: false }, (token) => {
      if (token) {
        chrome.identity.removeCachedAuthToken({ token }, resolve);
      } else {
        resolve();
      }
    });
  });
}

/**
 * 현재 로그인된 Gmail 계정 이메일 조회
 * @param {string} token
 * @returns {Promise<string>} 이메일 주소
 */
export async function getProfileEmail(token) {
  const response = await fetchGmail('/profile', token);
  return response.emailAddress;
}

/**
 * 최근 이메일 목록 조회
 * @param {string} token
 * @param {string} query - Gmail 검색 쿼리 (예: "after:2024/01/01 subject:인증")
 * @param {number} maxResults
 * @returns {Promise<Array<{id: string, threadId: string}>>}
 */
export async function listMessages(token, query = '', maxResults = 10) {
  const params = new URLSearchParams({ maxResults: String(maxResults) });
  if (query) params.set('q', query);

  const response = await fetchGmail(`/messages?${params}`, token);
  return response.messages || [];
}

/**
 * 이메일 상세 조회
 * @param {string} token
 * @param {string} messageId
 * @returns {Promise<GmailMessage>}
 */
export async function getMessage(token, messageId) {
  return fetchGmail(`/messages/${messageId}?format=full`, token);
}

/**
 * 이메일 제목 추출
 * @param {GmailMessage} message
 * @returns {string}
 */
export function getSubject(message) {
  const headers = message.payload?.headers || [];
  const subjectHeader = headers.find((h) => h.name.toLowerCase() === 'subject');
  return subjectHeader?.value || '';
}

/**
 * 이메일 발신자 추출
 * @param {GmailMessage} message
 * @returns {string}
 */
export function getSender(message) {
  const headers = message.payload?.headers || [];
  const fromHeader = headers.find((h) => h.name.toLowerCase() === 'from');
  return fromHeader?.value || '';
}

/**
 * 이메일 본문 추출 (plain text 우선, 없으면 HTML)
 * @param {GmailMessage} message
 * @returns {string}
 */
export function getBody(message) {
  const payload = message.payload;
  if (!payload) return '';

  // 단일 파트
  if (payload.body?.data) {
    return decodeBase64Url(payload.body.data);
  }

  // 멀티파트: text/plain 우선
  const parts = payload.parts || [];
  const plainPart = findPart(parts, 'text/plain');
  if (plainPart?.body?.data) {
    return decodeBase64Url(plainPart.body.data);
  }

  // text/html fallback
  const htmlPart = findPart(parts, 'text/html');
  if (htmlPart?.body?.data) {
    return decodeBase64Url(htmlPart.body.data);
  }

  return '';
}

/**
 * 이메일 수신 시각 추출 (ms timestamp)
 * @param {GmailMessage} message
 * @returns {number}
 */
export function getReceivedAt(message) {
  return parseInt(message.internalDate || '0', 10);
}

// ─── Private helpers ───────────────────────────────────────────────────────

async function fetchGmail(path, token) {
  const response = await fetch(`${GMAIL_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    // 토큰 만료 — 캐시 제거 후 재시도 신호
    chrome.identity.removeCachedAuthToken({ token }, () => {});
    throw new Error('AUTH_EXPIRED');
  }

  if (!response.ok) {
    throw new Error(`Gmail API 오류: ${response.status}`);
  }

  return response.json();
}

function decodeBase64Url(encoded) {
  const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/');
  try {
    return decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    );
  } catch {
    return atob(base64);
  }
}

function findPart(parts, mimeType) {
  for (const part of parts) {
    if (part.mimeType === mimeType) return part;
    if (part.parts) {
      const found = findPart(part.parts, mimeType);
      if (found) return found;
    }
  }
  return null;
}
