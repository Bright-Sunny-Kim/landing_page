# AI 자동화 회계감사 프로젝트 마스터 가이드 (Audit Master Guide)

## 최근 업데이트 (2026-07-15) - P0(감사조서 영속화) 구현 및 실사용 검증 완료 ✅
- 2장 로드맵의 P0를 구현. FK 정합성 확보를 위해 `users.company`(텍스트, 중복 가능)를 그대로 참조하지 않고 `corporate_number`(사업자등록번호)를 자연키로 하는 `companies` 마스터 테이블을 신설, `audit_working_papers.company_id`가 이를 FK로 참조하도록 설계 (`database/audit_working_papers_schema.sql`). `users` 테이블은 `company_id` 컬럼만 추가(기존 `company` 텍스트 컬럼 및 관련 로직은 그대로 유지)하고 백필 스크립트로 기존 데이터를 연결.
- `audit_working_papers`(회사/연도/버전 + `draft→reviewed→approved` 상태 + `analysis_result_json`/`working_paper_md`)와 이력 테이블 `audit_working_paper_logs` 추가. `database/rls_setup.sql`에 신규 3개 테이블 RLS 활성화 반영.
- **저장 시점은 자동이 아니라 마스터의 명시적 액션**: 기존 `/master/audit-analyze`(계산 전용)는 그대로 두고, 신규 `POST /master/audit-working-paper/<company_name>/save`가 화면에 표시된 분석 결과를 그대로 받아 새 버전으로 저장 (`app.py`). 그 외 버전 목록 조회(`GET /master/audit-working-paper/<company_name>`), 단건 상세(`GET .../detail/<id>`), 상태전이(`POST .../<id>/status`, `draft→reviewed→approved` 순서만 허용) 라우트 추가.
- 회원가입 경로(로그인 라우트 신규가입 분기, 소셜 로그인 신규가입 분기) 두 곳 모두 신규 `corporate_number` 가입 시 `companies` 테이블에도 동기화하도록 수정 — 앞으로 가입하는 회사도 FK 매핑이 끊기지 않도록 함.
- `templates/master_detail.html`에 "조서 저장" 버튼(+ 회계연도 입력), 저장된 버전 이력 테이블(상태 배지 + "검토완료로 표시"/"승인 처리" 버튼) 추가.
- **DB 마이그레이션 실행 완료**: Supabase 콘솔에서 `audit_working_papers_schema.sql` → `rls_setup.sql` 순서로 실행 완료. `companies` 생성 및 `users.company_id` 백필 정상 확인(`corporate_number`가 있는데 연결 안 된 누락 건 0건).
- **end-to-end 실사용 검증 완료**: 마스터 화면에서 분석→저장(버전 자동 증가)→상태전이(초안→검토완료→승인완료) 전체 플로우 클릭 테스트 통과. 서버 데이터로도 버전 넘버링이 회사/회계연도별로 독립 관리되는 것과(`UNIQUE(company_id, fiscal_year, version)`), 상태전이마다 `audit_working_paper_logs`에 이력이 정확히 쌓이는 것을 교차 확인함. **P0 완료.**

## 최근 업데이트 (2026-07-15) - master.html 파이프라인 콘솔을 P0~P5 우선순위 기준으로 재구성
- 2장 우선순위 로드맵(P0~P5) 확정 후, [master.html](../templates/master.html)의 두 곳(대시보드 홈 "Audit Pipeline" 섹션 / "시스템 통계 및 리포트 → AI 자동화 파이프라인 관리" 콘솔)에 반영. 기존에는 Step 01~06 카드가 주축이고 P0~P5는 별도 목록으로 분리되어 있어 착수 순서 파악이 어려웠음.
- **구조 전환**: P0~P5 카드를 주축으로 재구성하고, Step 번호는 각 카드 안에 작은 "참고: Step 0X" 태그로만 표시. 두 우선순위에 걸친 항목(P1=Step01+04, P3=Step02+03)은 관련 Step의 설명·남은 작업·설정 필드를 하나의 카드로 병합. 실제 설정값이 없는 P0·P2는 "연결 테스트" 버튼을 넣지 않음.
- **진도표 신설**: P0→P5 가로 스텝 트래커(완료/진행중/미착수 색상 점 + 연결선 + 요약 칩)를 두 위치 모두에 추가. Step 기준으로는 "완료 1"이었으나 우선순위 실행 관점에서는 완전히 끝난 항목이 없어 "완료 0 · 진행중 2(P1, P3) · 미착수 4(P0, P2, P4, P5)"로 정직하게 표시.
- [style.css](../static/css/style.css)에 `node-ref-tag`(Step 참고 태그), `progress-tracker`(진도표) 스타일 추가, 더 이상 쓰지 않는 `priority-roadmap`/`priority-item`/`node-priority-tag` 관련 CSS 제거. [main.js](../static/js/main.js)의 핑 테스트 목 응답 조건도 `step1/step2` → `p1/p3`로 갱신.

## 최근 업데이트 (2026-07-15) - 6단계 실행 절차, 실제 구현 기준으로 재정리
- 1장·3장(현재는 4장으로 번호 이동, 아래 참조)의 6단계/세부 로드맵 설명이 "n8n Webhook 기반 설계"를 전제로 쓰여 있었으나, 실제 `/master/audit-analyze`는 n8n을 거치지 않고 Flask가 [audit_engine.py](../audit_engine.py)를 직접 호출하는 구조로 구현되어 있음을 확인. 문서와 코드 간 괴리를 없애기 위해 각 단계에 **현재 상태(완료/부분 구현/미착수)**와 **남은 작업**을 직접 붙이는 방식으로 재작성함 (기존에 별도 블록이었던 "향후 과제"는 각 단계 설명에 흡수·통합).
- n8n Webhook 자동화 연동은 원래 설계 의도대로 **향후 과제로 유지** (제거하지 않음) — 아직 미착수 상태.
- **[추가] 6단계 순번 ≠ 착수 순서임을 확인하고 우선순위 로드맵(2장)을 신설**: 6단계 구분은 실제로 (A) 1·4단계가 공유하는 수집·표준화 로직, (B) 2·3단계의 상시 지식 베이스, (C) 4→5→6을 잇는 영속 상태·승인 워크플로라는 3개 레이어로 되어 있어, 순번대로 착수하면 "산출물을 저장할 곳이 없어 5·6단계를 시작할 수 없는" 등 구조적 문제가 발생함을 확인. 이에 따라 착수 순서를 P0(영속화)~P5(교차검증 평가체계)로 재정렬(2장 참조). 기존 3장 "1단계 세부 로드맵"은 4장으로, 참조 정보는 5장으로 번호 이동.

## 최근 업데이트 (2026-07-14) - Ubuntu 단일 노드 마이그레이션 Phase 1~3 완료
- AI 감사 자동화 파이프라인(Flask + Dify + ChromaDB)의 인프라 통합(**Phase 1~2 완료, Phase 3 진행 중**). 상세: [migration_progress.md](./migration_progress.md)
- FAQ RAG 체인(Agent → Custom Tool → Flask `/api/dify/retrieval` → ChromaDB)이 `staging.hyean-dskim.com`에서 ngrok 없이 로컬 직결로 정상 작동함을 실증 확인. Dify LLM은 OpenAI가 아닌 **Gemini**로 확인됨.
- soak test 통과 후 Phase 4(DNS 전환) 진행 예정. **인프라 통합이 끝나야 아래 6단계의 남은 작업에 안정적으로 착수 가능.** (상세 상태는 1장 참조)

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


본 문서는 회계법인 혜안의 내부 시스템 고도화 작업인 **'AI 회계감사 자동화 파이프라인'** 구축을 위한 마스터 설계 및 진행 상황 요약 문서입니다. 마스터 관리자가 향후 단계별 개발을 진행할 때 본 문서를 프로젝트 컨텍스트 가이드로 활용하십시오.

---

## 1. 프로젝트 아키텍처 및 6대 절차 개요

감사업무 전반을 자동화하기 위해 프론트엔드, 자동화 엔진(n8n), AI 에이전트(Dify), 데이터베이스(Supabase)를 유기적으로 연결하는 6단계 파이프라인을 **목표**로 합니다. 다만 1~4단계는 현재 n8n 없이 **Flask가 [audit_engine.py](../audit_engine.py)를 직접 호출**하는 축약 구조로 프로토타입이 구현되어 있고, n8n 연동은 아래처럼 각 단계의 남은 작업으로 유지됩니다.

### 📊 회계감사 자동화 6단계 세부 실행 절차

1. **단계 1: 고객 제시 데이터로부터 재무제표 작성 (주석 포함)** — 🔶 부분 구현
   * **구현됨**: T/B(시산표) 업로드 → `/master/audit-analyze`가 `parse_tb_file`/`merge_multiple_tb_dfs`로 파싱·병합 → `run_variance_analysis`로 변동성 분석까지 Flask에서 직접 처리.
   * **남은 작업**:
     - n8n Webhook 트리거 연동 (원래 설계대로, 아직 미착수 — 현재는 Flask 직접 호출)
     - 계정과목 표준매핑 테이블 신설 (Supabase) — `parse_tb_file`은 현재 컬럼명 키워드 매칭(`'계정'`, `'당기'` 등)에만 의존하고, 매칭 실패 시 모의 데이터로 Fallback함
     - 표준 재무상태표(BS)/손익계산서(IS) 자동 빌더 + 대차평형 검증
     - 고객 제시 재무제표와의 Delta 비교 알고리즘, Dify 기반 차이 원인 분석 보고서 생성
2. **단계 2: 회계기준(K-GAAP/K-IFRS) 및 감사기준(K-GAAS) RAG 구축** — ✅ 완료
   * **[실무 최적화]** 크롤러 대신 관리자가 원문 PDF를 한 번 다운받아 로컬 6대 카테고리 폴더(한국채택국제회계기준, 일반기업회계기준, 특수분야회계기준 등)에 넣으면 자동으로 일괄 파싱 및 적재하는 구조(`process_local_pdfs.py`) 채택.
   * Supabase `document_chunks` 테이블과 Storage에 벡터 데이터 적재 완료.
   * **[AI FAQ 프론트엔드 연동]** 파트너 전용 대시보드(`company.html`) 내에 Glassmorphism 챗봇 UI를 구축하고, Flask 백엔드 `/api/faq/ask` 라우트를 통해 OpenAI 임베딩 및 ChatCompletion과 Supabase HNSW 인덱싱 검색을 결합하여 실시간 AI 질의응답 서비스 상용화 완료.
3. **단계 3: DART 감사보고서 DB 구축 (RAG)** — 🔶 스키마·스크립트만 존재, 미가동
   * **구현됨**: `dart_audit_reports`/`dart_report_chunks` 테이블 스키마, `scripts/dart_crawler.py`(OpenDART API 호출·Upsert), `scripts/dart_document_parser.py`(문서 파싱·청킹·임베딩).
   * **남은 작업**: n8n 또는 cron 스케줄러로 정기 실행 연결 — 현재 실데이터 적재 이력 없음.
4. **단계 4: 항목별 감사조서 및 감사절차 작성** — 🔶 부분 구현 (조서 생성 + 영속화 완료, 인쇄 내보내기만 남음)
   * **구현됨**: `/master/audit-analyze` API가 K-GAAP RAG 매칭(`retrieve_k_gaap`)까지 거쳐 3단계 구조('감사 목표 - 수행 절차 - 감사 결과 및 결론')의 마크다운 감사조서를 `generate_working_paper`로 합성. `master_detail.html`에 결과 바인딩 및 원본 `.md` 다운로드 버튼까지 연결 완료.
   * **감사조서 영속화 완료 (P0)**: `audit_working_papers` 테이블(회사/연도/버전 + `draft→reviewed→approved` 상태)에 저장하는 `POST /master/audit-working-paper/<company>/save`(마스터의 명시적 "조서 저장" 클릭 시에만 새 버전 생성) + 버전 이력 조회/상태전이 라우트, `master_detail.html` UI, DB 마이그레이션, end-to-end 실사용 검증까지 전부 완료. 상세는 상단 "최근 업데이트" 참조.
   * **남은 작업**:
     - PDF/Word 정식 내보내기 — 현재는 raw markdown(`.md`) 다운로드만 가능. `doc_quote.html` 등 기존 `window.print()` A4 템플릿 패턴을 재사용해 조서 인쇄 템플릿 제작
5. **단계 5: 감사보고서 초안 작성** — ⏸ 미착수
   * **남은 작업**: 작성된 감사조서(4단계) + DART 유사 감사보고서 DB(3단계) 결합해 의견문단/주석 초안을 자동 산출하는 `/master/audit-report-draft` 라우트 신설.
6. **단계 6: 작성된 감사보고서 교차 검증 (Verification)** — ⏸ 미착수
   * **남은 작업**: 두 번째 LLM 패스(Dify reviewer)로 K-GAAS 체크리스트 대조 → 논리적 오류 검증 → 마스터 승인 시 확정 처리하는 워크플로 구축.

### ⚙️ 기술 스택 및 인프라 매핑
* **프론트엔드 & API**: Python Flask (Render 배포)
* **데이터 처리 및 연결망**: n8n, PostgreSQL 16
* **AI 에이전트 및 추론**: Dify (Docker 배포)
* **데이터 및 벡터 저장소**: Supabase (pgvector), Nextcloud

---

## 2. 우선순위 로드맵 (3-레이어 아키텍처 기준, 2026-07-15 재정렬)

6단계 순번(1→2→3→4→5→6)은 문서·UI에서 설명용 서사로는 유지하지만, 실제 착수 순서는 이 번호와 다릅니다. 기술적 의존관계를 분석한 결과 6단계는 실제로 3개 레이어로 묶여 있습니다.

* **레이어 A (수집·표준화)**: 1단계(재무제표 작성) + 4단계(감사조서 작성)가 **동일한 T/B 파싱 로직을 중복 호출**하고 있음 (`/master/audit-analyze`가 `parse_tb_file`을 직접 호출) — 하나로 통합 필요.
* **레이어 B (지식 베이스)**: 2단계(K-GAAP/GAAS RAG) + 3단계(DART RAG) — 한 번 만들고 끝나는 단계가 아니라 4·5·6단계가 계속 질의하는 **상시 유지보수 트랙**.
* **레이어 C (생성·검토 워크플로)**: 4→5→6단계는 순차적으로 이어져야 하는데, 지금은 결과물(`working_paper_md`)이 저장되지 않고 매번 재계산되어 **넘겨줄 산출물 자체가 없음** — 영속화 및 상태(승인) 관리가 선행되어야 함.

### 다음 착수 순서 (P0 → P5)

| 우선순위 | 작업 | 관련 단계 | 상태 | 이 순서인 이유 |
|---|---|---|---|---|
| **P0** | 감사조서/분석 결과 영속화 — `audit_working_papers` 테이블(회사/연도/버전 + `draft→reviewed→approved` 상태) 신설 | 4단계 직접 해당, 5·6단계 선행조건 | ✅ 완료 | 저장 공간이 없으면 5·6단계는 이어붙일 결과물 자체가 없어 물리적으로 시작 불가 — 전체 로드맵의 선행 조건 |
| **P1** | 1단계·4단계 T/B 파싱 로직 통합 (표준 BS/IS 빌더, 대차평형 검증, Delta 비교 알고리즘 포함) | 1단계, 4단계 | 🔶 코드에 중복 이미 존재 | 지금 두 단계가 각자 파싱 중이라 하나를 고치면 다른 하나가 깨지는 이중 유지보수 상태. P0에서 만든 저장소에 표준화 데이터를 남기고 4단계가 재파싱 대신 이를 읽도록 통합 |
| **P2** | 계정과목 표준매핑 — **부분 자동화 + 수동 오버라이드**로 설계 (완성형 매핑 X) | 1단계, 4단계 | ⏸ 미착수 | 회사가 늘수록 규칙이 계속 느는 롱테일 문제라 "다 매핑하고 다음으로" 방식은 무기한 막힐 위험. 매칭 실패 시 마스터 수동 지정 → 다음부터 자동 반영되는 구조로 시작 |
| **P3** | RAG 지식 베이스 유지보수 (상시 트랙, 병행 가능) — DART 크롤러 n8n/cron 정기 실행 연결 | 2단계(✅ 운영 중이나 커버리지 관리 필요), 3단계(🔶 미가동) | 진행 중 | 순번상 3번째 단계라서 여기서 진행하는 게 아니라 **P0~P2와 병행 가능한 독립 서비스**. 급하지 않으면 후순위로 미뤄도 P1·P2에 지장 없음 |
| **P4** | 감사보고서 초안 생성 라우트(`/master/audit-report-draft`) 신설 | 5단계 | ⏸ 미착수 | P0(영속화) 완료 전에는 착수 무의미 — 조서 결과를 안정적으로 읽어올 방법이 없음 |
| **P5** | 교차검증 워크플로 — **구현보다 평가 방법론(ground truth) 정의가 먼저** | 6단계 | ⏸ 미착수 | "AI가 AI를 검토"하는 로직은 정답 세트 없이는 잘 작동하는지 판단 기준이 없어 무기한 막힐 위험이 가장 큰 항목. 실제 감사보고서 샘플에 대한 기대 결과를 먼저 정의한 뒤 구현 착수 |

### 진행 원칙
1. **기존 프로토타입을 먼저 교체하지 않는다** — 새 로직(표준매핑, 영속화 등)은 지금 동작하는 `/master/audit-analyze` 위에 얹는 방식으로 추가하고, 실패 시 현재 방식(키워드 매칭)으로 자동 폴백되게 한다.
2. **자동화가 막혀도 마스터가 수동으로 감사 업무를 계속할 수 있는 경로를 항상 유지한다.**

---

## 3. 관리자 포털 UI 고도화 반영 내역

회계감사 자동화 파이프라인은 내부 보안이 요구되는 사항이므로 일반 고객용 페이지에서 철저히 격리하고, 최고 관리자(`cpaeastsun@gmail.com`)용 화면에 관리 콘솔로 구축 완료했습니다.

* **로그인 페이지 롤백** ([login.html](file:///c:/Users/CLAUD/landing_page/templates/login.html)):
  * 하단에 구현했던 소개 영역을 전면 삭제하고 캐시 갱신 롤백을 진행하여 컴팩트한 기존 로그인 폼으로 완벽 복구했습니다.
  * `body` 레이아웃 스타일([style.css](file:///c:/Users/CLAUD/landing_page/static/css/style.css))을 정중앙 정렬로 복원했습니다.
* **시스템 통계 내 서브 탭 이식** ([master.html](file:///c:/Users/CLAUD/landing_page/templates/master.html) 및 [main.js](file:///c:/Users/CLAUD/landing_page/static/js/main.js)):
  * `시스템 통계 및 리포트(analytics)` 메뉴 클릭 시 실제 정적 요소인 `#analytics-dashboard-view`가 활성화됩니다. (화면 이동 시 입력값 유지 보장)
  * 상단 서브 탭 바를 통해 `📈 시스템 경영 통계`와 `⚙️ AI 자동화 파이프라인 관리` 뷰를 즉시 토글할 수 있습니다.
  * 6대 노드가 세련된 수직 결합 구조로 노출되며, 클릭 시 아코디언 형태로 세부 폼(Webhook 설정, API Key 입력란)과 **연결 테스트(Ping)** 버튼이 표시됩니다.
  * 연결 테스트 클릭 시 가상 딜레이(1.2초)를 가진 비동기 연결 시뮬레이션 결과가 상태 표시기에 안전하게 업데이트됩니다.

---

## 4. [P1·P2 상세] 1단계 고도화 세부 개발 로드맵 (7대 실행 절차)

2장 우선순위 로드맵의 **P1(파싱 로직 통합)·P2(계정과목 표준매핑)**에 해당하는 세부 항목입니다. 각 항목에 현재 구현 상태를 표시합니다.

1. **다양한 파일 포맷 파싱 및 표준화 엔진 고도화** — 🔶 부분 구현
   * CSV(UTF-8/CP949 fallback)·Excel 파싱과 다중 파일 병합(`merge_multiple_tb_dfs`)까지는 되어 있으나([audit_engine.py](file:///c:/Users/CLAUD/landing_page/audit_engine.py)), 칼럼 매핑이 `AccountName`/`Debit`/`Credit`처럼 정식 표준 구조가 아니라 컬럼명 키워드 매칭(`parse_tb_file`)에만 의존 — 회사마다 다른 양식에 취약함.
2. **표준 계정과목 매핑 딕셔너리 구축** — ⏸ 미착수
   * 피감사인의 잡다한 비표준 계정명을 회계법인 표준 코드(예: 보통예금 ➔ 10100 현금및현금성자산)로 자동 합산 및 분류해 줄 마스터 매핑 규칙 데이터베이스 테이블을 Supabase에 구축합니다.
3. **표준 재무상태표(BS) & 손익계산서(IS) 자동 산식 빌더 구현** — ⏸ 미착수
   * 매핑이 완료된 표준 계정과목 데이터를 합산하여 표준 BS 및 IS 양식을 자동으로 구성하는 빌더 모듈을 작성하고, 대차평형(자산=부채+자본) 검증 공식을 도입합니다.
4. **고객 제시 재무제표와의 차이(Delta) 검토 알고리즘 구현** — ⏸ 미착수
   * 시산표 잔액 기준 자동 재무제표와 피감사인이 직접 작성해 제시한 재무제표 드래프트 수치 간의 불일치 항목 및 차이 금액을 자동 계산하는 연산 알고리즘을 짭니다.
5. **n8n 자동화 Webhook 파이프라인 연동** — ⏸ 미착수 (향후 과제로 유지)
   * 파일 업로드 완료 시 n8n Webhook이 트리거되어 위 파이썬 정제 스크립트를 호출하고 가공 데이터를 Supabase DB 테이블에 자동 적재하도록 연동합니다. 현재는 이 단계를 거치지 않고 Flask가 직접 처리합니다.
6. **Dify API 연동을 통한 차이 원인 분석 및 수정 보고서 생성** — ⏸ 미착수
   * 차이가 발생한 Delta 항목 리스트를 Dify API로 전송하여 AI가 회계학적 원인 분석 보고서 마크다운을 자동 반환하도록 프롬프트 체인을 구축합니다. (4단계 감사조서 생성에 쓰이는 K-GAAP RAG 질의와는 별개 기능)
7. **마스터 포털 대시보드 UI 연계 및 시각화** — ✅ 완료
   * 정제 완료된 재무제표 테이블 및 AI 분석 보고서가 해당 파트너사 관리자 상세 페이지([master_detail.html](file:///c:/Users/CLAUD/landing_page/templates/master_detail.html))에 실시간 바인딩되어 렌더링되며, 원본 마크다운 `.md` 다운로드까지 연결되어 있습니다.

---

## 5. 관련 참조 정보 및 문서

* **디자인 시스템 및 CSS 가이드**: [css_master.md](file:///c:/Users/CLAUD/landing_page/css_master.md) (디자인 유지보수 시 필수 참조)
* **데이터베이스 스키마 정의**: [supabase_schema.sql](file:///c:/Users/CLAUD/landing_page/database/supabase_schema.sql)
* **핵심 백엔드 로직 파일**: [audit_engine.py](file:///c:/Users/CLAUD/landing_page/audit_engine.py) 및 [app.py](file:///c:/Users/CLAUD/landing_page/app.py)


## [2026-06-16] AI 회계기준 어시스턴트(RAG) 고도화 및 버그 수정
- **앱 백엔드 (pp.py)**: /api/faq/ask 라우트에서 OpenAI 및 Supabase 클라이언트 지연 초기화 적용. 프롬프트를 결론-설명-출처 구조로 개선.
- **문서 파싱 (chunker_standards.py)**: 회계기준서 청킹 정규식을 정교화하여 날짜/수식 오인식 방지. 8192 토큰 제한 초과 방지를 위해 3000자 초과 청크 자동 분할.
- **문서 업로드 (process_local_pdfs.py)**: 한글(Non-ASCII) 문자열로 인한 Supabase InvalidKey 에러 해결을 위해 카테고리 영문화 및 영문+해시 파일명 변환 적용.
- **UI 변경 (company.html)**: 담당 회계사 문의 탭 이름을 AI 회계사 문의로 변경.


## [2026-06-16] K-IFRS 문단 분할(Chunking) 고도화 적용
- **K-IFRS 정규식 추가 (chunker_standards.py)**: 1, 102A, 한1, B1, IE1 등 K-IFRS 고유의 복잡한 문단 번호 패턴을 완벽히 인식하여 분할하도록 ifrs_pattern 적용.
- **카테고리 연동 (process_local_pdfs.py)**: 문서의 카테고리 정보(category)를 Chunker 모듈로 전달하여, K-GAAP과 K-IFRS가 각각 자신에게 맞는 정규식을 동적으로 선택하도록 개선.


## [2026-06-16] K-IFRS 폴더 및 카테고리 병합 적용
- **폴더 구조 단순화**: 기존 한국채택국제회계기준(K-IFRS)(시행중) 및 (조기적용가능) 폴더를 한국채택국제회계기준(K-IFRS) 단일 폴더로 통합.
- **카테고리 매핑 수정 (process_local_pdfs.py)**: 스크립트가 단일 통합 폴더를 정상 인식하고 K-IFRS 영문 스토리지 경로로 업로드하도록 CATEGORIES 및 CATEGORY_MAP 설정 업데이트.

## [2026-06-26] 금융기관 조회업무 신청 시스템 고도화 적용
- **DB 및 백엔드**: 금융기관, 신청원장, 이력 관리 테이블 설계 완료 및 관리자용 세부 업데이트, 엑셀 다운로드 API(app.py) 구축 완료.
- **프론트엔드 연동**: 고객 대시보드(company.html) 상태별 요약 카드 및 3-Step 신청 폼 연결 완료. 관리자 대시보드(master.html) 상태 일괄 수정 및 상세 조회 기능 이식 성공.
