# HyeAn_DSKim (회계법인 혜안 고객 포털) 프로젝트 마스터 문서

본 문서는 `hyean-dskim.com` 웹사이트 프로젝트의 전체적인 아키텍처, 기능, 기술 스택 및 데이터베이스 구조를 요약한 **프로젝트 인수인계/컨텍스트 마스터 파일**입니다. 새로운 AI 챗봇 창이나 다른 개발 환경에서 본 문서를 프롬프트로 제공하면, 이전까지의 작업 내역을 완벽하게 이해하고 매끄럽게 이어서 작업할 수 있습니다.

---

## 1. 프로젝트 개요 및 기술 스택
- **프로젝트 명**: 회계법인 혜안 파트너스 포털 (HyeAn_DSKim)
- **주요 목적**: 기업 파트너(고객)가 로그인하여 세무/회계 자문 요청 및 파일을 업로드하고, 최고 관리자(Master)가 이를 상태별로 관리 및 다운로드할 수 있는 B2B 포털
- **프레임워크**: Python / Flask (버전 3.0.0 이상)
- **배포 환경**: Render 클라우드 (Web Service, `gunicorn` 사용)
- **도메인**: `https://hyean-dskim.com`
- **데이터베이스 및 스토리지**: Supabase (PostgreSQL 호환)
- **디자인 테마**: Glassmorphism (유리 질감), 오로라 보라색 포인트 (`#a78bfa`, `#6366f1`)
- **모바일 최적화**: PWA(Progressive Web App) 적용 완료 (설치 가능)

---

## 2. 주요 기능 및 라우팅 구조 (`app.py`)

### 🔑 인증 및 진입점
- `GET /` : 로그인 페이지 (`login.html`). 이메일 입력 시 DB 조회 후 기존 고객/신규 고객 판별.
- `POST /check-email` : AJAX 통신을 통해 이메일이 DB에 존재하는지 실시간 확인.
- `POST /login` : 세션(`session['email']`) 생성 후 대시보드로 리다이렉트. 신규 유저일 경우 DB에 최초 등록.
- `GET /logout` : 세션 삭제 및 로그인 페이지로 이동.

### 💼 파트너(고객) 전용 페이지
- `GET /company` : 로그인 성공 시 진입하는 고객 전용 웰컴 대시보드 (`company.html`).
- `POST /submit_request` : 고객이 작성한 문의 내용(`help_text`)과 첨부파일(`file`)을 Supabase Storage에 업로드하고 DB에 저장.

### 👑 마스터(최고 관리자) 전용 페이지
- **마스터 접속 계정**: `cpaeastsun@gmail.com` (해당 이메일로 로그인 시 마스터 권한 부여)
- `GET /master` : 모든 파트너사 목록과 업로드 통계를 한눈에 보는 관리자 대시보드 (`master.html`).
- `GET /master/<company_name>` : 특정 파트너사가 업로드한 파일 및 요청 사항 상세 내역 조회 (`master_detail.html`).
- `POST /update-status` : 개별 요청 건의 처리 상태(`대기중`, `처리중`, `완료`)를 비동기(AJAX)로 업데이트.

---

## 3. 데이터베이스(Supabase) 스키마

현재 모든 데이터는 Supabase의 `company_files` 테이블에서 관리되며, 첨부파일 원본은 Supabase Storage 버킷(`혜안_임시`)에 저장됩니다.

**테이블명**: `public.company_files`
| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `id` | int8 / UUID | 고유 식별키 (Primary Key) |
| `email` | text | 사용자(고객) 이메일 주소 |
| `username` | text | 담당자 이름 |
| `company` | text | 파트너사(기업) 명 |
| `task_type` | text | 주요 업무 타입 (세무, 기장 등) |
| `file_url` | text | Supabase Storage에 업로드된 파일 경로 |
| `help_text` | text | 고객이 작성한 문의 내용 / 요청 사항 |
| `created_at` | timestamp | 데이터 생성(업로드) 일시 |
| `status` | text | 업무 진행 상태 (기본값: '대기중' / '처리중' / '완료') |

---

## 4. 프론트엔드 및 PWA 구성 요소
- **스타일링**: `static/css/style.css` (CSS Variables를 활용한 중앙 집중식 테마 관리. TailwindCSS 미사용, 순수 Vanilla CSS 사용)
- **자바스크립트**: `static/js/main.js` (실시간 이메일 검증 로직, 파일 업로드 UI 피드백, 마스터 페이지의 상태 변경 비동기 로직, PWA 서비스 워커 등록)
- **PWA 에셋**: 
  - `static/manifest.json` : 앱 아이콘, 이름(`HyeAn_DSKim`), 테마 색상 정의.
  - `static/sw.js` : 브라우저 캐싱 등 기본 서비스 워커.
  - `static/icons/icon-512x512.svg` : 앱 아이콘 로고.

---

## 5. 환경 변수 (Environment Variables)
프로젝트 구동을 위해 클라우드(Render) 및 로컬 `.env` 파일에 반드시 설정되어야 하는 필수 변수들입니다.
* `SUPABASE_URL` : Supabase 프로젝트 URL
* `SUPABASE_KEY` : Supabase 익명/서비스 키
* `FLASK_SECRET_KEY` : 플라스크 세션 암호화를 위한 시크릿 키

---

> **[다음 작업 시 참고 사항]** 
> 현재 프로젝트는 로컬 PC 개발 -> GitHub Push -> Render 자동 배포로 이어지는 완전한 CI/CD 파이프라인이 구축되어 있습니다. 코드를 수정할 경우 반드시 `git push`를 통해 배포 서버에 변경 사항을 반영해야 합니다.
