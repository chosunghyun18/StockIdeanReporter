# SecureCode Auto-Fill — Chrome Extension

이메일로 수신된 보안코드(OTP)를 웹페이지에 자동으로 입력해주는 Chrome 익스텐션.

## 주요 기능

- Gmail OAuth2 연동 (비밀번호 저장 없음)
- 이메일 주기적 폴링 (기본 30초)
- 한국어/영어 보안코드 패턴 자동 추출
- 웹페이지 OTP 입력 필드 자동 감지 & 입력
- React/Vue/Angular controlled input 호환
- 개별 자릿수 분리 입력 필드 지원 (한국 사이트)

## 설치 방법

### 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성
3. **API 및 서비스** → **라이브러리** → Gmail API 활성화
4. **OAuth 동의 화면** 설정 (외부, 테스트 사용자 추가)
5. **사용자 인증 정보** → **OAuth 2.0 클라이언트 ID** 생성
   - 유형: **Chrome 앱**
   - 확장 프로그램 ID 입력 (아래에서 확인)
6. 발급된 클라이언트 ID 복사

### 2. manifest.json 수정

```json
"oauth2": {
  "client_id": "발급받은_클라이언트_ID.apps.googleusercontent.com"
}
```

### 3. Chrome에 로드

1. `chrome://extensions` 접속
2. **개발자 모드** 활성화
3. **압축해제된 확장 프로그램 로드** → `chrome-extension/` 폴더 선택
4. 확장 프로그램 ID 확인 후 Google Cloud Console에 등록

## 사용 방법

1. 익스텐션 아이콘 클릭 → **+ Gmail 연결** 버튼
2. Google 계정 로그인 및 권한 승인
3. 이후 이메일로 보안코드 수신 시 자동 입력

## 폴더 구조

```
chrome-extension/
├── manifest.json          — MV3 매니페스트
├── background/
│   └── service-worker.js  — Gmail 폴링 & 코드 추출
├── content/
│   └── content.js         — OTP 필드 감지 & 자동 입력
├── popup/
│   ├── popup.html         — 팝업 UI
│   ├── popup.js           — 팝업 로직
│   └── popup.css          — 팝업 스타일
├── utils/
│   ├── gmail-api.js       — Gmail REST API 래퍼
│   ├── code-extractor.js  — 보안코드 추출 정규식
│   └── storage.js         — Chrome storage 래퍼
└── icons/                 — 아이콘 (16, 48, 128px)
```

## 보안

- OAuth2만 사용 (비밀번호 저장 없음)
- 이메일 본문은 저장하지 않음 (코드만 임시 저장, 5분 후 무효화)
- `chrome.storage.local` 사용 (외부 서버 전송 없음)
- Gmail 읽기 권한만 요청 (`gmail.readonly`)
