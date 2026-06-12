# AI 자동화 회계감사 프로젝트 마스터 가이드 (Audit Master Guide)

본 문서는 회계법인 혜안의 내부 시스템 고도화 작업인 **'AI 회계감사 자동화 파이프라인'** 구축을 위한 마스터 설계 및 진행 상황 요약 문서입니다. 마스터 관리자가 향후 단계별 개발을 진행할 때 본 문서를 프로젝트 컨텍스트 가이드로 활용하십시오.

---

## 1. 프로젝트 아키텍처 및 6대 절차 개요

감사업무 전반을 자동화하기 위해 프론트엔드, 자동화 엔진(n8n), AI 에이전트(Dify), 데이터베이스(Supabase)를 유기적으로 연결하여 아래의 6단계 파이프라인을 구축합니다.

### 📊 회계감사 자동화 6단계 세부 실행 절차
1. **단계 1: 고객 제시 데이터로부터 재무제표 작성 (주석 포함)**
   * 결산 자료(T/B, 원장) 업로드 ➔ n8n Webhook 트리거 ➔ 파이썬 노드로 데이터 정제 및 표준 계정 코드 매핑 ➔ 표준 재무제표 빌드 ➔ Dify API로 차이 내역(Delta) 분석 및 수정 보고서 생성.
2. **단계 2: 회계기준(K-GAAP) 및 감사기준(K-GAAS) RAG 구축**
   * 기준서 원문 PDF/Text를 Nextcloud에 아카이빙 ➔ Dify 지식(Knowledge) 모듈을 이용해 텍스트 분할 및 벡터 임베딩 ➔ AI 감사 절차 판별의 준거 마련.
3. **단계 3: DART 감사보고서 DB 구축 (RAG)**
   * n8n 스케줄러(Cron)로 OpenDART API 호출 ➔ 동종 업계 기존 감사보고서 다운로드 및 청크화 ➔ Supabase pgvector에 임베딩 벡터값과 함께 저장 (초안 모범 문구 검색 기반).
4. **단계 4: 항목별 감사조서 및 감사절차 작성**
   * Flask 종합 분석 API 가동 ➔ Outlier 및 변동성 주요 계정에 대해 Dify 내 RAG 지식 베이스 질의 ➔ AI 에이전트가 3단계 구조('감사 목표 - 수행 절차 - 감사 결과 및 결론')의 마크다운 감사조서 합성.
5. **단계 5: 감사보고서 초안 작성**
   * 작성된 감사조서(4단계) + DART 유사 감사보고서 DB(3단계 벡터 검색 결과) 결합 ➔ Dify 메인 에이전트가 주석을 포함한 감사보고서 최종 초안 자동 산출.
6. **단계 6: 작성된 감사보고서 교차 검증 (Verification)**
   * 초안을 K-GAAS 규정에 대조하여 Dify 내 별도의 검수용(Reviewer) 에이전트가 교차 평가 및 논리적 오류 검증 ➔ 통과 시 완료 처리 및 피드백 전달.

### ⚙️ 기술 스택 및 인프라 매핑
* **프론트엔드 & API**: Python Flask (Render 배포)
* **데이터 처리 및 연결망**: n8n, PostgreSQL 16
* **AI 에이전트 및 추론**: Dify (Docker 배포)
* **데이터 및 벡터 저장소**: Supabase (pgvector), Nextcloud

---

## 2. 관리자 포털 UI 고도화 반영 내역

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

## 3. [단계 1] 고도화 세부 개발 로드맵 (7대 실행 절차)

향후 가장 먼저 구축에 나설 1단계(고객 제시 데이터로부터 재무제표 작성)의 구체적인 세부 로드맵입니다.

1. **다양한 파일 포맷 파싱 및 표준화 엔진 고도화**:
   * 피감사인이 업로드하는 다양한 엑셀/CSV 시산표(T/B) 파일의 칼럼 명칭을 Pandas를 이용해 표준 구조(`AccountName`, `Debit`, `Credit`, `Balance`)로 매핑하여 읽어내는 로직([audit_engine.py](file:///c:/Users/CLAUD/landing_page/audit_engine.py))을 고도화합니다.
2. **표준 계정과목 매핑 딕셔너리 구축**:
   * 피감사인의 잡다한 비표준 계정명을 회계법인 표준 코드(예: 보통예금 ➔ 10100 현금및현금성자산)로 자동 합산 및 분류해 줄 마스터 매핑 규칙 데이터베이스 테이블을 Supabase에 구축합니다.
3. **표준 재무상태표(BS) & 손익계산서(IS) 자동 산식 빌더 구현**:
   * 매핑이 완료된 표준 계정과목 데이터를 합산하여 표준 BS 및 IS 양식을 자동으로 구성하는 빌더 모듈을 작성하고, 대차평형(자산=부채+자본) 검증 공식을 도입합니다.
4. **고객 제시 재무제표와의 차이(Delta) 검토 알고리즘 구현**:
   * 시산표 잔액 기준 자동 재무제표와 피감사인이 직접 작성해 제시한 재무제표 드래프트 수치 간의 불일치 항목 및 차이 금액을 자동 계산하는 연산 알고리즘을 짭니다.
5. **n8n 자동화 Webhook 파이프라인 연동**:
   * 파일 업로드 완료 시 n8n Webhook이 트리거되어 위 파이썬 정제 스크립트를 호출하고 가공 데이터를 Supabase DB 테이블에 자동 적재하도록 연동합니다.
6. **Dify API 연동을 통한 차이 원인 분석 및 수정 보고서 생성**:
   * 차이가 발생한 Delta 항목 리스트를 Dify API로 전송하여 AI가 회계학적 원인 분석 보고서 마크다운을 자동 반환하도록 프롬프트 체인을 구축합니다.
7. **마스터 포털 대시보드 UI 연계 및 시각화**:
   * 정제 완료된 재무제표 테이블 및 AI 분석 보고서가 해당 파트너사 관리자 상세 페이지([master_detail.html](file:///c:/Users/CLAUD/landing_page/templates/master_detail.html))에 실시간 바인딩되도록 렌더링을 연계합니다.

---

## 4. 관련 참조 정보 및 문서

* **디자인 시스템 및 CSS 가이드**: [css_master.md](file:///c:/Users/CLAUD/landing_page/css_master.md) (디자인 유지보수 시 필수 참조)
* **데이터베이스 스키마 정의**: [supabase_schema.sql](file:///c:/Users/CLAUD/landing_page/supabase_schema.sql)
* **핵심 백엔드 로직 파일**: [audit_engine.py](file:///c:/Users/CLAUD/landing_page/audit_engine.py) 및 [app.py](file:///c:/Users/CLAUD/landing_page/app.py)
