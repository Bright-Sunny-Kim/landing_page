
## 최근 아키텍처 및 파이프라인 업데이트 (2026-06-25)

## 추가 업데이트 (2026-06-26)
1. **LlamaParse API 한도 예외 처리 강화**
   - 무료 API 한도 초과 시 빈 데이터(0 청크)를 반환하는 LlamaParse의 동작을 캐치하여, 성공으로 잘못 기록되지 않고 '실패(API 한도 초과)'로 parse_tracker.json에 정확히 기록되도록 process_llama_parse.py의 에러 핸들링을 강화했습니다.
2. **윈도우 자동 스케줄링 (Cron Job)**
   - LlamaParse 일일 한도 초기화 시간(한국 시간 오후 5시)을 고려하여, 매일 오후 6시(18:00)에 백그라운드에서 자동으로 파싱 스크립트를 실행하는 
un_parser.bat를 구성했습니다.
   - 윈도우의 작업 스케줄러(Task Scheduler)에 LlamaParse_Daily_Job으로 등록 완료했으며, 실행 결과는 parser_cron.log에 자동 기록됩니다.
1. **RAG 파이프라인 고도화 (LlamaParse 도입)**
   - 기존의 단순 텍스트 추출 한계를 극복하기 위해 llama-parse 및 langchain-text-splitters를 도입했습니다.
   - 복잡한 표(Table)와 마크다운 헤더 구조를 완벽하게 유지하며 의미 단위(Chunk)로 분할합니다.
   - 무료 티어 API 한도를 고려하여 매일 한정된 파일만 처리하도록 parse_tracker.json을 통한 점진적 파싱(Incremental Parsing)을 구현했습니다 (scripts/rag_pipeline/process_llama_parse.py).
2. **벡터 DB 이전 (ChromaDB)**
## 최근 아키텍처 및 파이프라인 업데이트 (2026-06-25)

## 추가 업데이트 (2026-06-26)
1. **LlamaParse API 한도 예외 처리 강화**
   - 무료 API 한도 초과 시 빈 데이터(0 청크)를 반환하는 LlamaParse의 동작을 캐치하여, 성공으로 잘못 기록되지 않고 '실패(API 한도 초과)'로 parse_tracker.json에 정확히 기록되도록 process_llama_parse.py의 에러 핸들링을 강화했습니다.
2. **윈도우 자동 스케줄링 (Cron Job)**
   - LlamaParse 일일 한도 초기화 시간(한국 시간 오후 5시)을 고려하여, 매일 오후 6시(18:00)에 백그라운드에서 자동으로 파싱 스크립트를 실행하는 
un_parser.bat를 구성했습니다.
   - 윈도우의 작업 스케줄러(Task Scheduler)에 LlamaParse_Daily_Job으로 등록 완료했으며, 실행 결과는 parser_cron.log에 자동 기록됩니다.
1. **RAG 파이프라인 고도화 (LlamaParse 도입)**
   - 기존의 단순 텍스트 추출 한계를 극복하기 위해 llama-parse 및 langchain-text-splitters를 도입했습니다.
   - 복잡한 표(Table)와 마크다운 헤더 구조를 완벽하게 유지하며 의미 단위(Chunk)로 분할합니다.
   - 무료 티어 API 한도를 고려하여 매일 한정된 파일만 처리하도록 parse_tracker.json을 통한 점진적 파싱(Incremental Parsing)을 구현했습니다 (scripts/rag_pipeline/process_llama_parse.py).
2. **벡터 DB 이전 (ChromaDB)**
   - 로컬 SQLite/pgvector 구조에서 Ubuntu Home Server에 배포된 ChromaDB로 마이그레이션했습니다.
   - 분산 환경 및 대용량 청크를 안정적으로 처리할 수 있도록 embedder_standards.py를 리팩토링했습니다.
3. **디렉토리/메타데이터 영어화**
   - 기준서 폴더명 및 파일 분류 메타데이터의 한글 의존성(인코딩 에러)을 해결하기 위해 K-IFRS, K-GAAP, SME-GAAP, NPO-GAAP, SPC-GAAP, K-GAAS 등 영문 약자로 구조를 개편했습니다.
   - 사용자 편의를 위해 UI(company.html) 드롭다운은 한글로 표기하되, 서버 전달 시 영문으로 매핑되도록 처리했습니다.

## 최근 업데이트 (2026-07-14) - Ubuntu 단일 노드 마이그레이션 Phase 1~3 완료, Phase 4 사전 준비
> 상세 내역·트러블슈팅·다음 할 일: [migration_progress.md](./migration_progress.md) 참조 (이 항목은 요약)

1. **Phase 1 (Ubuntu Flask 배포) 완료**: `~/hyean-portal`에 소스 배포, Python 3.14 `ensurepip` 미탑재 이슈 우회, `sentence-transformers`의 GPU torch 대신 CPU 전용 torch로 전환 설치. Gunicorn + systemd 사용자 서비스(`hyean-portal-user`, linger 적용) 등록. `staging.hyean-dskim.com`을 NPM이 아닌 **Cloudflare Tunnel Public Hostname**으로 직결 노출.
2. **Phase 2 (Dify Cloud → 로컬 Dify) 완료**: 로컬 Dify(`dify.hyean-dskim.com`)로 앱 DSL Import, LLM Provider를 **Gemini**로 확인. 워크스페이스 단위인 Custom Tool("Hyean RAG Retrieval API")을 로컬에 재등록하고 `172.17.0.1:5000`(Docker 브리지)으로 연결. `app.py`의 Dify URL을 `DIFY_API_BASE_URL` 환경변수로 분리.
3. **Phase 3 (내부망 직결) 진행 중**: `CHROMA_SERVER_HOST=localhost` 직결 및 실데이터 검색 확인, FAQ Agent→Tool→ChromaDB 전체 체인 검증 완료. **24시간 soak test는 클라우드 스케줄(`hyean-portal-soak-test`)로 자동화**하여 매시간 헬스체크 후 2026-07-15 21:06 KST경 자동 종료. ngrok 중지(3-3)는 현재 프로덕션이 여전히 의존 중이라 **Phase 4 이후로 순서 조정**.
4. **Phase 4 사전 준비**: `hyean-dskim.com`과 `staging.hyean-dskim.com`이 동일 Cloudflare 엣지로 응답함을 확인 — 기존에 가정한 "DNS TTL 300초 대기" 방식이 아니라 **Cloudflare Tunnel Public Hostname 전환만으로 즉시 처리 가능**하다는 사실을 재발견. Render 환경변수를 백업·대조하고 `FLASK_SECRET_KEY`를 Render 값과 동일화하여 전환 후 세션 연속성 확보.
5. **다음 세션 할 일**: soak test 결과 확인 → Go/No-Go 잔여 2개 항목(저트래픽 시간대, 롤백 리허설) → Phase 4 실행 → 이후 [audit_master.md](./audit_master.md)의 감사 자동화 기능 로드맵으로 이어서 진행.

## 최근 업데이트 (2026-07-11) - Ubuntu 단일 노드 마이그레이션 Phase 1 착수
1. **마이그레이션 계획 수립 (Blue-Green 전략)**
   - Render + Windows ngrok + Dify Cloud + Ubuntu ChromaDB 분산 구조의 단점 분석 및 4단계 이전 로드맵 확정.
   - 상세 진행 현황: `docs/migration_progress.md`, `docs/analysis_results.md` 참조.
2. **Phase 1 사전 준비 (로컬 저장소)**
   - `requirements.txt`에 RAG 필수 패키지(`chromadb`, `cohere`, `requests`) 추가.
   - `server_setup/portal/` — Gunicorn systemd 유닛, 사용자 서비스, `.env.example`, `deploy.sh` 작성.
3. **Ubuntu 서버 사전 점검 (2026-07-11)**
   - SSH 원격 접속 확인 (`ssh.hyean-dskim.com`, cloudflared + id_server).
   - ChromaDB(:8000), Dify(:8090), MinIO, NPM, n8n, Nextcloud Docker 서비스 정상 가동 확인.
   - Flask Portal(:5000) 및 `/opt/hyean-portal` — **미배포** (Phase 1 잔여 작업).
4. **Phase 1 잔여 / Phase 2~4 예정**
   - Phase 1: Ubuntu에 Flask 배포, Gunicorn, staging.hyean-dskim.com 프록시.
   - Phase 2: Dify Cloud → 로컬 Dify(`dify.hyean-dskim.com`) 설정 이전, `app.py` Dify URL 환경변수화.
   - Phase 3: localhost ChromaDB 직결, ngrok 제거.
   - Phase 4: hyean-dskim.com DNS를 Render → Ubuntu로 전환 (예상 다운타임 5~15분).

# HyeAn_DSKim (회계법인 혜안 고객 포털) 프로젝트 마스터 문서

## 최근 업데이트 (2026-07-09) - 수수료 및 청구 관리 (문서 자동화) 연동 고도화
1. **문서 자동화 UI 및 로직 고도화**
   - 마스터 포털 사이드바에 "수수료 및 청구 관리 (Billing)" 메뉴를 연동하여 가상 탭 렌더링.
   - 새 견적서/제안서 작성 폼을 이력 테이블 상단으로 배치하여 UX 개선.
   - 문서 이력 목록은 최근 3개 항목만 표시되도록 제한하고, 각 항목 우측에 안전한 [삭제] 버튼 추가.
2. **백엔드 문서 처리 API 확장**
   - `app.py`에 `/api/billing/docs` (GET/POST/DELETE) 라우트를 신설하여 프론트엔드와 Supabase의 `documents`, `document_items` 테이블 간 CRUD 완벽 연동. (삭제 시 하위 아이템 CASCADE 대응 수동 삭제 포함)
3. **고품질 인쇄용 문서 템플릿(A4) 다중 페이지 분할 적용**
   - 브라우저 네이티브 `window.print()` 방식을 활용하여 레이아웃 쏠림 없는 모던 스타일 A4 인쇄용 HTML 템플릿 3종(`doc_quote.html`, `doc_proposal.html`, `doc_invoice.html`) 도입.
   - 서버 사이드(Jinja2)에서 표 항목을 정확히 3개 단위로 청크(`batch(3)`) 분할하여 다중 페이지(`page-break-after`) 렌더링 로직 구현.
   - 2번째 페이지부터는 불필요한 개요 영역을 자동으로 생략하여 넉넉한 공간을 확보하되, 상단 공통 헤더와 하단 대표이사 직인은 모든 장에 렌더링되도록 처리. 총 금액 및 입금 계좌는 알맞은 위치에 표출하여 전문성을 극대화.

## 최근 업데이트 (2026-07-04) - 서면조회서 발급 시스템 전면 개편
1. **PDF 렌더링 방식 전면 교체 (안정성 확보)**
   - 기존 html2pdf.js의 IFrame 렌더링 버그(레이아웃 쏠림 및 찌그러짐 현상)를 원천 차단하기 위해, 브라우저 네이티브 인쇄(window.print) 방식을 활용한 PDF 저장 방식으로 전면 개편.
   - 파이썬 템플릿 빌더(build_full_templates.py)를 통해 A4 사이즈에 완벽히 최적화된 HTML로 재작성.
2. **입력 UI 그룹화 및 자동 매핑 고도화**
   - UI 내 '회사 상세 정보' 구역을 신설하고 그 하단에 '수수료 환급계좌 정보'를 그룹화하여 직관성 향상.
   - '회계법인 상세 정보'를 별도 분리 후, 실제 데이터(회계법인 혜안, 사업자등록번호 등)를 고정 입력하고 읽기 전용(readonly) 속성을 부여해 임의 변경을 차단.
   - 유효기간(3개월) 자동계산 로직 추가.
3. **사용성 개선**
   - 양식 안내 모달 가이드 추가 및 미사용 서식(채권채무조회서) 완전 제거.


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
- `POST /master/audit-analyze/<string:company_name>` / `GET /company/audit-analysis/<string:company_name>` (2026-07-18 추가) : **회사 종합 AI 감사 위험 분석 API**. 두 라우트 모두 공통 함수 `_run_audit_analysis()`(`app.py`)를 공유.
  - 해당 피감사인이 올린 파일을 파일명(합계잔액시산표/재무상태표/손익계산서)으로 구분해 실제 회계프로그램 양식 그대로 파싱(`audit_engine.py`의 `parse_trial_balance_structured`/`parse_financial_statement`) → 대차평형 검증 + 시산표-재무제표 계정별 대사(`build_standard_statements`) 수행. 분류 안 되는 파일은 기존 키워드매칭 `parse_tb_file`로 폴백.
  - 종합 변동성(Vertical/Horizontal) 분석을 가동하여 Outlier 계정을 식별하고 K-GAAP RAG 비교 매칭을 통해 완성도 높은 3단계('감사 목표 - 수행 절차 - 감사 결과 및 결론') 구조의 감사 조서 마크다운 문서를 합성합니다.
  - `/master/...`는 실데이터가 없으면 모의데이터로 폴백하지만(내부 테스트용), `/company/...`(고객사 자체 열람, `company.html` "분석보고서" 탭)는 그렇게 하지 않고 자료 부족 시 안내만 반환 — DB에 저장하지 않는 읽기 전용 조회. 상세는 `docs/audit_master.md` 참조.

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

## [2026-06-19]   Űó MinIO ̱׷̼
- ** 丮 ȯ**:  뷮 (PDF, 繫ǥ) Ҹ  Supabase Storage  Ȩ  1TB ϵ(MinIO)  ̰.
- **DB и **: ȸ (users), ε Ÿ(company_files)   ؽƮ DB  Supabase  (̺긮 Űó).
- **̽  **: pp.py  dart_document_parser.py  oto3 ̺귯  MinIO company-uploads, parsed-data Ŷ    Parquet ͸ εϵ .


## [2026-06-22] Supabase DB RLS 보안 강화 및 법인등록번호 기반 소속 자동 그룹화
- **Supabase RLS 설정**: users, company_files 등 주요 테이블에 대해 RLS(Row Level Security)를 활성화하여 외부 anon 접근을 원천 차단하고 Flask 백엔드(service_role)만을 통한 안전한 접근 구조 보장.
- **법인등록번호 기반 매핑**: users 테이블에 corporate_number 추가. 신규 가입 시 000000-0000000 형식의 유효성 검증을 거쳐 법인번호를 필수 수집.
- **오타 자동 교정 및 그룹화**: 동일 법인번호로 가입 시, 사용자가 회사명에 오타를 내더라도 DB에 기존 등록된 정확한 회사명으로 강제 교정하여 소속 파트너사 데이터를 완벽하게 그룹화.
- **프론트엔드 UI 수정 (login.html, main.js, style.css)**: 신규 가입 폼 및 소셜 간편 로그인 모달에 법인등록번호 필드 추가 및 애니메이션 영역(max-height) 확장 조정.

## [2026-06-23] 업종별 회계감사 자료 동적 제출 및 AI 문의 오류 수정
- **업종별 및 회계기준별 동적 자료 제출 UI 구현 (	emplates/company.html)**:
  - 제조업/도소매업, 금융/보험업, IT/소프트웨어, 건설업 중 업종을 선택할 수 있는 드롭다운 추가.
  - 일반기업회계기준, K-IFRS 중 적용 회계기준을 선택할 수 있는 드롭다운 추가.
  - 선택한 업종에 따라 기존 공통 서류 외에 재고자산수불부, 금융자산명세서, 무형자산명세서 등 11종의 특화 서류가 JavaScript 로직(updateDocumentList())을 통해 동적으로 표시되도록 고도화.
- **백엔드 업종 특화 자료 파싱 로직 확장 (pp.py)**:
  - /submit-request 엔드포인트에서 18개 서류 필드를 처리할 수 있도록 document_labels 매핑 확장.
  - 제출 시 사용자가 선택한 업종 및 회계기준 정보가 담당 회계사에게 전달되도록 help_text에 반영.
- **AI 회계사 문의 버그 수정**:
  - 서버 기동 시 환경변수 누락으로 인한 '서버의 AI 설정이 올바르지 않습니다' 오류를 파악하고, 에러 메시지를 구체화(Missing: openai, supabase 등)하여 디버깅을 용이하게 개선 및 재구동 완료.

## [2026-06-25] 파트너사 포털(제출 내역 조회 탭) 고도화 및 레이아웃 렌더링 버그 수정
- **UI 구조 결함 해결 (`company.html`)**: 이전 작업 중 '회계감사' 탭에서 서브 탭 컨테이너 닫힘 태그(`</div>`)가 누락되어 '제출 내역 조회' 및 'AI 회계사 문의' 탭 전체가 하위 요소로 잘못 종속(Nested)되던 버그를 해결. 원본 구조 복구 후 각 탭이 정상적인 형제(Sibling) 관계로 렌더링되도록 수정 (탭 클릭 시 빈화면 노출 현상 완벽 조치).
- **'제출 내역 조회' 탭 고도화 및 업로드 기능 통합 (`company.html`)**: 
  - 상단에 진척도(Progress) 요약 대시보드(퍼센트 게이지 바) 및 카테고리별 미제출 내역 리스트 표출.
  - 기존 '회계감사' 탭에 혼재되어 있던 항목별 자료 제출 기능(회사기본사항, 서면제출자료, 외부조회(금융/거래처))을 서브 탭 형태로 '제출 내역 조회' 탭 내부로 통합 이관하여 UX를 개선.
- **백엔드 분류/적재 로직 연동 (`app.py`)**: 
  - '제출 내역 조회' 탭 내의 새로운 단일 업로드 폼 형식(Hidden 필드로 Category 전달)을 파싱할 수 있도록 `company_upload` 로직 확장.
  - 제출된 카테고리와 세부 항목명(예: `current_fs`, `finance_bank_balance`)에 따라 `P-File`, `Temp/Temp_P`, `Temp/Temp_L`, `Ext_F`, `Ext_C` 명칭의 연도별(year_folder) 폴더 구조를 자동 판별하여 MinIO 및 DB에 맞춤형 적재 처리 구현 완료.

## [2026-06-26] 파트너사 포털 UI 구조 결함 완벽 복구 및 탭 전환 안정화
- **서면제출자료 탭 목록 증발 및 UI 깨짐 2차 복구 (company.html)**: 
  - '회사기본사항(P-file)' 서브 탭 및 '전체 제출 이력 타임라인' 영역(partner-history-view)의 HTML 닫힘 태그(</div>) 누락을 최종적으로 식별 및 추가.
  - 부모-자식 태그 종속 관계로 인해 switchSubTab 자바스크립트 실행 시 '서면제출자료' 탭의 리스트(테이블)가 통째로 display: none 처리되던 이슈를 완벽하게 해결. 
  - 중복 선언되어 있던 switchSubTab 함수를 정리하여 main.js의 공통 함수로 일원화 처리.

## [2026-06-26] 금융기관 조회업무 신청 시스템 구현 (고객/관리자 포털)
- **DB 스키마 구성**: financial_institutions, inquiry_requests, inquiry_status_logs 테이블 구축 완료.
- **백엔드 API 구현 (app.py)**: 관리자용 개별 상태 업데이트, 등기번호/메모 등록 API 및 엑셀 다운로드 API 구축. UTF-8 인코딩 헤더 추가.
- **고객 포털 UI 고도화**: 외부조회(금융기관) 서브 탭 내 단계별 3-Step 마법사(Wizard) 폼 도입 및 상태 요약 카드 대시보드 연동.
- **관리자 포털 UI 고도화**: 금융기관 조회 신청 관리 테이블, 일괄 상태 업데이트(Dropdown), Tracking 번호 및 Admin Note 입력, CSV 엑셀 다운로드 연동 완료.
