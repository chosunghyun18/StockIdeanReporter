/**
 * Chrome storage 래퍼 — 계정 및 상태 관리
 */

const STORAGE_KEYS = {
  ACCOUNTS: 'registered_accounts',
  LAST_CHECKED: 'last_checked_timestamp',
  PENDING_CODE: 'pending_code',
  SETTINGS: 'settings',
};

/**
 * 등록된 이메일 계정 목록 조회
 * @returns {Promise<Array<{email: string, addedAt: number}>>}
 */
export async function getAccounts() {
  const result = await chrome.storage.local.get(STORAGE_KEYS.ACCOUNTS);
  return result[STORAGE_KEYS.ACCOUNTS] || [];
}

/**
 * 이메일 계정 등록
 * @param {string} email
 * @returns {Promise<void>}
 */
export async function addAccount(email) {
  const accounts = await getAccounts();
  const exists = accounts.some((a) => a.email === email);
  if (exists) return;
  accounts.push({ email, addedAt: Date.now() });
  await chrome.storage.local.set({ [STORAGE_KEYS.ACCOUNTS]: accounts });
}

/**
 * 이메일 계정 삭제
 * @param {string} email
 * @returns {Promise<void>}
 */
export async function removeAccount(email) {
  const accounts = await getAccounts();
  const filtered = accounts.filter((a) => a.email !== email);
  await chrome.storage.local.set({ [STORAGE_KEYS.ACCOUNTS]: filtered });
}

/**
 * 마지막 이메일 확인 시각 조회
 * @returns {Promise<number>} timestamp (ms)
 */
export async function getLastChecked() {
  const result = await chrome.storage.local.get(STORAGE_KEYS.LAST_CHECKED);
  // 기본값: 현재 시각 기준 5분 전
  return result[STORAGE_KEYS.LAST_CHECKED] || Date.now() - 5 * 60 * 1000;
}

/**
 * 마지막 이메일 확인 시각 저장
 * @param {number} timestamp
 * @returns {Promise<void>}
 */
export async function setLastChecked(timestamp) {
  await chrome.storage.local.set({ [STORAGE_KEYS.LAST_CHECKED]: timestamp });
}

/**
 * 추출된 보안코드 임시 저장 (자동입력 대기)
 * @param {{code: string, source: string, extractedAt: number} | null} data
 * @returns {Promise<void>}
 */
export async function setPendingCode(data) {
  await chrome.storage.local.set({ [STORAGE_KEYS.PENDING_CODE]: data });
}

/**
 * 대기 중인 보안코드 조회
 * @returns {Promise<{code: string, source: string, extractedAt: number} | null>}
 */
export async function getPendingCode() {
  const result = await chrome.storage.local.get(STORAGE_KEYS.PENDING_CODE);
  return result[STORAGE_KEYS.PENDING_CODE] || null;
}

/**
 * 설정 조회
 * @returns {Promise<{pollIntervalSec: number, autoFill: boolean, notifyOnDetect: boolean}>}
 */
export async function getSettings() {
  const result = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  return {
    pollIntervalSec: 30,
    autoFill: true,
    notifyOnDetect: true,
    ...result[STORAGE_KEYS.SETTINGS],
  };
}

/**
 * 설정 저장
 * @param {Partial<{pollIntervalSec: number, autoFill: boolean, notifyOnDetect: boolean}>} settings
 * @returns {Promise<void>}
 */
export async function saveSettings(settings) {
  const current = await getSettings();
  await chrome.storage.local.set({
    [STORAGE_KEYS.SETTINGS]: { ...current, ...settings },
  });
}
