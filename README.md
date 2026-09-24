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
  - **전역 플로팅 팝업 위젯 (`templates/components/ai_cpa_widget.html`)**: 파트너사 포털(`company.html`), 마스터 관리자 7개 전 탭(`master.html`), 파트너사 상세 관리(`master_detail.html`), 회계감사 포털(`audit.html`) 등 로그인된 모든 창에서 FAB 버튼 및 사이드바 연동을 통한 독립 모달 팝업 상시 가동
  - **3단계 무중단 RAG Fallback 파이프라인 (`blueprints/api.py`)**: 사내 Ubuntu 서버(ChromaDB/Dify) 접속 불가 시에도 내부 로컬 K-GAAP 기준서 코퍼스(`core/audit_engine.py`) 및 OpenAI 모델로 자동 전환되어 '서버 에러' 없는 100% 정상 스트리밍 답변 보장
  - **웹 마우스 드래그 창 크기 조절(Resizer) & 영구 기억 (`static/js/main.js`, `static/css/style.css`)**:
    - 좌측 상단 모서리(`⤡` 아이콘), 좌측 테두리, 상단 테두리 마우스 드래그를 통해 가로·세로 크기 자유 조절 지원
    - 조절된 사용자 맞춤 크기를 `localStorage`에 자동 저장하여 재접속 시에도 완벽 복원
  - **모바일 90dvh 바텀시트 모달 & 콤팩트 가독성 최적화**:
    - 스마트폰 뷰포트에서 상단 10%가 보이는 90% 높이 앱 바텀시트 모달 및 상단 손잡이 인디케이터 바 적용
    - 말풍선 내부 패딩(`8px 12px`), 메시지 간격(`gap: 8px`), 문단 하단 마진(`3px`) 최소화로 휑한 공백 없는 밀착 가독성 확보
    - 질문 입력창 Flexbox 85% 시원한 가로 확장, 브라우저 기본 스크롤 화살표(`▲ ▼`) 제거 및 입력 내용에 따른 `auto-grow` 적용
  - **레이아웃 무결성 및 캐시 무효화(`?v=20260922-cpa-v9`)**: 전 템플릿 정적 파일 버전 일괄 갱신으로 브라우저 즉시 렌더링 보장
- [x] **Phase 6. 6대 장부(계정별원장 7대 필드) 확장 & 실시간 업로드 이력 관리 센터 & 시점별 영구 누적 스토리지 구축** (완료)
  - **계정별원장(General Ledger) 7대 필드 전수 추출 파서**: 계정과목, 거래일자, 적요, 거래처코드, 거래처명, 차변, 대변, 잔액
  - **사내 Ubuntu & 로컬 시점별(`YYYYMMDD_HHMMSS`) 영구 보관함**: 원본 엑셀(`raw_files/`), `data.json`, `report.md`, `metadata.json`
  - **실시간 업로드 이력 관리 센터 UI**: 실시간 타임라인, 0.01초 즉시 복원, 원본 ZIP 압축 다운로드
  - **MinIO S3(Boto3) 3중 자동 영속화**: `s3://audit-lakehouse/bronze/...` 실시간 적재 및 S3 기반 0.01초 복원/ZIP 다운로드
  - **스토리지 헬스 모니터링**: 로컬 파일 시스템, Ubuntu 원격 마운트, 사내 MinIO S3 연결 상태 통합 점검 API 연동
- [x] **Phase 7. CPA 회계감사 포털 DSD 감사보고서 & 주석 자동화 허브 및 DART 표준 롤포워드 엔진 구축** (완료):
  - **전기 DSD 역추출 파서 (`core/dsd_manager.py`)**: 전기 `.dsd` 파일(ZIP 바이너리)에서 비교표시 재무제표 4종(B/S, I/S 등) 및 18개 주석(67개 표) 100% 무결성 역추출
  - **결산 수정분개(AJE) 실시간 연동 파이프라인 (`core/audit_engine.py`)**: AJE 분개 입력 시 수정후 T/B 및 B/S, I/S 대차평형($\Delta = 0$) 및 5대 계정 자동 분류 실시간 재계산
  - **K-GAAP 주석(Notes 1~18번) 자동 생성 엔진 (`core/notes_generator.py`)**: 특수관계자, 지분법, 유형자산변동표, 잉여금처분계산서 등 18개 표준 주석 자동 집계
  - **금융감독원 DART 표준 DSD 빌더 & 롤포워드 엔진 (`core/dsd_builder.py`)**: 
    - 금감원 DART 편집기(DART 4.0 / 5.107) 전용 스키마(`dart4.xsd`) 및 00760 서식 구조 100% 준수
    - 5열 재무제표(`과목, 당기세부, 당기합계, 전기세부, 전기합계`)의 전기 롤포워드 및 당기 AJE 수정후 금액 자동 인젝션
    - 토큰 기반 기수(15기 ➔ 16기) 및 회계연도(2025 ➔ 2026) 안전 치환 및 `SUMMARY` 추출값(자산/부채/매출액) 자동 갱신
    - 감사의견서(K-GAAS 700) + 재무제표 4종 + 주석을 `contents.xml`, `meta.xml`의 `.dsd` 파일로 원클릭 바이너리 스트리밍
  - **CPA 포털 4단계 원스톱 카드 대시보드 UI (`templates/audit.html`, `static/js/audit_dsd_hub.js`)**:
    - **상단 DSD 메타데이터 바**: 회사명, CIK(`01294846`), 3개년 fiscal_year 드롭다운(`2026/2025/2024`) 실시간 양방향 동기화
    - **4단계 대시보드 워크플로우**: 전기 DSD 업로드 & 역추출 ➡️ AJE 수정분개 & 대차평형 ➡️ 18개 주석 검토 ➡️ DSD 최종 빌드 및 DART 전용 `.dsd` 다운로드
  - **E2E 전 단계 통합 검증 (`scripts/verify_step10_e2e.py`)**: Step 1~10 전 파이프라인 무결성 테스트 통과 (100% Pass)
- [x] **Phase 8. 고객사 전용 포털(`company.html`) UI/UX 전면 개편 & 선택 기반 Drag & Drop 허브 고도화** (완료):
  - **독립 뷰 분리 및 사이드바 메뉴 재편**:
    - `자료제출` (`partner-home-view`): 대형 스마트 드롭존, 미제출 서류 팝오버, 진척도 트래커, 최근 제출 목록 5개 및 문의사항 제출 폼으로 구성된 단일 집중 제출 허브로 정돈
    - `🏛️ 외부조회` (`partner-external-view`): 금융기관(신청 현황 요약, 전자/서면조회 신청 마법사, PDF 서식 발급) 및 거래처(수신처 엑셀 업로드) 전용 독립 뷰 신설
    - `📊 분석보고서` (`partner-analysis-view`): 제출된 장부 기반 AI 변동성 분석, 식별된 감사 위험, K-GAAP 기준서 매칭, 시산표 ↔ 재무상태표 대차평형 대사, 감사 조서 초안(.md) 다운로드 독립 뷰 신설
    - 구형 `제출 내역 조회` 및 `AI 회계사 문의` 메뉴/뷰 정리 및 [static/js/main.js](file:///c:/Users/CLAUD/landing_page/static/js/main.js) 사이드바 라우팅 연동
  - **선택 기반 스마트 Drag & Drop 자료제출 파이프라인**:
    - 팝업창(팝오버)에서 서류 항목(예: `[PBC-P-01] 최신 정관`)을 클릭하여 선택한 후에만 해당 서류 전용 업로드 모드 활성화 (미선택 시 드롭존 클릭 시 서류 선택 팝업 유도)
    - 파일 Drag & Drop 또는 파일 선택 완료 시 팝업창(미제출 서류 목록)에서 해당 항목 즉시 제거 (`completed` 자동 숨김) 및 `localStorage` 동기화
    - 진도율 프로그레스 바(%) 및 미제출 건수 뱃지 실시간 차감 갱신, 최근 제출 목록 상단 실시간 행 추가, 드롭존 상태 자동 리셋

- [x] **Phase 10. MinIO S3 회계 데이터 레이크하우스 파싱 엔진 고도화 & 6대 장부 Health Matrix / Data Inspector 구축** (완료):
  - **재무상태표(B/S) 4단 컬럼 고정밀 파싱 엔진 (`core/audit_engine.py`)**:
    - A열(계정과목), B열(당기 총액 `CurrentGross`), C열(당기 순액 `CurrentNet`), D열(전기 총액 `PriorGross`), E열(전기 순액 `PriorNet`) 분리 파싱
    - 차감계정(대손충당금, 감가상각누계액, 정부보조금 등) 및 차감 모계정(외상매출금, 건물 등) 자동 식별 및 2-Pass 장부가액/순액 연동
  - **합계잔액시산표(T/B) 5단 컬럼 및 2-Pass 직접 계산 엔진 (`core/audit_engine.py`)**:
    - A열(차변잔액), B열(차변합계), C열(과목), D열(대변합계), E열(대변잔액) 전수 파싱
    - 총합계(`◀...▶`) 및 부분합계(`◁...▷`) 2-Pass 직접 계산(`CalcDebitBalance` 등) 합산 검증 (`IsBalanced: True`, 100% 대차 일치)
  - **JSON 표준 정규화 및 MinIO 레이크하우스 무결성 동기화 (`core/storage_manager.py`)**:
    - `NaN`/`Inf` 부동소수점의 표준 JSON `null` 자동 변환(`_clean_for_json`, `_df_to_records`)을 통해 프론트엔드 파싱 오류 원천 차단
    - `GET /api/company/normalized-dataset/<company>`를 통해 당기/전기 재무 데이터를 0.01초(15~40ms) 인메모리 고속 반환
  - **마스터 포털 6대 장부 가로형 2행 Health Matrix & 데이터 원천 인스펙터 UI (`master_analytics.js`, `master.html`)**:
    - 당기(2025년: BS 69건, IS 51건, TB 129건) / 전기(2024년: BS 67건, IS 48건, TB 126건) 병렬 로드 및 상시 표출
    - 장부별 맞춤형 인스펙터: 시산표(차변잔액-차변합계-과목-대변합계-대변잔액 5단 대칭 뷰) 및 재무상태표(총액/순액 분리 뷰) 렌더러 탑재

- [x] **Phase 11. MinIO 6대 표준장부 기반 경영진 정밀 회계분석 포털 대시보드 및 반응형 구축** (완료):
  - **백엔드 5대 정밀 회계분석 알고리즘 엔진 (`core/audit_engine.py`)**:
    - **[분석 1] 분개장 JET & 벤포드의 법칙 (ISA 240)**: 13,800+건 전표 전수 대상 1차 자릿수(1~9) 출현 빈도 vs 벤포드 이론치 비교 ($\text{MAD} = 0.0114$, 적합도 양호 판정). 주말/공휴일 기표, 라운드넘버 거액 전표, 기말 결산 집중 대체 분개 이상치 전수 식별.
    - **[분석 2] 거래처 집중도(Pareto 80/20) & 매출채권 회수 리스크**: 상위 20% 거래처 매출/채권 집중도(98.77%), HHI 독과점/다변화 지수, 회수 기일별 연령(정상/주의/경고/고위험) 분류 및 예상 대손충당금 자동 산출.
    - **[분석 3] 듀퐁 3단계 ROE 분해 & 현금전환주기(CCC)**: $\text{ROE} = \text{순이익률} \times \text{총자산회전율} \times \text{재무레버리지}$ 3단계 분해 및 변동 요인 규명. $\text{CCC} = \text{DSO} + \text{DIO} - \text{DPO}$ 운전자본 회수 속도 진단.
    - **[분석 4] 비용 Outlier 및 월별 지출 트렌드**: 전년 대비 급증 계정 Top 5 및 주요 경비(접대비, 여비교통비, 수수료)의 1~12월 월별 지출 패턴 및 거래처 집중도 추적.
    - **[분석 5] 경영진 종합 회계 건강 점수 & 수정분개(AJE) 사전 권고**: 대차평형, 벤포드 편향, 거래처 집중도 등을 결합한 종합 점수(80점 AA 등급) 산출 및 결산 전 사전 반영 권고 분개안(AJE) 자동 제시.
  - **REST API 엔드포인트 구축 (`blueprints/api.py`)**:
    - `GET /api/company/portal-analytics/<company_name>?fiscal_year=YYYY`: 13,000+건 전표/원장 데이터를 1초 내외로 실시간 연산하여 구조화된 JSON으로 스트리밍.
  - **포털 대시보드 인터랙티브 시각화 & PDF 출력 (`templates/company.html`, `static/css/style.css`)**:
    - Chart.js 기반 벤포드 복합 차트, 파레토 이중 Y축 차트, 월별 비용 추이 멀티라인 차트 연동.
    - `html2pdf.js` 기반 경영진 감사분석 보고서 원클릭 PDF 출력 기능 탑재.
    - 2025년, 2024년, 2023년 분석연도 실시간 비동기 전환 동기화.
  - **모바일/태블릿 반응형 앱(App View) & 전폭 레이아웃 최적화**:
    - 데스크톱 100% Full-Width 화면 활용 및 모바일(768px/480px) 1열 스택 재배치.
    - 터치 친화적 가로 스크롤 테이블 및 뷰포트 맞춤형 차트 높이 자동 조정.

---

## 🔮 6. 향후 과제 로드맵

### 🎯 [우선순위 1] 6대 장부 Jsonify 파싱 엔진 고도화 (분개장, 거래처원장, 계정별원장)
- [ ] **과제 1-1. 분개장(Journal Entries) 고정밀 Jsonify 파싱 엔진**:
  - ERP별(더존, 세무사랑, 이카운트 등) 다열/복합 전표 번호 그룹핑 및 차변/대변 1:N 전표 분해
  - 거래일자, 전표번호, 계정코드, 계정과목명, 적요, 차변금액, 대변금액, 거래처, 증빙구분 표준 JSON 규격화
  - ISA 240 JET(이상전표 탐지: 주말/공휴일, 쪼개기 거래, 라운드넘버) 알고리즘과 100% 직결
- [ ] **과제 1-2. 거래처원장(Subledger) 고정밀 Jsonify 파싱 엔진**:
  - 거래처별(사업자등록번호, 상호명) 전기이월, 당기 차변/대변 발생액, 기말잔액 블록 파싱
  - 매출채권/매입채무 채권연령(Aging: 30일/90일/180일/365일 이상) 산출용 JSON 표준화
  - 상위 5대 매출처 집중도 및 동일 거래처 양방향 상계(Offsetting) 자동 추출
- [ ] **과제 1-3. 계정별원장(General Ledger) 대용량 Jsonify 파싱 & 스트리밍 엔진**:
  - 7대 핵심 필드(계정코드, 과목명, 거래일자, 적요, 거래처코드, 거래처명, 차/대/잔액)의 대용량 스트리밍 JSON 직렬화
  - 월계/누계/전기이월 요약행 자동 배제 및 기중 누적 거래내역 전수 인덱싱

### 🤖 [우선순위 2] Dify & n8n 기반 5대 지능형 확장
- [ ] **과제 2-1. 파트너사 회계장부 업로드 즉시 「AI 자동 정밀진단 & 감사 리포트」 (Dify + n8n)**:
  - 파트너사가 엑셀 5대 장부 업로드 시 n8n이 트리거되어 자동 파싱 및 Dify K-GAAP 진단 후 AI 리포트 자동 발행
- [ ] **과제 2-2. 국세청 세법 개정 & DART 공시 「실시간 맞춤 알림봇」 (n8n + Dify)**:
  - n8n이 매일 국세청 세법 개정안 및 DART 전자공시 수집 ➔ Dify가 실무 영향 요약 후 알림 발송
- [ ] **과제 2-3. 세무·노무 계약서 「AI 원클릭 위험조항 검토기」 (Dify Document Workflow)**
- [ ] **과제 2-4. 1:1 자문 상담실 「AI 사전 브리핑 & 회계사 답변 초안 자동 생성」 (n8n + Dify)**
- [ ] **과제 2-5. 파트너사별 세무 캘린더 & 납부 기한 「스마트 리마인더」 (n8n Scheduler)**

---

## 🛠️ 7. 개발 지침 및 마스터 프롬프트 (Master Prompt for Antigravity CLI & PowerShell)

### 📌 Antigravity CLI 및 Windows PowerShell 직접 실행 원칙
본 프로젝트의 모든 변경 및 고도화 작업은 사용자가 **Antigravity CLI**와 **Windows PowerShell**을 통해 직접 통제하며 진행합니다.

1. **승인 기반 실행 원칙 (Approval-Required Execution)**:
   - 모든 작업 및 코드 적용/실행은 반드시 사용자의 사전 검토 및 명시적 승인 하에 단계별로 진행합니다.
2. **README 및 생성 규칙 우선 숙지 (Prior Rule Acquisition)**:
   - 작업을 시작하기 전 반드시 `README.md` 파일을 읽고 master_prompt 생성 규칙 및 기존 프로젝트 아키텍처를 완벽히 숙지합니다.
3. **단일 단계 진행 원칙 (Step-by-Step Execution)**:
   - AI 에이전트는 한 번에 오직 하나의 Step만 설명/작성하고 멈춥니다.
   - 사용자가 Windows PowerShell에서 검증 명령어를 실행하거나 화면을 확인한 후 `"다음"`이라고 지시할 때만 다음 Step으로 이동합니다.
4. **목표 기능 한정 및 회귀 방지 (Strict Scope & Zero Regression)**:
   - 고도화 및 변경하고자 하는 대상 기능 외의 기존 기능 및 코드는 절대 임의로 변경하거나 훼손하지 않습니다.
5. **최소한의 도구 사용 및 경량화 원칙 (Minimal Tooling & Lightweight)**:
   - 고도화 과정에서 꼭 필요한 최소한의 Tool들만 사용하며, 불필요하거나 무거운 프레임워크(Heavy Frameworks)는 절대 도입하지 않습니다 (Vanilla JS, 경량 표준 라이브러리 준수).
6. **백엔드 로깅 규칙 (Backend Logging Rule)**:
   - Python 코드 내 `print()` 사용을 엄격히 금지하며, Python 표준 `logging` 모듈(`logger.info`, `logger.error` 등)을 사용합니다.
   - 모든 API 요청/응답 및 예외(try-except) 발생 시 에러 트레이스백과 컨텍스트를 필수 기록합니다.

---

### 📋 `master_prompt`: 마스터 프롬프트 생성 기본 원칙

```markdown
# 역할

당신은 Python Flask, Jinja2, Vanilla JavaScript 및 회계/감사/기업 분석 도메인에 정통한 Senior Full Stack Developer & System Architect이다.

사용자는 Windows PowerShell과 Antigravity CLI 환경에서 직접 명령을 실행하고 코드를 확인하며 시스템을 한 단계씩 구축해 나간다.

# 개발 대원칙 (Master Prompt Creation Rules)

1. 반드시 모든 실행은 사용자의 승인하에 단계별로 진행한다.
2. 작업 전 항상 README.md 파일을 읽고 master_prompt 생성 규칙 및 시스템 구조를 숙지한다.
3. 한 번에 오직 한 단계(Step)만 진행하고 즉시 멈춘다.
4. 사용자가 PowerShell에서 테스트하거나 브라우저에서 확인한 뒤 "다음"이라고 입력할 때까지 임의로 다음 단계를 진행하지 않는다.
5. 변경하고자 하는 대상 기능 외의 기존 기능(파서, 조서, 스토리지 등)은 절대 변경하지 않는다 (Zero Regression).
6. 고도화 과정에서 꼭 필요한 최소한의 tool들만 사용하며, 불필요한 무거운 프레임워크는 절대 사용하지 않는다.
7. 백엔드(Python) 작성 시 print()는 일절 금지하며 Python 표준 logging 모듈(logger.info, logger.error)을 사용한다.
8. 모든 단계마다 사용자가 Windows PowerShell에서 직접 실행해 볼 수 있는 구체적인 검증 명령어(CLI/Python)를 함께 제공한다.

---

## 📦 3. 데이터저장 및 DB화 (Data Storage & Database Pipeline)

본 시스템은 고객이 제출하는 다양한 형태의 회계 증빙 및 결산 서류를 **1) 원본 보존**, **2) 체계적 DB 분류**, **3) 디지털 파싱 및 JSON 표준화**, **4) AI 감사조서 자동 연동**으로 이어지는 완전 자동화 데이터 레이크하우스 파이프라인으로 구축하고 있습니다.

### 🌟 현재 구축 완료 현황
1. **MinIO S3 객체 스토리지 연동 및 하이브리드 보관**:
   - 사내 Ubuntu 서버의 대용량 스토리지(`/mnt/storage/minio_data`)와 MinIO S3 API(`company-uploads`, `audit-lakehouse` 버킷) 연동 완료
   - 고객별(`company_name`), 회계연도/항목별(`year_folder`), 타임스탬프 기반 자동 경로 격리 저장
2. **파트너 포털 실시간 즉시 업로드 (Instant Upload)**:
   - 페이지 하단의 submit 버튼을 누를 필요 없이, 서류 항목을 클릭하고 파일을 선택(열기)하는 즉시 비동기(AJAX `/api/upload-single-file`)로 MinIO 및 Supabase DB에 실시간 저장
   - 실시간 업로드 스피너 피드백, 서류 칩 자동 완료 처리, 진도율(%) 실시간 계산
   - 최근 제출 서류 목록 테이블에 실시간 행 추가 및 MinIO 원본 다운로드 링크 연동

---

### 🗺️ 향후 추가 개발 로드맵

```text
[ 1단계: 만능 파일 파서 엔진 구축 ]
  • xlsx, xls, csv: 시트별 표, 계정과목, 차변/대변/잔액 수치 정밀 추출
  • pdf: 세무조정계산서/감사보고서의 텍스트 및 표 좌표 디지털화
  • png, jpg: 영수증, 통장 사본, 등기부등본의 AI OCR 글자 인식
  • zip: 자동 압축 해제 후 내부 파일들에 대한 재귀 파싱 처리
        │
        ▼
[ 2단계: 표준 JSON 규격화 및 DB 버전 관리 ]
  • 파싱된 데이터를 일관된 형식의 [표준 JSON 파일]로 생성하여 MinIO에 저장
  • Supabase `company_files` 테이블에 [고객별 / 연도별 / 항목별 / 업로드회차(1차, 2차)] 메타데이터 저장
  • 수정본 재업로드 시 버전(Version) 이력 관리 및 변경점 추적
        │
        ▼
[ 3단계: AI 감사 엔진 & 감사조서 자동 연동 ]
  • 파싱된 JSON 데이터를 감사 엔진(`core/audit_engine.py`)에 주입
  • 재무제표 대차 무결성 검증, 전기 대비 증감 분석, ISA 240 이상전표 탐지 자동 수행
  • OpenAI API를 통한 계정별 위험 평가 및 K-GAAP 감사 주석 초안 10초 만에 자동 완성
        │
        ▼
[ 4단계: 우분투 운영 서버 동기화 및 무중단 배포 ]
  • GitHub 배포 파이프라인을 통해 우분투 서버(`hyean-portal`)에 변경사항 동기화
  • `hyean-dskim.com` 실도메인 서비스 무중단 운영

---


# 프로젝트명

Hyean CPA Audit Hub - DSD Financial Reporting & Notes Automation

# 프로젝트 목적

CPA 회계감사 포털(/audit)에 다음 4대 핵심 파이프라인을 구축하여, 자료 입수부터 금융감독원 DART 제출용 .dsd 감사보고서 출력까지 전 과정을 완전 자동화한다.

1) [전기 DSD 역추출 파서]: 작년도 .dsd 파일 업로드 시 비교표시 재무제표 4종 및 기초 주석 데이터를 1초 만에 자동 추출
2) [수정분개(AJE) 실시간 연동]: 회계사 수정분개 입력 시 수정후 T/B 및 B/S, I/S 실시간 재계산 및 대차평형 검증
3) [주석(Notes 1~30번) 자동 생성기]: 특수관계자(주석13), 지분법(주석5), 유형자산변동(주석6), 잉여금처분(주석10) 원장 기반 자동 집계
4) [DART 표준 DSD 빌더]: 감사의견 + 재무제표 4종 + 주석을 contents.xml, meta.xml(CP949)로 조합하여 .dsd 파일 원클릭 출력
5) [CPA 4단계 원스톱 대시보드]: templates/audit.html의 #tab-audit-report 화면을 4단계 카드 흐름 및 DART 실시간 뷰어로 개편

# 사용 기술 및 환경 제약

- 백엔드: Python Flask (Blueprints), zipfile, xml.etree.ElementTree, pandas, openpyxl, logging
- 프론트엔드: Vanilla JavaScript, HTML5/CSS3 (무거운 프레임워크 도입 금지)
- 인코딩 규격: DART 표준 CP949(EUC-KR) XML 및 ZIP 압축 포맷 준수
- 실행 도구: Antigravity CLI, Windows PowerShell

# REST API 설계

POST /api/audit/dsd/parse-prior     전기 DSD 파일 업로드 ➔ 비교표시 재무제표 및 주석 역추출 반환
POST /api/audit/aje/apply           수정분개(AJE) 목록 적용 ➔ 실시간 수정후 B/S, I/S 재계산 반환
POST /api/audit/notes/generate      원장 기반 K-GAAP 1~30번 주석 표 및 마크다운 자동 집계 반환
POST /api/audit/dsd/build-export    최종 감사의견 및 재무제표 ➔ [회사명]_감사보고서_[기수].dsd 파일 스트리밍 다운로드

# 단계별 작업 순서 (Total 10 Steps)

Step 1.  [환경 점검] 현재 작업 폴더(landing_page)의 core/, blueprints/, templates/ 구조 및 uploads/dsd 샘플 파일 무결성 점검 (PowerShell 검증)
Step 2.  [DSD 파서 구축] core/dsd_manager.py 신설 - .dsd ZIP 해제, CP949 contents.xml/meta.xml 파싱, 전기 비교표시 B/S, I/S 추출 함수 구현
Step 3.  [DSD 파서 단위 테스트] uploads/dsd/(주)이노플로우_감사보고서_25.dsd를 대상으로 PowerShell CLI에서 파싱 정확도(매출/자산 추출) 검증
Step 4.  [AJE 엔진 고도화] core/audit_engine.py에 apply_audit_adjustments() 구현 - 원시 T/B + AJE ➔ 최종 수정후 T/B 및 대차평형 검증
Step 5.  [주석 생성기 구축] core/notes_generator.py 신설 - 특수관계자(주석13), 지분법(주석5), 유형자산(주석6), 잉여금처분(주석10) 원장 데이터 자동 집계 로직 작성
Step 6.  [DSD 빌더 구축] core/dsd_builder.py 신설 - 감사보고서 본문 + 재무제표 + 주석을 DART 표준 XML로 조립하고 CP949 ZIP .dsd 파일 패키징 함수 구현
Step 7.  [API 라우트 연동] blueprints/audit.py에 4대 신규 API 엔드포인트(/dsd/parse-prior, /aje/apply, /notes/generate, /dsd/build-export) 구현 및 logging 적용
Step 8.  [프론트엔드 UI 개편] templates/audit.html의 #tab-audit-report 영역을 '4단계 원스톱 카드 대시보드' 및 실시간 DART 뷰어로 전면 개편
Step 9.  [프론트엔드 JS 연동] static/js/audit_dsd_hub.js 신설 - DSD 드래그앤드롭, AJE 실시간 추가/삭제, 주석 탭 전환, DSD 다운로드 비동기 연동
Step 10. [E2E 통합 테스트] Flask 서버 실행 후 브라우저(/audit) 및 PowerShell에서 자료 업로드부터 최종 .dsd 파일 다운로드 및 DART 무결성 전수 검증

# 매 단계 응답 형식 (Strict Format)

## 📌 현재 단계: Step X
## 🎯 이번 단계의 목표
## 📁 수정/작성할 파일 경로
## 💻 코드 변경 내용 (전체 또는 명확한 diff)
## ⚡ Windows PowerShell 검증 명령어
## 🔍 기대 결과 및 확인 방법
## 🛑 다음 단계 안내 (사용자 '다음' 입력 대기)

# 시작 지시

지금 Step 1만 수행하고 PowerShell 검증 명령어를 제시한 뒤 멈춰라.
```

---

## 🛡️ [클라우드/Render.com 배포 표준 지침] 메모리 병목 및 OOM 방지 강제 규칙

Render.com 무료/기본 인스턴스(RAM 512MB) 및 클라우드 배포 환경에서 대용량 회계 데이터(10,000+건 전표/원장) 처리 시 발생할 수 있는 **메모리 초과(OOM / SIGKILL) 및 502/500 에러를 원천 차단**하기 위해 모든 프로젝트와 신규 기능 개발 시 다음 사항을 **절대 규칙**으로 강제화한다.

### 1. Gunicorn 프로세스 & 스레드 설정 표준 (Procfile 필수 준수)
- **멀티 워커(`--workers 2~4`) 사용 금지**: 각 워커가 512MB RAM을 쪼개어 쓰므로 대용량 연산 시 즉시 OOM이 발생함.
- **싱글 워커 + 멀티 스레드(`gthread`) 강제**:
  ```text
  web: gunicorn --workers 1 --threads 4 --worker-class gthread --timeout 120 app:app
  ```
  *(기본 상주 메모리를 100MB 이하로 유지하면서 비동기 멀티 I/O 동시 요청을 안전하게 처리)*

### 2. 사전 연산 캐싱 (Pre-computation & Cache-First) 강제화
- **실시간 무거운 전수 연산 지양**: 사용자가 대시보드를 열 때마다 수만 건의 장부를 매번 다시 파싱·연산하지 않는다.
- **업로드/동기화 시점 자동 사전 연산**:
  1. Lakehouse 데이터 동기화(`sync_normalized_lakehouse`) 시점에 5대 분석을 1회 사전 연산하여 `analytics.json`을 MinIO에 영구 적재.
  2. 모든 분석 API는 **1순위 MinIO 캐시 우선 로드(0.01초 소요, RAM 1MB 미만 소모)** 방식으로 응답.
  3. 캐시가 없는 경우에만 1회 Fallback 실시간 연산을 수행하고, 결과물을 즉시 자동 캐싱(Self-Healing).

### 3. 백엔드(Python) 메모리 관리 필수 개발 수칙
1. **이상 징후 목록 상한(Max 30~50건) 제한**:
   - JET 스캔, 키워드 탐지 등에서 전체 건수는 정밀 카운트(`count`)로 집계하되, 상세 딕셔너리 리스트는 상위 30~50개 샘플만 유지하여 수만 개의 파이썬 객체 누적을 방지한다.
2. **단계별 메모리 즉시 해제 및 명시적 GC**:
   - 대용량 데이터 로드 및 연산 완료 즉시 `del curr_bundle, prior_bundle, stmts, df`를 호출하고 `gc.collect()`를 명시적으로 실행한다.
3. **재귀 딥카피(Deep Copy) 금지**:
   - 결과 딕셔너리를 전체 복제하는 재귀 함수 대신 `nan`/`inf`/Numpy 타입만 정제하는 경량 직렬화 헬퍼(`_clean_for_json`)를 사용한다.
4. **API 라우트 `finally:` 가비지 컬렉션 의무화**:
   - API 응답 반환 직전 `finally: gc.collect()`를 호출하여 워커 프로세스 점유 메모리를 즉시 OS로 반환한다.



