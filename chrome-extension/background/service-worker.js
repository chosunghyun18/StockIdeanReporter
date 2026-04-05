/**
 * Background Service Worker
 * - Gmail 주기적 폴링
 * - 보안코드 추출
 * - 콘텐츠 스크립트로 코드 전달
 */

import {
  getAuthToken,
  listMessages,
  getMessage,
  getSubject,
  getBody,
  getReceivedAt,
} from '../utils/gmail-api.js';
import { isSecurityCodeEmail, extractSecurityCode, isValidCode } from '../utils/code-extractor.js';
import { getAccounts, getLastChecked, setLastChecked, setPendingCode, getSettings } from '../utils/storage.js';

const ALARM_NAME = 'gmail-poll';

// ─── 초기화 ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(async () => {
  await setupAlarm();
  console.log('[SecureCode] 익스텐션 설치 완료');
});

chrome.runtime.onStartup.addListener(async () => {
  await setupAlarm();
});

async function setupAlarm() {
  const { pollIntervalSec } = await getSettings();
  chrome.alarms.clearAll();
  chrome.alarms.create(ALARM_NAME, {
    periodInMinutes: pollIntervalSec / 60,
    delayInMinutes: 0.1, // 시작 후 6초 뒤 첫 실행
  });
}

// ─── 알람 핸들러 (주기적 폴링) ────────────────────────────────────────────

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  await pollGmail();
});

// ─── 팝업 메시지 핸들러 ───────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'POLL_NOW') {
    pollGmail().then(() => sendResponse({ ok: true })).catch((e) => sendResponse({ ok: false, error: e.message }));
    return true; // 비동기 응답
  }

  if (message.type === 'FILL_CODE') {
    injectCodeToActiveTab(message.code);
    sendResponse({ ok: true });
  }
});

// ─── Gmail 폴링 핵심 로직 ─────────────────────────────────────────────────

async function pollGmail() {
  const accounts = await getAccounts();
  if (accounts.length === 0) return;

  const { autoFill, notifyOnDetect } = await getSettings();

  let token;
  try {
    token = await getAuthToken(false);
  } catch {
    console.log('[SecureCode] 토큰 없음 — 로그인 필요');
    return;
  }

  const lastChecked = await getLastChecked();
  const afterDate = formatGmailDate(lastChecked);

  // Gmail 검색 쿼리: 최근 수신된 보안코드 관련 메일
  const query = `after:${afterDate} (인증 OR 보안코드 OR verification OR "security code" OR OTP OR "one-time")`;

  let messages;
  try {
    messages = await listMessages(token, query, 20);
  } catch (e) {
    if (e.message === 'AUTH_EXPIRED') {
      try {
        token = await getAuthToken(false);
        messages = await listMessages(token, query, 20);
      } catch {
        return;
      }
    } else {
      console.error('[SecureCode] Gmail 조회 오류:', e);
      return;
    }
  }

  await setLastChecked(Date.now());

  for (const { id } of messages) {
    try {
      const msg = await getMessage(token, id);
      const receivedAt = getReceivedAt(msg);

      // 이미 확인한 메일 제외
      if (receivedAt <= lastChecked) continue;

      const subject = getSubject(msg);
      if (!isSecurityCodeEmail(subject)) continue;

      const body = getBody(msg);
      const code = extractSecurityCode(body);

      if (!code || !isValidCode(code)) continue;

      console.log(`[SecureCode] 코드 발견: ${code} (제목: ${subject})`);

      // 대기 코드 저장
      await setPendingCode({ code, source: subject, extractedAt: Date.now() });

      // 알림 표시
      if (notifyOnDetect) {
        showNotification(code, subject);
      }

      // 자동 입력
      if (autoFill) {
        await injectCodeToActiveTab(code);
      }

      break; // 첫 번째 발견된 코드만 처리
    } catch (e) {
      console.error('[SecureCode] 메시지 처리 오류:', e);
    }
  }
}

// ─── 콘텐츠 스크립트로 코드 주입 ─────────────────────────────────────────

async function injectCodeToActiveTab(code) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  try {
    await chrome.tabs.sendMessage(tab.id, { type: 'AUTO_FILL', code });
  } catch {
    // 콘텐츠 스크립트가 없는 탭 (chrome://, about: 등) — 무시
    console.log('[SecureCode] 현재 탭에 입력 불가');
  }
}

// ─── 알림 ────────────────────────────────────────────────────────────────

function showNotification(code, subject) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '../icons/icon48.png',
    title: 'SecureCode: 보안코드 감지',
    message: `코드 ${code} 를 자동 입력합니다.\n출처: ${subject}`,
    priority: 2,
  });
}

// ─── 유틸 ─────────────────────────────────────────────────────────────────

/**
 * Gmail after: 파라미터용 날짜 포맷 (YYYY/MM/DD)
 * @param {number} timestamp
 * @returns {string}
 */
function formatGmailDate(timestamp) {
  const d = new Date(timestamp);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}/${m}/${day}`;
}
