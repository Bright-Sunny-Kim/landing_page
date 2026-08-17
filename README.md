# 🏢 HEYAN 마스터 기업 정밀 분석 시스템 (Enterprise Financial Analytics & Audit Hub)

> **고객이 제출한 5대 회계자료(재무상태표, 손익계산서, 합계잔액시산표, 분개장, 거래처원장)를 기반으로 100% 결정론적 정규화 파싱, 4대 재무비율 벤치마크, ISA 240 JET 이상전표 전수 스캔, 거래처 리스크 분석, 사내 로컬/Ubuntu 서버 안전 영속화 및 K-GAAP RAG 감사 조서(Working Paper)를 자동 산출하는 차세대 종합 분석 솔루션**

---

## 📌 1. 시스템 개요 및 주요 기능

본 시스템은 공인회계사 및 세무 전문가가 기업의 결산 서류와 회계 원장을 원클릭으로 정밀 진단할 수 있도록 구축된 **풀스택 감사/분석 엔진**입니다.

### 🌟 핵심 역량 및 고도화 완료 기능
1. **100% Python 결정론적 정규화 파싱 엔진 (Zero-Hallucination Parser)**:
   - LLM AI의 추론에 의존하지 않고 순수 파이썬 알고리즘으로 5대 회계장부 전수 파싱
   - ERP(더존 Smart A, 세무사랑, 위하고, 이카운트 등)의 복합 서식 엑셀(`.xlsx`, `.xls`) 및 `.csv` 자동 인식
   - 차감계정(대손충당금, 감누액) 자동 음수화, 괄호 번호(`(1)`, `(2)`) 및 주석행 완벽 필터링
2. **수집 현황 및 대차 무결성 가로형 2행(당기/전기) Health Matrix Dashboard**:
   - 상단 분석 컨트롤 패널과 동일한 가로 Full-Width 레이아웃으로 당기(2025년)와 전기(2024년) 2개 행 매트릭스 표출
   - 5대 장부별 수집 상태(`🟢 정상 126건`), 연도별 파일명, 대차평형 여부, 수집 무결성 점수(`100점`) 실시간 표출
   - **데이터 원본 인스펙터 모달**: 표(Table) 뷰와 JSON 원본 뷰 전환 열람 및 [📋 JSON 복사] 지원
3. **사내 폐쇄형 로컬 보관함 & 사내 Ubuntu 서버 확장 하이브리드 스토리지**:
   - 외부 클라우드로 회계 데이터가 유출되지 않도록 `uploads/작업완료_보관함/<기업명>/`에 자동 저장
   - 사내 Ubuntu 서버(PostgreSQL / Remote Mount) 환경설정 지원으로 손쉬운 엔터프라이즈 확장
   - **0.01초 초고속 복원**: 과거 분석 데이터를 재파싱 없이 0.01초 만에 화면 전체로 복원
4. **기준연도 동적 타겟팅 (Fiscal Year Dynamic Targeting)**:
   - 드롭다운 선택(2025년 당기 / 2024년 전기 등)에 따라 다중 연도 파일 중 해당 연도 자료를 최우선으로 선별 집계
5. **4대 재무비율 & 한국은행 벤치마크 진단**:
   - 안정성(부채비율, 유동비율, 당좌비율, 차입금의존도, 이자보상배율)
   - 수익성(영업이익률, 순이익률, ROE, ROA)
   - 성장성(매출성장률, 영업이익성장률, 총자산증가율, 순이익증가율)
   - 활동성(매출채권회전율/DSO, 재고자산회전율/DIO)
6. **ISA 240 분개장 저널 엔트리 테스팅 (JET Anomaly Detection)**:
   - 전표번호 그룹핑, 대차평형(`∑차변 == ∑대변`) 무결성 검증
   - 주말/공휴일 전표, 쪼개기(Smurfing) 거래, 라운드 넘버(000,000원 단위), 가지급금/가수금 대체, 분식 위험 키워드 전수 스캔
7. **거래처원장 리스크 & 채권 연령(Aging) 분석**:
   - 상위 5대 매출처 집중도(Top 5 Concentration) 산출
   - 180일 및 365일 이상 장기 미회수 부실 채권 식별 및 동일 상호 매출/매입 양방향 상계 대상 대사
8. **K-GAAP RAG 감사 조서 자동 작성 & 영속화**:
   - 일반기업회계기준(K-GAAP) 임베딩 벡터 RAG 검색 연동
   - 전문 마크다운(`.md`) 감사 보고서 실시간 렌더링, 클립보드 복사, 파일 다운로드

---

## 🏛️ 2. 시스템 아키텍처 및 파일 구조

```text
landing_page/
├── core/
│   ├── audit_engine.py          # 5대 회계자료 파서, 무결성 번들 빌더, 재무비율 계산기, JET 스캐너, K-GAAP RAG
│   ├── storage_manager.py       # [Phase 3/확장] 사내 로컬 보관함 및 Ubuntu 서버 하이브리드 스토리지 어댑터
│   └── extensions.py            # Supabase, ChromaDB, OpenAI 임베딩 및 글로벌 로거 설정
├── blueprints/
│   └── master.py                # 마스터 관리자 엔드포인트 (/master/api/analyze-*, /datasets/local-*, /storage/status 등)
├── templates/
│   └── master.html              # 수집 현황 5-Pill 그리드, 데이터 인스펙터 모달, 과거 보관함 로드 바, 조서 뷰어
├── static/
│   ├── js/
│   │   ├── main.js              # 탭 라우팅 및 전역 이벤트 핸들러
│   │   └── master_analytics.js  # 수집 현황 렌더러, 인스펙터 모달, 로컬 보관함 0.01초 복원 엔진
│   └── css/
│       └── style.css            # 수집 현황 카드 호버 효과, 모달 테이블, @media print 최적화
└── uploads/
    ├── 고객제시자료/            # 고객 제출 엑셀 원본 보관함
    └── 작업완료_보관함/          # [사내 로컬 폐쇄형 보관함] 기업별 일자/연도별 정규화 JSON 및 MD 조서
```

---

## 🔌 3. REST API 엔드포인트 명세

| Method | Endpoint | 설명 | 주요 Request Parameters | 주요 Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/master/api/analyze-direct` | 엑셀 직접 업로드, 결정론적 정규화 파싱 및 자동 로컬 영속화 | `company_name`, `fiscal_year`, `files[]` | `normalized_bundle`, `ingestion_health`, `summary`, `ratios`, `jet_anomalies`, `report_md` |
| `POST` | `/master/api/analyze-company/<name>` | 고객사 스토리지 자료 원클릭 분석 및 자동 로컬 영속화 | JSON: `{ "fiscal_year": "2025" }` | `normalized_bundle`, `ingestion_health`, `summary`, `ratios`, `jet_anomalies`, `report_md` |
| `GET` | `/master/api/datasets/local-list/<name>` | 사내 로컬/Ubuntu 보관함에 저장된 과거 분석 데이터셋 목록 조회 | URL Parameter: `company_name` | `{ "datasets": [{ "filename", "fiscal_year", "saved_at", "size_bytes", "source" }] }` |
| `GET` | `/master/api/datasets/local-load` | 과거 보관본 JSON을 재파싱 없이 0.01초 만에 즉시 복원 로드 | Query: `?company_name=...&filename=...` | 전체 분석 페이로드 (`normalized_bundle`, `summary`, `report_md` 등) |
| `GET` | `/master/api/storage/status` | 사내 로컬 보관함 및 사내 Ubuntu 서버 연결 상태 메타데이터 조회 | Header: Admin Session | `{ "mode": "hybrid", "local_storage": {...}, "ubuntu_server": {...} }` |
| `POST` | `/master/api/save-analysis` | 분석 결과 및 조서 수동 영속화 저장 | JSON: `{ "company_name", "fiscal_year", "analysis_data", "report_md" }` | `{ "success": true, "archive_info": {...} }` |

---

## 💾 4. 하이브리드 스토리지 확장 가이드 (사내 Ubuntu Server)

사내 별도의 Ubuntu 서버로 확장을 원할 경우, `.env` 파일에 다음 항목을 지정하기만 하면 즉시 연동됩니다:

```bash
# STORAGE_MODE: 'local' (로컬 전용), 'ubuntu_server' (Ubuntu 전용), 'hybrid' (로컬+Ubuntu 동시 저장)
STORAGE_MODE=hybrid

# 방안 1) 사내 Ubuntu 서버 마운트 경로 지정 (NFS / Samba / SFTP)
UBUNTU_ARCHIVE_PATH=/mnt/audit_lakehouse/uploads

# 방안 2) 사내 Ubuntu PostgreSQL Database 연결 (선택 사항)
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
- [ ] **Phase 4. 향후 다각적 분석 허브 로드맵**:
  - **시계열 다개년 추세 분석 (Multi-year Trend)**: 3~5개년도 저장본 결합 분석
  - **동종업계 피어 그룹 교차 비교 (Cross-sectional Peer Benchmarking)**
  - **세무조정 및 심층 포렌식 연계 (Tax Adjustment & Forensic)**
