# 🏢 HEYAN 마스터 기업 정밀 분석 시스템 & CPA 회계감사 포털
> **Enterprise Financial Analytics & AI Audit Hub**

> **고객이 제출한 6대 회계자료(재무상태표, 손익계산서, 합계잔액시산표, 분개장, 거래처원장, 계정별원장)를 기반으로 한 [기업 정밀 분석 허브]와 K-GAAP 105개 엑셀 조서 RAG, 6대 장부 실시간 수치 대사, K-GAAS 700 표준 감사보고서 AI 생성을 지원하는 [CPA 회계감사 전용 포털]이 완벽히 통합된 차세대 종합 회계 감사 솔루션**

---

## 📌 1. 시스템 개요 및 주요 기능

본 시스템은 공인회계사 및 세무 전문가가 기업의 결산 서류와 회계 원장을 원클릭으로 정밀 진단하고 회계감사 조서 및 감사보고서를 완벽히 자동화할 수 있도록 구축된 **풀스택 감사/분석 엔진**입니다.

---

### 🏛️ [NEW] 회계법인 혜안 CPA AI 회계감사 전용 포털 (`/audit`)
회계사(`role='cpa'` / `task_type='회계감사'`) 로그인 시 마스터 포털을 거치지 않고 독립된 **회계감사 전용 작업장(Audit Hub)**으로 직접 라우팅(Direct Routing)되며, 5대 전문 업무 탭을 제공합니다.

1. **📑 1. 감사조서 작성 & AI 자동생성 (`#tab-audit-wp`)**:
   - **K-GAAP 조서 색인 계층형 아코디언 트리**: Section 1000(감사계약)부터 Section 8000(기타)까지 105개 표준 조서 서식을 섹션별 아코디언 형태로 정돈, 실시간 검색창 지원
   - **6대 장부 실시간 수치 대사 (Reconciliation Bar)**: TB 전기말 잔액, 당기말 잔액, 변동 금액/변동률, 장부 무결성 대사 상태를 실시간 연동
   - **AI 조서 자동생성**: 계정별 입증절차, 실재성/완전성/평가 검증 코멘트 및 회계감사 기준서 준용 조서를 마크다운으로 1초 만에 자동 작성
   - **K-GAAP 원본 서식 엑셀(`.xlsx`) 스트리밍 다운로드**: OpenPyXL 셀 좌표 바인딩을 통해 수식과 원본 셀 서식을 100% 보존한 엑셀 조서 파일 즉시 다운로드
   - **K-GAAS 기준서 & RAG 가이드**: 계정과목 선택 시 관련 감사 기준서와 필수 실증절차 지침 자동 표출

2. **📅 2. 감사일정 캘린더 (`#tab-audit-cal`)**:
   - **마일스톤 D-Day 카드**: 기초재고 실사, 기말감사 현장투입, 금융기관 조회서 마감, 감사보고서 초안, 주총 공시 마감 등 주요 마일스톤 D-Day 실시간 계산
   - **FullCalendar v6 다크 테마 인터랙티브 캘린더**: 월별/주별 일정 뷰, 일정 등록 모달 연동

3. **👥 3. 프로젝트 & 배정 관리 (`#tab-audit-assign`)**:
   - 수임 감사계약 현황, 담당 PM (In-charge), 투입 회계사, 감사 단계, 기준일 데이터 관리

4. **🏦 4. 금융기관 조회·증빙 (`#tab-audit-finance`)**:
   - 금융거래확인서, 은행/증권 잔액증명서 발송 및 회신 상태, 장부잔액 대사, 조회서 파일 조서 연계

5. **📄 5. 감사보고서 작성 & AI 초안 (`#tab-audit-report`)**:
   - **K-GAAS 700/701/705/706 표준 감사보고서 AI 자동생성**: 감사의견(적정/한정/부적정/의견거절), 재무제표 기준일, 발행일자, 핵심감사사항(KAM) 유무 선택
   - **핵심감사사항(KAM) 칩 원클릭 삽입**: 수익인식의 적정성, 재고자산 순실현가치 평가, 영업권 손상, 파생상품 평가 등 주요 위험 항목 즉시 문단 추가
   - **정식 A4 서식 인쇄/PDF 미리보기**: 실제 인쇄용 A4 규격 서식으로 렌더링되며 [인쇄 / PDF] 원클릭 지원

---

### 🌟 기업 정밀 분석 허브 (`/master`) 핵심 기능
1. **🚀 2대 전담 탭 원천 분리 아키텍처 (Decoupled Pipeline)**:
   - **`[📂 회계자료 수집 & 보관소]` (#tab-data-ingestion)**: 6대 장부 드래그앤드롭 업로드, 100% Python 결정론적 파싱, 대차 무결성 검증, 우분투/로컬 스토리지 시점별 영구 저장, 실시간 업로드 이력 관리 및 원본 ZIP 일괄 다운로드
   - **`[🧠 기업 정밀 분석 (Hub)]` (#tab-analytics-hub)**: 슬림 분석 컨트롤 바(`기업 선택 ➔ 결산연도 ➔ 시점 선택 ➔ 0.01초 분석 실행`), 4대 재무비율, 변동분석, ISA 240 JET 이상전표 탐지, K-GAAP RAG 감사 조서 뷰어, 클립보드 복사 및 다운로드
2. **100% Python 결정론적 정규화 파싱 엔진 (Zero-Hallucination Parser)**:
   - LLM AI의 추론에 의존하지 않고 순수 파이썬 알고리즘으로 **6대 회계장부(재무상태표, 손익계산서, 시산표, 분개장, 거래처원장, 계정별원장)** 전수 파싱
   - ERP(더존 Smart A, 세무사랑, 위하고, 이카운트 등)의 복합 서식 엑셀(`.xlsx`, `.xls`) 및 `.csv` 자동 인식
   - 차감계정(대손충당금, 감누액) 자동 음수화, 괄호 번호(`(1)`, `(2)`) 및 주석행 완벽 필터링
3. **📒 계정별원장(General Ledger) 7대 핵심 필드 정밀 파싱 엔진**:
   - `[계정과목 Header] ➔ [일자별 상세 거래 Rows]` 블록 서식 전수 파싱
   - **7대 필드**: `계정코드`, `계정과목명`, `거래일자`, `적요`, `거래처코드`, `거래처명`, `차변/대변/잔액` 완벽 추출
   - 요약행(`월계`, `누계`, `전기이월`) 스마트 제외 및 대차 무결성 검증
4. **수집 현황 및 대차 무결성 가로형 2행(당기/전기) Health Matrix Dashboard**:
   - 수집 전용 탭에서 당기(2025년)와 전기(2024년) 2개 행 매트릭스 표출
   - 6대 장부별 수집 상태(`🟢 정상 126건`), 연도별 파일명, 대차평형 여부, 수집 무결성 점수(`100점`) 실시간 표출
   - **데이터 원본 인스펙터 모달**: 6대 장부별 표(Table) 뷰와 JSON 원본 뷰 전환 열람 및 [📋 JSON 복사] 지원
5. **📂 실시간 회계 데이터 아카이브 & 업로드 이력 관리 센터**:
   - 기업별, 결산연도별, 시점별(Timestamp) 영구 누적 보관 타임라인 테이블 표출
   - **⚡ 0.01초 즉시 복원**: 과거 분석 데이터를 재파싱 없이 0.01초 만에 화면 전체로 복원
   - **📥 원본 ZIP 일괄 다운로드**: 특정 시점에 업로드되었던 원본 엑셀/CSV 파일들을 인메모리 압축 ZIP 파일로 제공
6. **사내 폐쇄형 로컬 보관함 & 사내 Ubuntu 서버 확장 하이브리드 스토리지**:
   - 외부 클라우드로 회계 데이터가 유출되지 않도록 `uploads/작업완료_보관함/<기업명>/<연도>/<타임스탬프>/`에 원본 파일(`raw_files/`), `data.json`, `metadata.json`, `report.md` 동시 영속화
   - 사내 Ubuntu 서버(Docker MinIO / Remote Mount `/mnt/storage/minio_data`) 환경설정 지원으로 손쉬운 엔터프라이즈 확장
7. **4대 재무비율 & 한국은행 벤치마크 진단**:
   - 안정성(부채비율, 유동비율, 당좌비율, 차입금의존도, 이자보상배율)
   - 수익성(영업이익률, 순이익률, ROE, ROA)
   - 성장성(매출성장률, 영업이익성장률, 총자산증가율, 순이익증가율)
   - 활동성(매출채권회전율/DSO, 재고자산회전율/DIO)
8. **ISA 240 분개장 저널 엔트리 테스팅 (JET Anomaly Detection)**:
   - 전표번호 그룹핑, 대차평형(`∑차변 == ∑대변`) 무결성 검증
   - 주말/공휴일 전표, 쪼개기(Smurfing) 거래, 라운드 넘버(000,000원 단위), 가지급금/가수금 대체, 분식 위험 키워드 전수 스캔
9. **거래처원장 리스크 & 채권 연령(Aging) 분석**:
   - 상위 5대 매출처 집중도(Top 5 Concentration) 산출
   - 180일 및 365일 이상 장기 미회수 부실 채권 식별 및 동일 상호 매출/매입 양방향 상계 대상 대사
10. **K-GAAP RAG 감사 조서 자동 작성 & 영속화**:
    - 일반기업회계기준(K-GAAP) 임베딩 벡터 RAG 검색 연동
    - 전문 마크다운(`.md`) 감사 보고서 실시간 렌더링, 클립보드 복사, 파일 다운로드

---

## 🏛️ 2. 시스템 아키텍처 및 파일 구조

```text
landing_page/
├── core/
│   ├── audit_engine.py          # [분리] ingest_accounting_files_to_bundle (1단계) & run_analysis_from_normalized_bundle (2단계)
│   ├── storage_manager.py       # [스토리지] 시점별 영구 누적 저장(raw_files, data.json, metadata.json), 0.01초 로드, 원본 ZIP 다운로드
│   └── extensions.py            # Supabase, ChromaDB, OpenAI 임베딩 및 글로벌 로거 설정
├── blueprints/
│   └── master.py                # [/master/api/ingest-files], [/master/api/analyze-stored-dataset], [/upload-history*] 엔드포인트
├── templates/
│   └── master.html              # [📂 회계자료 수집 & 보관소 (#tab-data-ingestion)] & [🧠 기업 정밀 분석 허브 (#tab-analytics-hub)]
├── static/
│   ├── js/
│   │   ├── main.js              # 탭 라우팅 및 사이드바 이벤트 핸들러
│   │   └── master_analytics.js  # handleIngestFiles, handleStoredAnalysis, 6대 장부 매트릭스 렌더러, 0.01초 복원 엔진
│   └── css/
│       └── style.css            # 2대 탭 레이아웃, 드롭존, 수집 매트릭스, 인스펙터 모달 스타일
└── uploads/
    ├── 고객제시자료/            # 고객 제출 엑셀 원본 보관함
    └── 작업완료_보관함/          # [사내 로컬 폐쇄형 보관함] {회사명}/{연도}/{타임스탬프}/(raw_files, data.json, metadata.json)
```

---

## 🔌 3. REST API 엔드포인트 명세

| Method | Endpoint | 설명 | 주요 Request Parameters | 주요 Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/master/api/ingest-files` | **[1단계] 6대 장부 수집, 스마트 파싱 및 우분투/로컬 시점별 영구 저장** | `company_name`, `fiscal_year`, `files[]` | `session_id`, `ingestion_health`, `normalized_bundle`, `archive_info` |
| `POST` | `/master/api/analyze-stored-dataset` | **[2단계] 저장본 기반 0.01초 초고속 정밀 분석 & AI 감사 조서 산출** | JSON: `{ "company_name", "fiscal_year", "session_id" }` | `summary`, `ratios`, `variance_analysis`, `jet_anomalies`, `subledger_risks`, `report_md` |
| `GET` | `/master/api/upload-history` | 실시간 회계 데이터 업로드 및 아카이브 타임라인 이력 목록 반환 | Query: `?company_name=...` (선택) | `{ "success": true, "count": N, "history": [{ "company_name", "session_id", "saved_at", "ledgers_collected", ... }] }` |
| `GET` | `/master/api/upload-history/restore` | 특정 시점의 아카이브 데이터를 0.01초 만에 즉시 복원 | Query: `?company_name=...&session_id=...` | 전체 분석 페이로드 (`normalized_bundle`, `summary`, `report_md` 등) |
| `GET` | `/master/api/upload-history/download-raw` | 특정 시점의 원본 업로드 엑셀 파일들을 ZIP으로 일괄 다운로드 | Query: `?company_name=...&session_id=...` | `application/zip` 바이너리 스트림 |
| `GET` | `/master/api/datasets/local-list/<name>` | 사내 로컬/Ubuntu 보관함에 저장된 과거 분석 데이터셋 목록 조회 | URL Parameter: `company_name` | `{ "datasets": [{ "filename", "fiscal_year", "saved_at", "size_bytes", "source" }] }` |
| `POST` | `/master/api/save-analysis` | 분석 결과 및 조서 수동 영속화 저장 | JSON: `{ "company_name", "fiscal_year", "analysis_data", "report_md" }` | `{ "success": true, "archive_info": {...} }` |
| `GET` | `/api/audit/companies` | **[감사] 감사 수임 고객사 목록 조회** | - | `{ "success": true, "companies": [{ "id", "company_name", ... }] }` |
| `GET` | `/api/audit/templates/tree` | **[감사] K-GAAP 105개 조서 색인 트리 반환** | - | `{ "success": true, "tree": [{ "code", "title", "items": [...] }] }` |
| `POST` | `/api/audit/working-papers/generate` | **[감사] 6대 장부 연계 계정과목별 AI 조서 자동생성** | JSON: `{ "company_name", "fiscal_year", "account_code" }` | `{ "success": true, "working_paper_md", "reconciliation" }` |
| `GET` | `/api/audit/working-papers/export-excel` | **[감사] K-GAAP 원본 서식 엑셀(.xlsx) 스트리밍 다운로드** | Query: `?company_name=...&fiscal_year=...&account_code=...` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `GET` | `/api/audit/schedules` | **[감사] FullCalendar v6 감사일정 목록 조회** | Query: `?company_name=...&type=...` | `{ "success": true, "schedules": [...] }` |
| `POST` | `/api/audit/schedules` | **[감사] 신규 감사일정 등록** | JSON: `{ "company_name", "title", "schedule_type", "start_date", "end_date" }` | `{ "success": true, "schedule": {...} }` |

---

## 💾 4. 하이브리드 스토리지 확장 가이드 (사내 Ubuntu Server & MinIO S3)

사내 별도의 Ubuntu 서버 및 MinIO 오브젝트 스토리지로 확장을 원할 경우, `.env` 파일에 다음 항목을 지정하기만 하면 즉시 연동됩니다:

```bash
# STORAGE_MODE: 'local' (로컬 전용), 'ubuntu_server' (Ubuntu 전용), 'hybrid' (로컬+MinIO S3+Ubuntu 동시 저장)
STORAGE_MODE=hybrid

# 방안 1) 사내 Ubuntu MinIO S3 오브젝트 스토리지 연동 (Boto3 API Lakehouse Bronze Layer)
MINIO_ENDPOINT=https://s3.hyean-dskim.com
MINIO_ACCESS_KEY=hyean_dskim
MINIO_SECRET_KEY=your_password
MINIO_BUCKET_NAME=audit-lakehouse

# 방안 2) 사내 Ubuntu 서버 마운트 경로 지정 (NFS / Samba / SFTP)
UBUNTU_ARCHIVE_PATH=/mnt/storage/minio_data

# 방안 3) 사내 Ubuntu PostgreSQL Database 연결 (선택 사항)
UBUNTU_PG_HOST=192.168.1.100
UBUNTU_PG_PORT=5432
UBUNTU_PG_DB=audit_lakehouse
UBUNTU_PG_USER=postgres
UBUNTU_PG_PASSWORD=your_password
```

---

## 🚀 5. 고도화 마일스톤 현황

- [x] **Phase 1. 결정론적 정규화 파싱 엔진 (`build_normalized_financial_bundle`) 구축** (완료)
- [x] **Phase 2. 수집 현황 5-Pill 그리드 & 데이터 원본 인스펙터 모달 UI 신설** (완료)
- [x] **Phase 3. 사내 폐쇄형 로컬 보관함 자동 저장 & 0.01초 초고속 복원 허브 구축** (완료)
- [x] **사내 Ubuntu 서버 확장용 하이브리드 스토리지 어댑터 (`core/storage_manager.py`) 구축** (완료)
- [x] **사내 Ubuntu MinIO S3 오브젝트 스토리지 (Boto3 API) 자동 적재 & 버킷 관리 & S3 스트리밍 복원 연동** (완료)
- [x] **Phase 4. 모바일/태블릿 반응형 최적화 & PWA 웹앱 환경 및 1:1 상담 메신저 구축** (완료)
  - 스마트폰 뷰포트 Single-Column 스택 레이아웃 및 상단 가로 스크롤 탭 바
  - 카카오톡 스타일 1:1 실시간 자문 상담실 모바일 UI 및 터치 최적화
  - PWA (`manifest.json`, `sw.js`, 192x192/512x512 아이콘) 홈 화면 추가 지원
- [x] **Phase 5. 전역 플로팅 AI 회계사 팝업 & 3계층 무중단 하이브리드 RAG 엔진 고도화** (완료)
  - **전역 플로팅 팝업 위젯 (`templates/components/ai_cpa_widget.html`)**: 파트너사 포털(`company.html`), 마스터 관리자 7개 전 탭(`master.html`), 파트너사 상세 관리(`master_detail.html`) 등 로그인된 모든 창에서 FAB 버튼 및 사이드바 연동을 통한 독립 모달 팝업 상시 가동
  - **3단계 무중단 RAG Fallback 파이프라인 (`blueprints/api.py`)**: 사내 Ubuntu 서버(ChromaDB/Dify) 접속 불가 시에도 내부 로컬 K-GAAP 기준서 코퍼스(`core/audit_engine.py`) 및 OpenAI 모델로 자동 전환되어 '서버 에러' 없는 100% 정상 스트리밍 답변 보장
  - **모바일/앱 뷰포트 텍스트 찌그러짐 원천 차단 (`static/css/style.css`)**: 한글 단어 단위 줄바꿈(`word-break: keep-all; min-width: 0;`) 및 100% 풀스크린 반응형 오버레이 적용
  - **레이아웃 무결성 및 탭 독립화 (`static/js/main.js`)**: 마스터 관리자 HTML DOM 중첩 버그 수정 및 사이드바 클릭 인터셉트를 통해 모든 탭 전환 시 위젯 상시 표시 보장
- [x] **Phase 6. 6대 장부(계정별원장 7대 필드) 확장 & 실시간 업로드 이력 관리 센터 & 시점별 영구 누적 스토리지 구축** (완료)
  - **계정별원장(General Ledger) 7대 필드 전수 추출 파서**: 계정과목, 거래일자, 적요, 거래처코드, 거래처명, 차변, 대변, 잔액
  - **사내 Ubuntu & 로컬 시점별(`YYYYMMDD_HHMMSS`) 영구 보관함**: 원본 엑셀(`raw_files/`), `data.json`, `report.md`, `metadata.json`
  - **실시간 업로드 이력 관리 센터 UI**: 실시간 타임라인, 0.01초 즉시 복원, 원본 ZIP 압축 다운로드
  - **MinIO S3(Boto3) 3중 자동 영속화**: `s3://audit-lakehouse/bronze/...` 실시간 적재 및 S3 기반 0.01초 복원/ZIP 다운로드
  - **스토리지 헬스 모니터링**: 로컬 파일 시스템, Ubuntu 원격 마운트, 사내 MinIO S3 연결 상태 통합 점검 API 연동
- [ ] **Phase 7. 향후 다각적 분석 허브 및 운영 최적화 로드맵**:
  - **서버 환경 실운영 안정화 (500 에러 및 패키지/권한 정밀 진단)**
  - **마스터 관리자 사이드바 3대 탭 체계(대시보드 / 파트너사 관리 / 회계감사) 리팩토링**
  - **시계열 다개년 추세 분석 (Multi-year Trend)**: 3~5개년도 저장본 결합 분석
  - **동종업계 피어 그룹 교차 비교 (Cross-sectional Peer Benchmarking)**
  - **세무조정 및 심층 포렌식 연계 (Tax Adjustment & Forensic)**

---

## 🛠️ 6. 개발 지침 및 마스터 프롬프트 가이드 (Instruction & Master Prompt)

### 📌 개발 진행 시 준수 가이드라인 (Instruction for Developers & AI Agents)
1. **단일 단계 진행 원칙 (Step-by-Step Execution)**:
   - 새로운 기능 추가나 대규모 리팩토링 시 아래의 `master_prompt_example` 구조를 준수하여 한 번에 하나의 Step만 진행합니다.
   - 각 단계가 완료된 후 동작 검증(Frontend Console Log, Backend Flask Log)을 거친 뒤 다음 단계로 넘어갑니다.
2. **백엔드 로깅 규칙 (Backend Logging Rule)**:
   - Python 코드 내 `print()` 사용을 엄격히 금지하며, `logging` 모듈(`logger.info`, `logger.error` 등)을 사용합니다.
   - 모든 API 요청/응답 및 예외(try-except) 처리 시 트레이스백과 상황 컨텍스트를 구조화된 로그로 남깁니다.
3. **무결성 및 회귀 방지 (Zero Regression)**:
   - 기존에 정상 동작하던 엔드포인트 및 UI 컴포넌트는 절대 임의로 삭제하거나 덮어쓰지 않습니다.

---

### 📋 `master_prompt_example` (마스터 관리자 개편 마스터 프롬프트 예시)

```markdown
# 역할

당신은 Python Flask, Jinja2, Vanilla JavaScript, CSS로 회계법인 포털 시스템을 고도화하는 Senior Full Stack Developer이다.

코딩 및 시스템 구조 변경을 진행할 때 초보자와 함께 한 단계씩 안전하게 진행한다.

복잡한 구조보다 다음을 우선한다.
1. 기존 기능의 완벽한 보존 (회귀 버그 방지)
2. 매 단계 실행해서 화면과 동작을 즉시 확인할 수 있는 상태 유지
3. 충분한 Frontend Console Log와 Backend Python Logging
4. 오류 발생 시 현재 상태와 원인을 초보자에게 친절하고 명확하게 설명하는 구조

# 프로젝트명

Hyean Admin Portal - Master Tab Refactoring

# 프로젝트 목적

마스터 관리자(Master Admin)의 좌측 사이드바 및 페이지 구성을 업무 효율 중심의 3대 핵심 탭 체계로 전면 개편한다.

1) [대시보드 홈]: 기존 홈 화면 유지 (전체 현황 요약)
2) [파트너사 관리]: 파트너사 목록뿐 아니라 '업무 요청 관리'와 '공지 및 알림 관리'를 서브 탭/모듈로 통합
3) [회계감사]: 기존 '금융기관 조회 관리'를 '회계감사' 탭으로 명칭 및 영역을 확장하고, 하위에서 금융기관 조회 및 감사 증빙을 관리
4) [통합 문서 보관함]: 별도 우분투 서버를 유지 중인 환경을 고려하여, 비효율적인 독립 전역 탭을 제거하고 파트너사별/감사업무별 하위 문서함으로 분산 통합

# 절대 규칙 (가장 중요)

- 기존에 구현되어 정상 작동하던 백엔드 로직(데이터 조회, 승인/반려, 금융기관 상태 변경 등)을 임의로 삭제하거나 훼손하지 않는다.
- 모든 백엔드(Python) 코드 작성 및 수정 시 단순 print() 대신 Python 표준 logging 모듈(logger.info, logger.error 등)을 필수 사용한다.
- API 요청(Request), 응답(Response), 예외(try-except) 발생 시 에러 트레이스백과 컨텍스트를 반드시 로그에 남긴다.
- 비밀값(API 키, 토큰, DB 접속정보 등)은 프론트엔드나 로그에 절대 노출하지 않는다.
- 사용자가 명시적으로 지시하지 않는 한, 커밋(commit)이나 푸시(push)를 임의로 수행하지 않는다.

# 사용 기술 및 제약사항

- 사용 기술: Python Flask (Blueprints), Jinja2 Template, Vanilla JavaScript, HTML5/CSS3
- 불필요한 무거운 프레임워크(React, Vue 등)나 추가 라이브러리 도입을 금지하고 기존 순수 JS/CSS 구조를 유지한다.

# 사이드바 및 UI 구조 개편 정의

[기존 사이드바: 6개 메뉴]
- 대시보드 홈 / 파트너사 관리 / 업무 요청 관리 / 금융기관 조회 관리 / 통합 문서 보관함 / 공지 및 알림 관리

[개편 후 사이드바: 3대 메인 탭 체계]
1. 🏠 대시보드 홈 (`#tab-dashboard` / `/master`)
   - 전사 요약 지표 카드, 최근 요청/알림 현황 위젯 유지
2. 👥 파트너사 관리 (`#tab-partners` / `/master/partners`)
   - [서브탭 1] 파트너사 목록 및 등록/수정
   - [서브탭 2] 업무 요청 관리 (기존 업무 요청 승인/반려/필터링 이관)
   - [서브탭 3] 공지 및 알림 발송 관리 (기존 공지 작성/발송 이관)
   - [서브탭 4] 파트너사별 수발신 문서 이력
3. 🏛️ 회계감사 (`#tab-audit` / `/master/audit`)
   - [서브탭 1] 금융기관 조회 관리 (기존 조회서 발송, 회신 상태 추적 이관)
   - [서브탭 2] 감사 증빙 문서 관리

# Flask 라우트 및 API 구조

GET  /master               마스터 관리자 메인 템플릿(master.html) 렌더링
GET  /master/partners      파트너사 관리 통합 뷰 및 데이터 반환
GET  /master/audit         회계감사(금융기관 조회) 뷰 및 데이터 반환
POST /api/partners/...     파트너사 CRUD API
POST /api/requests/...     업무 요청 승인/반려/상태변경 API
POST /api/audit/...        금융기관 조회서 등록/상태업데이트 API
POST /api/notices/...      공지/알림 등록 및 발송 API

# Frontend Console Log 규칙

[NAV]     탭 전환 시작 (이전 탭 -> 대상 탭)
[SUBTAB]  서브 탭 전환 (파트너사 목록 / 업무요청 / 공지알림 / 회계감사 서브)
[REQUEST] API 요청 전송 (엔드포인트, 파라미터 요약)
[RENDER]  UI 컴포넌트 렌더링 완료
[ACTION]  사용자 인터랙션 (승인, 반려, 필터 변경, 모달 열기)
[ERROR]   JS 실행 또는 API 응답 오류

# Backend Log 규칙

Python logging 모듈을 사용한다. print()는 일절 사용하지 않는다.

[ROUTE]   GET /master - Master Admin Main Loaded
[ACTION]  탭/서브페이지 이동 또는 데이터 조회
[API_REQ] API 요청 파라미터 (Request Payload)
[API_RES] API 응답 상태 (Response Status & Data Count)
[ERROR]   예외 발생 시 logger.error()로 상세 Traceback 출력

# 반드시 지킬 작업 순서

Step 1.  현재 작업 경로(landing_page)와 templates/, blueprints/, static/ 내 관리자 파일 구조를 점검한다.
Step 2.  templates/master.html 및 master_detail.html의 사이드바 메뉴 HTML을 3대 메인 탭 체계로 재구성한다.
Step 3.  사이드바 메뉴 스타일(CSS) 및 활성화(active) 클래스 전환 스타일을 점검하고 보완한다.
Step 4.  static/js/main.js(또는 관리자 JS)의 탭 전환 라우팅/이벤트 리스너를 3대 탭 체계에 맞게 수정한다.
Step 5.  '파트너사 관리' 탭 내부에 [파트너사 목록 | 업무 요청 | 공지 및 알림 | 문서함] 서브탭 UI를 구성한다.
Step 6.  기존 '업무 요청 관리'의 테이블, 필터, 모달 로직을 '파트너사 관리 > 업무 요청' 서브탭으로 이관한다.
Step 7.  기존 '공지 및 알림 관리'의 작성 폼과 발송 내역 로직을 '파트너사 관리 > 공지/알림' 서브탭으로 이관한다.
Step 8.  '회계감사' 메인 탭 UI를 신설하고, 기존 '금융기관 조회 관리' 테이블과 상태 관리 로직을 이관한다.
Step 9.  blueprints/master.py 및 관련 API 라우트를 개편된 탭/서브탭 구조에 맞게 점검하고 로깅(logger)을 보강한다.
Step 10. 독립 탭이었던 '통합 문서 보관함'을 제거하고, 파트너사/회계감사 하위로의 연계 정상 동작을 확인한다.
Step 11. Flask 로컬 서버를 실행하여 브라우저에서 탭 전환, 서브탭 전환, 반응형 UI를 직접 검증한다.
Step 12. 업무 요청 승인/반려, 공지 발송, 금융기관 조회 상태 변경 등 주요 기능이 오류 없이 동작하는지 최종 테스트한다.

# 개발 원칙

- 한 번에 한 단계만 진행한다.
- 각 단계가 끝나면 멈추고, 사용자가 "다음"이라고 말할 때까지 기다린다.
- 코드를 말로만 설명하지 말고 실제 수정할 파일과 정확한 코드 스니펫을 제시한다.
- 이전 단계에서 정상 작동하던 기존 기능을 삭제하거나 누락시키지 않는다.
- 파일을 수정할 때는 어떤 파일을 왜 수정하는지 먼저 명확히 설명한다.
- 오류가 발생하면 여러 곳을 추측으로 건드리지 말고 원인을 분리하여 한 번에 하나씩 해결한다.

# 응답 형식 (매 단계마다 이 형식을 엄격히 지킨다)

## 현재 단계
## 이번 단계의 목표
## 수정/작성할 파일 또는 입력할 명령어
## 코드 / 변경 내용
## 이 작업이 하는 일
## 실행 및 확인 방법
## 완료 확인
## 다음 단계

# 시작 지시

지금 Step 1만 수행하고 멈춰라.
```

