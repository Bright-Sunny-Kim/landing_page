# HyeAn_DSKim (회계법인 혜안 고객 포털) 프로젝트 마스터 문서

본 문서는 `hyean-dskim.com` 웹사이트 프로젝트의 전체적인 아키텍처, 기능, 기술 스택, 데이터베이스 구조 및 최근 진행된 고도화 사항을 요약한 **프로젝트 인수인계/컨텍스트 마스터 파일**입니다. 새로운 AI 챗봇 창이나 다른 개발 환경에서 본 문서를 프롬프트로 제공하면, 이전까지의 작업 내역을 완벽하게 이해하고 매끄럽게 이어서 작업할 수 있습니다.

---

## 1. 프로젝트 개요 및 기술 스택
- **프로젝트 명**: 회계법인 혜안 파트너스 포털 (HyeAn_DSKim)
- **주요 목적**: 기업 파트너(고객)가 로그인하여 세무/회계 자문 요청 및 파일을 업로드하고, 최고 관리자(Master)가 이를 상태별로 관리 및 다운로드할 수 있는 B2B 포털
- **프레임워크**: Python / Flask (버전 3.0.0 이상)
- **배포 환경**: Render 클라우드 (Web Service, `gunicorn` 사용)
- **도메인**: `https://hyean-dskim.com`
- **데이터베이스 및 스토리지**: Supabase (PostgreSQL 호환, pgvector 확장 사용)
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
  - **고객 전용 사이드바 레이아웃**: 홈(자료 제출), 제출 내역 조회, 담당 회계사 문의(AI FAQ), 수수료 청구/결제, 내 정보 설정의 5가지 메뉴 구성.
  - **비동기 가상 탭 렌더링**: 메뉴 클릭 시 화면 전환 없이 탭 형태로 렌더링 (`main.js`). (기타 메뉴는 기능 준비 중 목업 화면 표출)
  - **다중 파일 및 Drag & Drop 업로드**: 각 서류 항목별로 여러 개의 파일을 드래그 앤 드롭으로 동시에 첨부 가능. 첨부 시 "N개 파일 선택됨" 안내 문구 동적 표출.
- `POST /submit-request` : 고객이 작성한 문의 내용(`help_text`)과 다중 첨부파일(`files`)을 Supabase Storage에 개별 파일로 안전하게 업로드하고 DB에 각각 저장.
- `POST /api/faq/ask` : **[Phase 2 완료]** AI 회계기준 어시스턴트(FAQ) 챗봇 백엔드 라우트. `text-embedding-3-large`로 질문을 임베딩하고 HNSW 검색을 거쳐 `gpt-4o-mini`가 전문적인 답변과 출처를 반환.

### 👑 마스터(최고 관리자) 전용 페이지
- **마스터 접속 계정**: `cpaeastsun@gmail.com`
- `GET /master` : 모든 파트너사 목록과 업로드 통계를 한눈에 보는 관리자 대시보드 (`master.html`).
  - **10대 통합 관리 사이드바**: 대시보드 홈, 파트너사 관리, 업무 요청 관리, 통합 문서 보관함, 공지 및 알림 관리, 세무 일정 캘린더, 실시간 자문 상담, 수수료 및 청구 관리, 시스템 통계 및 리포트, 포털 시스템 설정.
  - **비동기 가상 탭 렌더링**: 대시보드 홈 / 파트너사 관리 외 8개 메뉴 클릭 시, 화면 전환 없이 우측 영역에 해당하는 목업 안내 카드가 동적으로 렌더링됨 (`main.js`).
  - **파트너사 관리 고도화**: 요청 업무별 드롭다운 필터링, 파트너사별 파일 업로드율(%) 진행률 바 표시 및 클릭 시 상세 페이지 다이렉트 이동 기능 포함.
- `GET /master/<company_name>` : 특정 파트너사가 업로드한 파일 및 요청 사항 상세 내역 조회 (`master_detail.html`).
  - 상세 관리 도중 사이드바 메뉴 클릭 시 목록 페이지(`/master`)로 자동 리다이렉트 및 탭 활성화 분기 처리.
- `POST /update-status` : 개별 요청 건의 처리 상태(`대기중`, `처리중`, `완료`)를 비동기(AJAX)로 업데이트.

### 📊 AI 감사 자동화 API
- `POST /master/audit-analyze/<string:company_name>` : **회사 종합 AI 감사 위험 분석 API**.
  - 해당 피감사인이 올린 모든 시산표(T/B) 데이터프레임을 다운로드 및 순차 파싱하여 일괄 병합합니다.
  - 종합 변동성(Vertical/Horizontal) 분석을 가동하여 Outlier 계정을 식별하고 K-GAAP RAG 비교 매칭을 통해 완성도 높은 3단계('감사 목표 - 수행 절차 - 감사 결과 및 결론') 구조의 감사 조서 마크다운 문서를 합성합니다.

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
| `created_at` | timestamp | 데이터 생성(업로드) 일시 |
| `status` | text | 업무 진행 상태 (기본값: '대기중' / '처리중' / '완료') |

### 🧠 RAG 벡터 지식베이스 테이블 (`public.document_chunks`)
회계/감사 기준서 원문 PDF를 텍스트로 분할하고 임베딩하여 저장하는 벡터 테이블입니다.
| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `id` | int8 (PK) | 고유 식별키 (BigSerial) |
| `document_id` | text | 기준서 파일명 (예: K-GAAP_재고자산) |
| `category` | text | **[Phase 2 추가]** 6대 기준 분류 (예: 일반기업회계기준, K-IFRS 등) |
| `article_name` | text | 조항명 (예: 제10조) |
| `chunk_text` | text | 파싱된 텍스트 원문 (1개 조항 단위) |
| `embedding` | vector(1536) | OpenAI `text-embedding-3-large` 기반 1536차원 벡터 |
| `created_at` | timestamp | 적재 일시 |

> **HNSW 인덱스 및 필터링 적용**: 검색 속도 최적화를 위한 HNSW 인덱스가 걸려 있으며, `match_document_chunks` RPC 함수를 통해 `category`별 독립적 필터링 유사도 검색을 지원합니다.

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


## [2026-06-16] AI 회계기준 어시스턴트(RAG) 고도화 및 버그 수정


## [2026-06-16] AI 회계기준 어시스턴트(RAG) 고도화 및 버그 수정
- **앱 백엔드 ( pp.py)**: /api/faq/ask 라우트에서 OpenAI 및 Supabase 클라이언트 지연 초기화 적용. 프롬프트를 결론-설명-출처 구조로 개선.
- **문서 파싱 (chunker_standards.py)**: 회계기준서 청킹 정규식을 정교화하여 날짜/수식 오인식 방지. 8192 토큰 제한 초과 방지를 위해 3000자 초과 청크 자동 분할.
- **문서 업로드 (process_local_pdfs.py)**: 한글(Non-ASCII) 문자열로 인한 Supabase InvalidKey 에러 해결을 위해 카테고리 영문화 및 영문+해시 파일명 변환 적용.
- **UI 변경 (company.html)**: 담당 회계사 문의 탭 이름을 AI 회계사 문의로 변경.


## [2026-06-16] K-IFRS 문단 분할(Chunking) 고도화 적용
- **K-IFRS 정규식 추가 (chunker_standards.py)**: 1, 102A, 한1, B1, IE1 등 K-IFRS 고유의 복잡한 문단 번호 패턴을 완벽히 인식하여 분할하도록 ifrs_pattern 적용.
- **카테고리 연동 (process_local_pdfs.py)**: 문서의 카테고리 정보(category)를 Chunker 모듈로 전달하여, K-GAAP과 K-IFRS가 각각 자신에게 맞는 정규식을 동적으로 선택하도록 개선.


## [2026-06-16] K-IFRS 폴더 및 카테고리 병합 적용
- **폴더 구조 단순화**: 기존 한국채택국제회계기준(K-IFRS)(시행중) 및 (조기적용가능) 폴더를 한국채택국제회계기준(K-IFRS) 단일 폴더로 통합.
- **카테고리 매핑 수정 (process_local_pdfs.py)**: 스크립트가 단일 통합 폴더를 정상 인식하고 K-IFRS 영문 스토리지 경로로 업로드하도록 CATEGORIES 및 CATEGORY_MAP 설정 업데이트.

## [2026-06-16] Open DART 감사보고서 크롤링 파이프라인 구축 및 챗봇 고도화
- **DB 스키마 구성**: Supabase에 감사보고서 메타데이터 저장을 위한 `dart_audit_reports` 테이블과 본문 파싱 청크를 담는 `dart_report_chunks` 테이블 및 HNSW 벡터 인덱스를 설계(`database` 디렉토리 내 `.sql` 파일).
- **크롤러 및 파서 스크립트 구축**: 
  - `scripts/dart_crawler.py`: `requests`를 사용해 Open DART의 "회계감사인의 명칭 및 감사의견" API를 호출, `adtor` 등 변경된 메타데이터를 정합성 있게 매핑하여 DB에 Upsert.
  - `scripts/dart_document_parser.py`: DART `document.xml` 공시 원본(ZIP)을 내려받아 `BeautifulSoup4` 및 `lxml`로 텍스트 파싱, Overlap 기반 Chunking 및 OpenAI `text-embedding-3-large` 임베딩 후 `dart_report_chunks`에 적재.
- **챗봇 프롬프트 및 에러 픽스 (`app.py`)**: 
  - `PGRST203` Overload 오류 해결을 위해 '전체' 카테고리 검색 시 명시적으로 `filter_category: None` 전달 로직 추가.
  - AI 챗봇이 시각적으로 명확한 `[결론]`, `[상세 설명]`, `[관련 근거(조항)]` 마크다운 템플릿으로 답변하도록 시스템 프롬프트 업데이트 완료.
- **UI 개선 (`templates/company.html`)**: K-IFRS '시행중', '조기적용가능' 셀렉트 옵션을 `한국채택국제회계기준(K-IFRS)` 단일 항목으로 통합.

## [2026-06-18] 홈페이지 메인 랜딩 페이지 및 인증 흐름 전면 고도화
- **인트로 페이지(`intro.html`) 원페이지 스크롤 전환**: 
  - 홈, 주요업무, 팀, 실적, Contact(문의) 섹션 신설 및 `scroll-behavior: smooth` 적용.
  - 상단 고정 네비게이션(Sticky Nav)에 각 섹션별 바로가기 앵커(`#services`, `#team`, `#track-record`, `#contact`) 추가.
  - CEO 프로필(`profile.html`) 별도 페이지 생성 및 통합 네비게이션 연동.
- **프로필(`profile.html`) 사명(Mission) 업데이트**: 
  - "첨단 데이터 분석 기술과 깊이 있는 회계·세무 전문성으로 고객의 투명한 미래와 지속가능한 성장을 견인하겠습니다."로 대표 슬로건 변경.
- **로그인 로직 및 폼 검증 개선 (`login.html`, `main.js`)**:
  - 처음 접속 시에도 비밀번호 입력 칸과 '로그인 상태 유지' 체크박스가 기본적으로 노출되도록 UI/스크립트 개선.
  - 로그인 상태 유지 체크 여부에 따라 브라우저(로컬스토리지)에 이메일 정보 저장 동작 명확화.
- **인증 및 전역 보안 처리 (`app.py`, 전역 템플릿)**:
  - 템플릿 상단 내비게이션 바에 세션 접속 여부에 따른 '로그인', '로그아웃', '내 페이지로 이동' 동적 렌더링.
  - 브라우저 캐시에 기인한 보안 취약점 방지를 위해, 로그아웃 후 뒤로가기를 눌러도 접근 불가하도록 `@app.after_request`에 전역 `no-cache`, `no-store` HTTP 헤더 적용 완료.
