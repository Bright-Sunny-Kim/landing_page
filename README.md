# 🏢 HEYAN 마스터 기업 정밀 분석 시스템 (Enterprise Financial Analytics & Audit Hub)

> **고객이 제출한 5대 회계자료(재무상태표, 손익계산서, 합계잔액시산표, 분개장, 거래처원장)를 기반으로 자동 파싱, 4대 재무비율 벤치마크, ISA 240 JET 이상전표 전수 스캔, 거래처 리스크 분석, K-GAAP RAG 매핑 및 감사 조서(Working Paper)를 자동 산출하는 종합 분석 솔루션**

---

## 📌 1. 시스템 개요 및 주요 기능

본 시스템은 공인회계사 및 세무 전문가가 기업의 결산 서류와 회계 원장을 원클릭으로 정밀 진단할 수 있도록 구축된 **풀스택 감사/분석 엔진**입니다.

### 🌟 6대 핵심 역량
1. **5대 회계자료 스마트 파싱 (Multi-format Parsing)**:
   - ERP(더존 Smart A, 세무사랑, 위하고, 이카운트 등)에서 내려받은 복합 서식 엑셀(`.xlsx`, `.xls`) 및 `.csv`를 1초 만에 자동 판별 및 데이터 정규화
   - 5열 레이아웃(세부/소계 분리), 글자 공백 정규화, 로마자 접두사(`Ⅰ. Ⅱ. Ⅹ.`) 및 특수문자 제거
2. **기준연도 동적 타겟팅 (Fiscal Year Dynamic Targeting)**:
   - 드롭다운 선택(2025년 당기 / 2024년 전기 등)에 따라 다중 연도 파일 중 해당 연도 자료를 최우선으로 선별 집계
3. **4대 재무비율 & 한국은행 벤치마크 진단**:
   - 안정성(부채비율, 유동비율, 당좌비율, 차입금의존도, 이자보상배율)
   - 수익성(영업이익률, 순이익률, ROE, ROA)
   - 성장성(매출성장률, 영업이익성장률, 총자산증가율, 순이익증가율)
   - 활동성(매출채권회전율/DSO, 재고자산회전율/DIO)
4. **ISA 240 분개장 저널 엔트리 테스팅 (JET Anomaly Detection)**:
   - 전표번호 그룹핑, 대차평형(`∑차변 == ∑대변`) 무결성 검증
   - 주말/공휴일 전표, 3만원/50만원/100만원 한도직하 쪼개기(Smurfing) 거래, 라운드 넘버(000,000원 단위), 가지급금/가수금 대체, 분식 위험 키워드 전수 스캔 (위험도 0~100점 산출)
5. **거래처원장 리스크 & 채권 연령(Aging) 분석**:
   - 거래처별 총괄잔액 서식 및 일자별 원장 서식 전수 지원
   - 상위 5대 매출처 집중도(Top 5 Concentration) 산출
   - 180일(6개월) 및 365일(1년) 이상 장기 미회수/정체 부실 채권 자동 식별
   - 동일 상호 매출/매입 양방향 상계 대상 거래처 대사
6. **K-GAAP RAG 감사 조서 자동 작성 & 영속화**:
   - 일반기업회계기준(K-GAAP) 임베딩 벡터 RAG 검색 연동
   - 전문 마크다운(`.md`) 감사 보고서 실시간 렌더링, 클립보드 복사, 파일 다운로드, Supabase DB 영속화 저장

---

## 🏛️ 2. 시스템 아키텍처 및 파일 구조

```text
landing_page/
├── core/
│   ├── audit_engine.py          # 5대 회계자료 파서, 재무비율 계산기, JET 스캐너, 거래처 리스크, K-GAAP RAG 및 보고서 생성 코어
│   └── extensions.py            # Supabase, ChromaDB, OpenAI 임베딩 및 글로벌 로거 설정
├── blueprints/
│   └── master.py                # 마스터 관리자 엔드포인트 (/master/api/analyze-direct, /analyze-company, /save-analysis 등)
├── templates/
│   └── master.html              # 마스터 포털 UI (기업 정밀 분석 Hub 컨테이너, Glassmorphism 그리드, 조서 뷰어)
├── static/
│   ├── js/
│   │   ├── main.js              # 탭 라우팅 및 전역 이벤트 핸들러
│   │   └── master_analytics.js  # 기업 분석 비동기 통신, 드래그앤드롭, 동적 렌더링, DB 영속화, MD 다운로드
│   └── css/
│       └── style.css            # 기업 분석 전용 반응형 그리드, KPI 카드, 뱃지, 커스텀 스크롤바, @media print
└── uploads/
    └── 고객제시자료/            # 실제 기업 결산자료 (.xlsx, .xls) 보관함
```

---

## 🔌 3. REST API 엔드포인트 명세

| Method | Endpoint | 설명 | 주요 Request Parameters | 주요 Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/master/api/analyze-direct` | 엑셀 다중 파일 직접 업로드 및 실시간 종합 분석 | `company_name`, `fiscal_year`, `files[]` (Multipart) | `summary`, `ratios`, `jet_anomalies`, `subledger_risks`, `report_md` |
| `POST` | `/master/api/analyze-company/<name>` | 등록된 고객사 스토리지 회계자료 원클릭 분석 | JSON: `{ "fiscal_year": "2025", "selected_file_ids": [] }` | `summary`, `ratios`, `jet_anomalies`, `subledger_risks`, `report_md` |
| `POST` | `/master/api/save-analysis` | 분석 결과 및 조서 영속화 저장 | JSON: `{ "company_name", "fiscal_year", "analysis_data", "report_md" }` | `{ "success": true, "record_id": ..., "version": ... }` |
| `GET` | `/master/api/analysis-history/<name>` | 고객사별 과거 분석 조서 이력 조회 | URL Parameter | `history: [{ "id", "version", "fiscal_year", "created_at" }]` |

---

## 📊 4. 5대 회계자료별 지원 서식 및 파싱 규칙

1. **재무상태표 (Balance Sheet)**:
   - 파일명/시트명: `*재무*`, `*bs*`, `*balancesheet*`
   - 열 구조: `[0: 과목명 | 1: 당기 세부 | 2: 당기 소계/합계 | 3: 전기 세부 | 4: 전기 소계/합계]`
   - 로마자/소계(`Ⅰ. 유동자산`, `(1) 당좌자산`)와 개별 말단 계정 자동 분리
2. **손익계산서 (Income Statement)**:
   - 파일명/시트명: `*손익*`, `*is*`, `*pl*`, `*incomestatement*`
   - 열 구조: `[0: 과목명 | 1: 당기 세부 | 2: 당기 소계/합계 | 3: 전기 세부 | 4: 전기 소계/합계]`
   - `Ⅹ. 당기순이익` 정규화 및 `당기순이익(Current / Prior)` 정확 집계
3. **합계잔액시산표 (Trial Balance)**:
   - 파일명/시트명: `*합잔*`, `*시산표*`, `*tb*`, `*trialbalance*`
   - 열 구조: `[0: 차변잔액 | 1: 차변합계 | 2: 계정과목 | 3: 대변합계 | 4: 대변잔액]`
   - `◀ ▶`, `◁ ▷` 소계 분리 및 연간 3각 대차평형 검증
4. **분개장 (Journal Entries)**:
   - 파일명/시트명: `*분개*`, `*전표*`, `*journal*`
   - 열 구조: `[0: 전표일자 | 1: 전표번호 | 2: 구분 | 3: Code | 4: 계정과목 | 5: 차변 | 6: 대변 | 7: 거래처 | 9: 적요]`
   - `[일자+전표번호]` 기반 그룹핑, 입금/출금/대체전표 분류, 상대계정 매핑
5. **거래처원장 (Subledger)**:
   - 파일명/시트명: `*거래처*`, `*원장*`, `*subledger*`
   - 열 구조: `[0: 코드 | 1: 계정과목 | 2: 전기이월 | 3: 차변발생 | 4: 대변발생 | 5: 거래처명/기말잔액]`
   - 1거래처 1행 총괄 연간 잔액 및 일자별 원장 서식 동시 지원

---

## 💾 5. 데이터베이스 영속화 스키마 (Supabase)

### `audit_working_papers` 테이블
```sql
CREATE TABLE IF NOT EXISTS public.audit_working_papers (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT REFERENCES public.users(id),
    company_name VARCHAR(255) NOT NULL,
    fiscal_year INTEGER NOT NULL DEFAULT 2025,
    version INTEGER NOT NULL DEFAULT 1,
    summary_data JSONB NOT NULL,
    ratios_data JSONB NOT NULL,
    jet_data JSONB NOT NULL,
    subledger_data JSONB NOT NULL,
    working_paper_md TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
*(Supabase 미연결 환경에서는 `uploads/작업완료_보관함/audit_working_papers_backup.json`으로 자동 로컬 백업됩니다.)*

---

## 🚀 6. 향후 고도화 로드맵 (Next Milestones)

- [ ] **1. DART 전자공시 API 실시간 대사**: 외감/상장 기업의 경우 DART 공시 재무제표와 업로드 엑셀 간의 자동 대사 기능 결합
- [ ] **2. 국세청 홈택스 전자세금계산서 스크래핑 연동**: 세금계산서 합계표와 장부상 외상매출/매입금 간의 실시간 불부합 검증
- [ ] **3. PDF 감사 보고서 익스포트**: 마크다운 뷰어 내용을 회계법인 표준 양식의 스타일링된 PDF로 1초 출력
- [ ] **4. 벤포드의 법칙(Benford's Law) 추가**: 분개장 금액의 첫째 자리 수 분포 분석을 통한 인위적 조작 전표 고도화 탐지
