# HyeAn_DSKim (회계법인 혜안 고객 포털) 프로젝트 마스터 문서

본 문서는 `hyean-dskim.com` 웹사이트 프로젝트의 전체적인 아키텍처, 기능, 기술 스택, 데이터베이스 구조 및 최근 진행된 고도화 사항을 요약한 **프로젝트 인수인계/컨텍스트 마스터 파일**입니다. 새로운 AI 챗봇 창이나 다른 개발 환경에서 본 문서를 프롬프트로 제공하면, 이전까지의 작업 내역을 완벽하게 이해하고 매끄럽게 이어서 작업할 수 있습니다.

---

## 1. 프로젝트 개요 및 기술 스택
- **프로젝트 명**: 회계법인 혜안 파트너스 포털 (HyeAn_DSKim)
- **주요 목적**: 기업 파트너(고객)가 로그인하여 세무/회계 자문 요청 및 파일을 업로드하고, 최고 관리자(Master)가 이를 상태별로 관리 및 다운로드할 수 있는 B2B 포털
- **프레임워크**: Python / Flask (버전 3.0.0 이상)
- **배포 환경**: Render 클라우드 (Web Service, `gunicorn` 사용)
- **도메인**: `https://hyean-dskim.com`
- **데이터베이스 및 스토리지**: Supabase (PostgreSQL 호환)
- **디자인 테마**: Glassmorphism (유리 질감), 오로라 보라색 포인트 (`#a78bfa`, `#6366f1`)
- **브랜드 로고**: 혜안 공식 로고 이미지를 다크 모드용 투명 화이트 마스크(`logo_light.png`)로 가공 반영 및 Portal, Admin, Partner 서브 배지 텍스트 조합 적용
- **모바일 최적화**: PWA(Progressive Web App) 적용 완료 및 미디어 쿼리(992px 이하) 기반 모바일 메뉴 슬라이더 최적화 완료

---

## 2. 주요 기능 및 라우팅 구조 (`app.py`)

### 🔑 인증 및 진입점
- `GET /` : 로그인 페이지 (`login.html`). 이메일 입력 시 DB 조회 후 기존 고객/신규 고객 판별.
- `POST /check-email` : AJAX 통신을 통해 이메일 존재 여부 및 비밀번호 설정 상태를 실시간 확인.
- `POST /login` : 일반/마스터 로그인 수행. 비밀번호 해싱(`werkzeug.security` pbkdf2) 검증 및 최초 로그인 시 자동 암호화 마이그레이션 적용. 로그인 상태 유지(Remember Me) 체크 시 30일 반영.
- `POST /login/social` : Google / Naver 모의 소셜 간편 로그인 및 신규 정보 동적 수집 모달 대응.
- `GET /logout` : 세션 삭제 및 로그인 페이지로 이동.

### 💼 파트너(고객) 전용 페이지
- `GET /company/<company_name>` : 로그인 성공 시 진입하는 고객 전용 웰컴 대시보드 (`company.html`).
- `POST /submit-request` : 고객이 작성한 문의 내용(`help_text`)과 첨부파일(`file`)을 Supabase Storage에 업로드하고 DB에 저장 (안전한 영문/숫자 폴더 트리 생성).

### 👑 마스터(최고 관리자) 전용 페이지
- **마스터 접속 계정**: `cpaeastsun@gmail.com`
- `GET /master` : 모든 파트너사 목록과 업로드 통계를 한눈에 보는 관리자 대시보드 (`master.html`).
  - **10대 통합 관리 사이드바**: 대시보드 홈, 파트너사 관리, 업무 요청 관리, 통합 문서 보관함, 공지 및 알림 관리, 세무 일정 캘린더, 실시간 자문 상담, 수수료 및 청구 관리, 시스템 통계 및 리포트, 포털 시스템 설정.
  - **비동기 가상 탭 렌더링**: 대시보드 홈 / 파트너사 관리 외 8개 메뉴 클릭 시, 화면 전환 없이 우측 영역에 해당하는 목업 안내 카드가 동적으로 렌더링됨 (`main.js`).
- `GET /master/<company_name>` : 특정 파트너사가 업로드한 파일 및 요청 사항 상세 내역 조회 (`master_detail.html`).
  - 상세 관리 도중 사이드바 메뉴 클릭 시 목록 페이지(`/master`)로 자동 리다이렉트 및 탭 활성화 분기 처리.
- `POST /update-status` : 개별 요청 건의 처리 상태(`대기중`, `처리중`, `완료`)를 비동기(AJAX)로 업데이트.

---

## 3. 데이터베이스(Supabase) 스키마

### 👥 회원 테이블 (`public.users`)
| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `email` | text (PK) | 사용자(고객/관리자) 이메일 주소 |
| `company` | text | 파트너사(기업) 명 |
| `username` | text | 담당자 이름 |
| `task_type` | text | 담당 주요 업무 타입 (세무 자문, 회계감사 등) |
| `password` | text | PBKDF2 암호화 해시 문자열 (소셜 가입은 `OAUTH:provider` 저장) |
| `created_at` | timestamp | 회원 등록 일시 |

### 📂 요청 및 파일 보관 테이블 (`public.company_files`)
첨부파일 원본은 Supabase Storage 버킷(`company-uploads`)에 보안 저장됩니다.
| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `id` | int8 (PK) | 고유 식별키 |
| `uploaded_by` | text | 파일 업로드 담당자 이메일 주소 (users 테이블 email 참조) |
| `company_name` | text | 파트너사(기업) 명 |
| `file_name` | text | 원본 파일명 |
| `file_url` | text | Supabase Storage 내 파일 업로드 경로 |
| `help_text` | text | 고객이 작성한 문의 내용 / 요청 사항 |
| `created_at` | timestamp | 데이터 생성(업로드) 일시 |
| `status` | text | 업무 진행 상태 (기본값: '대기중' / '처리중' / '완료') |

---

## 4. 프론트엔드 및 PWA 구성 요소
- **스타일링**: `static/css/style.css` (CSS Variables 기반 프리미엄 Glassmorphism 스타일, 오로라 빛 광원 효과, 사이드바 레이아웃, 모바일 992px 반응형 슬라이드 칩셋 메뉴 스타일 포함)
- **자바스크립트**: `static/js/main.js` (실시간 이메일/비밀번호 동적 폼 제어, 모의 OAuth 로그인 모달 처리, 10대 메뉴 비동기 목업 인젝션, PWA 서비스 워커 관리)
- **에셋 및 로고**: 
  - `static/images/logo_light.png` : 흰색 투명화 가공된 공식 로고 이미지
  - `static/images/logo_transparent.png` : 남색 배경 투명화 공식 로고 이미지
  - `static/manifest.json` : PWA 설정 파일
  - `static/sw.js` : PWA 서비스 워커 파일
  - `static/icons/icon-512x512.svg` : PWA 앱 아이콘 로고

---

## 5. 환경 변수 (Environment Variables)
* `SUPABASE_URL` : Supabase 프로젝트 URL
* `SUPABASE_KEY` : Supabase API Key
* `FLASK_SECRET_KEY` : 플라스크 세션 암호화를 위한 시크릿 키

---

> **[배포 및 변경 사항 관리 참고 사항]** 
> 본 프로젝트는 GitHub 저장소의 `main` 브랜치와 Render.com 웹 서비스 빌드 파이프라인이 자동 연동되어 있습니다. 코드 수정 시 `git commit` 및 `git push origin main`을 실행하면 수 분 내에 실서버(`hyean-dskim.com`)로 자동 업데이트 배포됩니다.
