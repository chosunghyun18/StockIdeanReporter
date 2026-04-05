/**
 * Popup UI 로직
 */

import {
  getAccounts,
  addAccount,
  removeAccount,
  getPendingCode,
  getLastChecked,
  getSettings,
  saveSettings,
} from '../utils/storage.js';
import { getAuthToken, getProfileEmail } from '../utils/gmail-api.js';

// ─── DOM 참조 ─────────────────────────────────────────────────────────────

const statusBadge = document.getElementById('status-badge');
const lastCheckedText = document.getElementById('last-checked-text');
const codeSection = document.getElementById('code-section');
const detectedCode = document.getElementById('detected-code');
const codeSource = document.getElementById('code-source');
const accountList = document.getElementById('account-list');
const btnAddAccount = document.getElementById('btn-add-account');
const btnCopy = document.getElementById('btn-copy');
const btnFill = document.getElementById('btn-fill');
const btnPoll = document.getElementById('btn-poll');
const toggleAutoFill = document.getElementById('toggle-auto-fill');
const toggleNotify = document.getElementById('toggle-notify');
const selectInterval = document.getElementById('select-interval');

// ─── 초기화 ───────────────────────────────────────────────────────────────

async function init() {
  await renderAccounts();
  await renderPendingCode();
  await renderLastChecked();
  await renderSettings();
  bindEvents();
}

// ─── 렌더링 ───────────────────────────────────────────────────────────────

async function renderAccounts() {
  const accounts = await getAccounts();
  accountList.innerHTML = '';

  if (accounts.length === 0) {
    accountList.innerHTML = '<li class="empty-state">연결된 계정이 없습니다</li>';
    setStatus('idle');
    return;
  }

  setStatus('active');
  for (const { email } of accounts) {
    const li = document.createElement('li');
    li.className = 'account-item';
    li.innerHTML = `
      <span class="account-email">${escapeHtml(email)}</span>
      <button class="btn btn--sm" data-remove="${escapeHtml(email)}">삭제</button>
    `;
    accountList.appendChild(li);
  }

  // 삭제 버튼 이벤트
  accountList.querySelectorAll('[data-remove]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await removeAccount(btn.dataset.remove);
      await renderAccounts();
    });
  });
}

async function renderPendingCode() {
  const pending = await getPendingCode();
  if (!pending) {
    codeSection.classList.add('hidden');
    return;
  }

  // 5분 이내 코드만 표시
  const age = Date.now() - pending.extractedAt;
  if (age > 5 * 60 * 1000) {
    codeSection.classList.add('hidden');
    return;
  }

  codeSection.classList.remove('hidden');
  detectedCode.textContent = pending.code;
  codeSource.textContent = `출처: ${pending.source}`;
  setStatus('detected');
}

async function renderLastChecked() {
  const ts = await getLastChecked();
  const date = new Date(ts);
  lastCheckedText.textContent = `마지막 확인: ${formatTime(date)}`;
}

async function renderSettings() {
  const settings = await getSettings();
  toggleAutoFill.checked = settings.autoFill;
  toggleNotify.checked = settings.notifyOnDetect;
  selectInterval.value = String(settings.pollIntervalSec);
}

// ─── 이벤트 ───────────────────────────────────────────────────────────────

function bindEvents() {
  // Gmail 계정 연결
  btnAddAccount.addEventListener('click', async () => {
    btnAddAccount.textContent = '연결 중...';
    btnAddAccount.disabled = true;
    try {
      const token = await getAuthToken(true);
      const email = await getProfileEmail(token);
      await addAccount(email);
      await renderAccounts();
    } catch (e) {
      alert(`계정 연결 실패: ${e.message}`);
    } finally {
      btnAddAccount.textContent = '+ Gmail 연결';
      btnAddAccount.disabled = false;
    }
  });

  // 코드 복사
  btnCopy.addEventListener('click', async () => {
    const code = detectedCode.textContent;
    await navigator.clipboard.writeText(code);
    btnCopy.textContent = '복사됨!';
    setTimeout(() => { btnCopy.textContent = '복사'; }, 1500);
  });

  // 현재 페이지에 입력
  btnFill.addEventListener('click', async () => {
    const code = detectedCode.textContent;
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    try {
      const resp = await chrome.tabs.sendMessage(tab.id, { type: 'AUTO_FILL', code });
      if (resp?.filled) {
        btnFill.textContent = '입력 완료!';
        setTimeout(() => { btnFill.textContent = '현재 페이지에 입력'; }, 2000);
      } else {
        alert('입력 필드를 찾지 못했습니다. 인증 코드 입력란에 포커스 후 다시 시도하세요.');
      }
    } catch {
      alert('현재 페이지에서는 자동 입력이 불가합니다.');
    }
  });

  // 지금 확인
  btnPoll.addEventListener('click', async () => {
    btnPoll.textContent = '확인 중...';
    btnPoll.disabled = true;
    try {
      await chrome.runtime.sendMessage({ type: 'POLL_NOW' });
      await renderPendingCode();
      await renderLastChecked();
    } finally {
      btnPoll.textContent = '지금 확인';
      btnPoll.disabled = false;
    }
  });

  // 설정 변경
  toggleAutoFill.addEventListener('change', () =>
    saveSettings({ autoFill: toggleAutoFill.checked })
  );
  toggleNotify.addEventListener('change', () =>
    saveSettings({ notifyOnDetect: toggleNotify.checked })
  );
  selectInterval.addEventListener('change', () => {
    saveSettings({ pollIntervalSec: parseInt(selectInterval.value, 10) });
    chrome.runtime.sendMessage({ type: 'POLL_NOW' }); // 알람 재설정 트리거
  });
}

// ─── 유틸 ─────────────────────────────────────────────────────────────────

function setStatus(type) {
  statusBadge.className = `badge badge--${type}`;
  const labels = { idle: '대기 중', active: '모니터링 중', detected: '코드 감지!' };
  statusBadge.textContent = labels[type] || '대기 중';
}

function formatTime(date) {
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ─── 시작 ─────────────────────────────────────────────────────────────────

init();
