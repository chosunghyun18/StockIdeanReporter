/**
 * Content Script — OTP 필드 감지 & 자동 입력
 * 모든 웹페이지에서 실행됨
 */

// ─── 메시지 수신 ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'AUTO_FILL') {
    const filled = fillOtpCode(message.code);
    sendResponse({ filled });
  }
});

// ─── OTP 필드 탐색 & 입력 ─────────────────────────────────────────────────

/**
 * 페이지에서 OTP 입력 필드를 찾아 코드를 입력
 * @param {string} code
 * @returns {boolean} 입력 성공 여부
 */
function fillOtpCode(code) {
  // 전략 1: 단일 OTP 입력 필드
  const singleField = findSingleOtpField();
  if (singleField) {
    fillInput(singleField, code);
    return true;
  }

  // 전략 2: 개별 자릿수 입력 필드 (6개 분리된 input)
  const digitFields = findDigitFields(code.length);
  if (digitFields.length === code.length) {
    digitFields.forEach((field, i) => fillInput(field, code[i]));
    return true;
  }

  // 전략 3: 자릿수 개수와 다를 때 — 활성화된 포커스 필드에 직접 입력
  const focused = document.activeElement;
  if (focused && isInputField(focused)) {
    fillInput(focused, code);
    return true;
  }

  return false;
}

/**
 * 단일 OTP 입력 필드 탐색
 * @returns {HTMLInputElement | null}
 */
function findSingleOtpField() {
  const otpKeywords = [
    '인증', '보안코드', '보안 코드', '인증코드', '인증번호', '확인코드',
    'otp', 'verification', 'security', 'code', 'token', 'passcode', 'pin',
  ];

  const inputs = Array.from(
    document.querySelectorAll('input[type="text"], input[type="number"], input[type="tel"], input:not([type])')
  );

  for (const input of inputs) {
    if (!isVisible(input)) continue;

    const attrs = [
      input.placeholder,
      input.name,
      input.id,
      input.getAttribute('aria-label'),
      input.getAttribute('autocomplete'),
    ].map((v) => (v || '').toLowerCase());

    // autocomplete="one-time-code" — 표준 OTP 속성
    if (input.getAttribute('autocomplete') === 'one-time-code') return input;

    const matched = otpKeywords.some((kw) => attrs.some((attr) => attr.includes(kw)));
    if (matched) return input;

    // 레이블 텍스트 확인
    const label = getAssociatedLabel(input);
    if (label && otpKeywords.some((kw) => label.toLowerCase().includes(kw))) {
      return input;
    }
  }

  return null;
}

/**
 * 개별 자릿수 입력 필드 탐색 (한국 사이트 등)
 * @param {number} codeLength
 * @returns {HTMLInputElement[]}
 */
function findDigitFields(codeLength) {
  const inputs = Array.from(
    document.querySelectorAll('input[type="text"], input[type="number"], input[type="tel"]')
  ).filter((input) => {
    if (!isVisible(input)) return false;
    const maxLen = parseInt(input.maxLength || '0', 10);
    return maxLen === 1;
  });

  // 연속된 그룹 찾기
  if (inputs.length === codeLength) return inputs;

  // 포커스된 필드 근처의 같은 그룹 찾기
  const focused = document.activeElement;
  if (focused && isInputField(focused)) {
    const parent = focused.closest('form, [class*="otp"], [class*="code"], [class*="pin"], [class*="verify"]');
    if (parent) {
      const groupInputs = Array.from(parent.querySelectorAll('input')).filter(isVisible);
      if (groupInputs.length === codeLength) return groupInputs;
    }
  }

  return [];
}

// ─── 입력 이벤트 발생 (React/Vue 호환) ──────────────────────────────────

/**
 * input 필드에 값을 입력하고 관련 이벤트를 발생시킴
 * React, Vue, Angular의 controlled input 모두 대응
 * @param {HTMLInputElement} input
 * @param {string} value
 */
function fillInput(input, value) {
  input.focus();

  // React controlled input 대응
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  )?.set;

  if (nativeInputValueSetter) {
    nativeInputValueSetter.call(input, value);
  } else {
    input.value = value;
  }

  // 이벤트 순서: input → change → keyup
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
}

// ─── DOM 유틸 ─────────────────────────────────────────────────────────────

function isInputField(el) {
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
}

function isVisible(el) {
  return !!(el.offsetParent || el.offsetWidth || el.offsetHeight)
    && window.getComputedStyle(el).visibility !== 'hidden'
    && window.getComputedStyle(el).display !== 'none';
}

function getAssociatedLabel(input) {
  // for 속성 연결
  if (input.id) {
    const label = document.querySelector(`label[for="${input.id}"]`);
    if (label) return label.textContent;
  }
  // 부모 label
  const parentLabel = input.closest('label');
  if (parentLabel) return parentLabel.textContent;

  return null;
}
