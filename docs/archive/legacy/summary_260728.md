# WORK_kds 기업진단 기능과 HyeAn 포털 연계 검토 요약

- 작성일: 2026-07-28
- 검토 대상: `C:\Users\CLAUD\landing_page\docs\*.md`
- 연계 대상: `C:\Users\cpaea\WORK_kds\기업진단`
- 목적: 다음 개발 세션에서 현재 판단과 권장 구조를 바로 이어서 사용할 수 있도록 아키텍처 검토 결과를 기록한다.
- 주의: 이 문서는 구조 검토 결과이며, 작성 시점에는 포털 소스와 서버 설정을 변경하지 않았다.

## 1. 결론

`landing_page`는 이름과 달리 단순 랜딩 페이지가 아니다. 현재 문서 기준으로 다음 기능이 결합된 Flask 기반 통합 포털이다.

- 로그인과 사용자 세션
- 고객사·마스터 화면
- 기업자료 업로드 및 조회
- 수수료·청구 및 서면조회
- 세무 일정 캘린더
- 기업 감사자료 분석
- RAG 기반 회계기준 질의
- Supabase DB 및 스토리지 연동
- Dify, ChromaDB 등 AI 인프라 연동

따라서 `WORK_kds` 전체를 포털 디렉터리에 복사하거나 별도의 웹사이트와 인증 체계를 새로 만드는 방식은 적절하지 않다.

권장 방향은 다음과 같다.

> 기존 `landing_page`를 중심 애플리케이션으로 유지하고, `WORK_kds`에서 웹에 필요한 기업진단 코드만 업무 모듈로 편입한다. Ubuntu 서버는 포털, 진단 작업, Dify 및 ChromaDB의 실행 환경으로 사용하고, 업무 데이터는 Supabase와 MinIO 또는 Supabase Storage에 영속화한다.

## 2. 문서에서 파악한 현재 구조

현재 시스템은 다음 요소로 구성되어 있다.

```text
사용자 브라우저
      ↓ HTTPS
hyean-dskim.com
      ↓
Flask 포털(landing_page)
├── 고객·마스터 화면
├── 인증 및 세션
├── 파일 업로드
├── 기업진단·감사 API
├── audit_engine.py
├── Supabase DB/Storage
├── Dify
└── ChromaDB
```

Ubuntu 서버에는 문서상 다음 서비스가 이미 구축되어 있다.

- Flask/Gunicorn 스테이징 서비스
- 사용자 systemd 서비스 `hyean-portal-user.service`
- 로컬 Dify
- ChromaDB
- MinIO
- PostgreSQL 및 n8n
- Nextcloud
- Nginx Proxy Manager
- Cloudflare Tunnel

따라서 Ubuntu 인프라를 처음부터 다시 구축하기보다 기존 구성 위에 기업진단 기능을 추가하는 것이 적합하다.

주요 근거 문서는 다음과 같다.

- `docs/project_master.md`
- `docs/migration_progress.md`
- `docs/server_summary.md`
- `docs/analysis_results.md`
- `docs/audit_master.md`
- `docs/walkthrough.md`
- `docs/dify_rag_setup_guide.md`
- `docs/css_master.md`

## 3. 목표 아키텍처

```text
개발 PC
├── landing_page: 포털 및 웹 API
└── WORK_kds: 기업진단 연구·업무 코드와 자료
          │
          │ 필요한 코드만 모듈화
          ▼
GitHub 비공개 저장소
          │
          │ 배포
          ▼
Ubuntu Server
├── Flask/Gunicorn 포털
├── 기업진단 실행 모듈 또는 worker
├── Dify
├── ChromaDB
├── n8n
└── 임시 처리 공간
          │
          ├── Supabase: 업무 DB
          ├── MinIO/Supabase Storage: 원본 및 결과 파일
          └── ChromaDB: 회계·감사 지식 벡터
```

역할을 다음과 같이 명확히 나눈다.

- `landing_page`: 화면, 인증, API, 권한 확인, 작업 요청 및 결과 표시
- 기업진단 모듈: 파싱, 계산, 분석, 보고서 생성
- Supabase: 사용자·회사·진단 프로젝트·분석 결과·승인 상태
- MinIO 또는 Supabase Storage: Excel, CSV, PDF 및 생성 보고서
- ChromaDB: 회계기준, 감사기준, DART 등 RAG 지식
- Ubuntu 로컬 디스크: 로그, 캐시 및 재생성 가능한 임시 파일

## 4. WORK_kds 내용 분류 기준

`WORK_kds` 전체를 복사하지 말고 다음 기준으로 분류한다.

| WORK_kds 내용 | 권장 위치 또는 관리 방식 |
|---|---|
| 기업진단 Python 로직 | `landing_page` 내부 기업진단 업무 모듈 |
| 재무자료 파서 | 기업진단 모듈의 `parsers` |
| 계산·분석 로직 | 기업진단 모듈의 `analyzers` |
| 보고서 생성 코드 | 기업진단 모듈의 `reports` |
| 일괄 처리·변환 스크립트 | `scripts` 또는 `workers` |
| 기업정보·진단 결과 | Supabase DB |
| Excel·CSV·PDF 원본 | MinIO 또는 Supabase Storage |
| 생성된 PDF·Word·Excel | MinIO 또는 Supabase Storage |
| 회계기준·감사기준 RAG 자료 | ChromaDB 및 원본 스토리지 |
| API 키·비밀번호 | Ubuntu의 Git 비추적 `.env` |
| 테스트용 샘플 | `tests/fixtures` |
| 로그·임시 결과 | Ubuntu 서버 전용 디렉터리 |

핵심 원칙:

```text
WORK_kds 코드 → Git으로 관리·배포
WORK_kds 업무 데이터 → DB/스토리지로 이전
WORK_kds 장시간 작업 → Ubuntu에서 실행
사용자 결과 표시 → 기존 landing_page 화면과 API 이용
```

`WORK_kds`를 `static`, `public` 또는 웹에서 직접 접근 가능한 디렉터리에 복사해서는 안 된다. 기업자료와 설정 파일이 외부에 노출될 위험이 있다.

## 5. 권장 코드 구조

기존 `app.py`에는 인증, 문서, 캘린더, RAG 및 감사분석 기능이 함께 들어 있다. 기업진단 기능까지 계속 직접 추가하면 유지보수가 어려워지므로 신규 기능부터 모듈로 분리한다.

```text
landing_page/
├── app.py
├── audit_engine.py
│
├── modules/
│   └── company_diagnosis/
│       ├── routes.py
│       ├── service.py
│       ├── models.py
│       ├── parsers/
│       ├── analyzers/
│       └── reports/
│
├── workers/
│   ├── diagnosis_jobs.py
│   └── document_jobs.py
│
├── scripts/
│   ├── import_work_kds.py
│   └── rag_pipeline/
│
├── database/
│   ├── supabase_schema.sql
│   └── migrations/
│
├── templates/
├── static/
├── tests/
├── server_setup/
└── docs/
```

위 구조는 목표 구조이며 한 번에 대규모 리팩터링하지 않는다. 기존 기능은 유지하고 신규 기업진단 기능부터 모듈 방식으로 추가한다.

`audit_engine.py`와 `WORK_kds`의 기업진단 코드 사이에는 다음과 같은 중복 가능성이 있으므로 먼저 대조해야 한다.

- T/B 및 재무제표 파싱
- 계정과목 정규화
- 대차평형 검증
- 시산표·재무제표 차이 분석
- 변동성 분석
- 보고서 생성

중복 로직을 복사하지 말고 공통 서비스로 추출하며, 문서에 명시된 기존 폴백 경로는 유지한다.

## 6. 웹 기능 처리 흐름

기존 로그인, 사용자 회사 소속 및 마스터 권한 체계를 그대로 사용한다.

```text
고객이 진단자료 업로드
        ↓
Supabase에 회사·문서 메타데이터 저장
        ↓
원본 파일을 MinIO 또는 Supabase Storage에 저장
        ↓
진단 작업 생성: pending
        ↓
Ubuntu의 기업진단 모듈 또는 worker 실행
        ↓
상태 변경: processing
        ↓
결과와 보고서를 저장
        ↓
상태 변경: completed 또는 failed
        ↓
고객·마스터 화면에서 결과 조회 및 승인
```

예상 API 구조:

```text
POST /api/companies/<id>/diagnoses
GET  /api/companies/<id>/diagnoses
GET  /api/diagnoses/<id>
POST /api/diagnoses/<id>/run
GET  /api/diagnoses/<id>/report
POST /api/diagnoses/<id>/approve
```

장시간 분석은 HTTP 요청 안에서 끝까지 실행하지 않는다. 처음에는 systemd 작업 또는 n8n을 이용할 수 있고, 작업량이 증가하면 Celery 또는 RQ와 같은 작업 큐를 검토한다.

## 7. 데이터 저장 원칙

### Supabase DB

- 사용자 및 회사
- 진단 프로젝트
- 업로드 파일 메타데이터
- 작업 상태와 오류 정보
- 진단 항목 및 계산 수치
- 보고서 버전
- 검토 및 승인 상태
- 작업·접근 감사 로그

기업은 회사명 문자열이나 폴더명이 아니라 기존 `companies.id`, `users.company_id` 등 DB 식별자로 연결한다.

### MinIO 또는 Supabase Storage

- 원본 Excel, CSV, PDF
- 생성된 PDF, Word, Excel 보고서
- 대용량 중간 산출물

문서에는 MinIO와 Supabase Storage 사용 내역이 모두 존재한다. 신규 기업진단 파일의 주 저장소를 하나로 정하고 다른 저장소의 역할을 명확히 해야 한다.

### ChromaDB

- 회계기준서 청크
- 감사기준 및 DART 자료
- 기업진단 근거 검색용 임베딩

### Ubuntu 로컬 디스크

- 처리 중 임시 파일
- 로그
- 캐시
- 재생성 가능한 중간 파일

Ubuntu 로컬 디스크를 업무 데이터의 유일한 원본으로 사용하지 않는다.

## 8. 배포 및 운영 전환 판단

문서에는 시점별로 서로 다른 운영 상태가 기록되어 있다.

- 과거 구조: GitHub `main`에서 Render로 자동 배포
- 2026-07-14 전후: Ubuntu 스테이징, 로컬 Dify 및 ChromaDB 검증
- 2026-07-22: 운영 로그인과 환경변수 문제를 Render에서 처리

따라서 문서만으로는 운영 도메인이 Ubuntu로 완전히 전환되었다고 판단할 수 없다. Render가 여전히 운영이고 Ubuntu가 스테이징 또는 병행 상태일 가능성이 높다.

권장 전환 순서:

```text
1. WORK_kds 코드와 데이터를 분류한다.
2. landing_page에 필요한 기업진단 모듈만 추가한다.
3. 로컬 자동 테스트와 샘플 데이터 검증을 수행한다.
4. GitHub 저장소에 반영한다.
5. Ubuntu staging에 배포한다.
6. 실제 고객정보가 없는 테스트 회사로 전체 흐름을 검증한다.
7. Render와 Ubuntu의 환경변수를 대조한다.
8. DB, Storage, Dify 및 ChromaDB 연결을 확인한다.
9. Cloudflare Tunnel의 운영 도메인을 Ubuntu로 전환한다.
10. Render를 일정 기간 롤백용으로 유지한다.
11. 안정화 후 Render, ngrok 및 Windows 상시 실행 의존성을 제거한다.
```

최종 배포 흐름:

```text
개발 PC
   ↓ git push
GitHub 비공개 저장소
   ↓ 자동 배포
Ubuntu /home/dskim/hyean-portal
   ↓ systemd 재시작
hyean-dskim.com
```

Ubuntu 운영 서버에서 직접 소스를 수정하는 방식은 피한다. GitHub 저장소를 코드의 단일 기준으로 유지한다.

## 9. 구조상 확인된 위험과 정리 과제

1. `landing_page`를 프런트엔드만 있는 프로젝트로 간주해서는 안 된다. 현재는 Flask 템플릿과 API가 결합된 통합 애플리케이션이다.
2. `WORK_kds`를 웹 공개 디렉터리에 복사하면 기업자료와 설정 파일이 노출될 수 있다.
3. 신규 기업진단 기능은 별도의 회원·회사 체계를 만들지 말고 기존 인증과 회사 FK를 사용해야 한다.
4. `app.py`의 책임이 이미 크므로 신규 기능은 Flask Blueprint 또는 독립 업무 모듈로 구성해야 한다.
5. 기존 `audit_engine.py`와 `WORK_kds`의 중복 분석 로직을 먼저 조사해야 한다.
6. Supabase Storage와 MinIO의 역할을 확정해야 한다.
7. 운영 도메인의 실제 배포 대상이 Render인지 Ubuntu인지 실측 확인해야 한다.
8. `analysis_results.md`와 `server_summary.md`에는 과거 마이그레이션 상태가 남아 있고, `project_master.md`와 `walkthrough.md`에는 더 최근 상태가 기록되어 있다. 현재 상태를 나타내는 기준 문서를 하나로 정해야 한다.
9. 기존 문서에 서비스 이름과 배포 위치가 여러 형태로 기록되어 있으므로 실제 Ubuntu의 서비스 이름, 경로 및 환경파일 위치를 배포 전에 확인해야 한다.
10. 자동화가 실패해도 마스터가 수동으로 업무를 계속할 수 있는 기존 원칙을 유지한다.

## 10. 다음 세션 권장 시작점

이 문서를 읽은 다음 작업자는 바로 구현하지 말고 아래 항목부터 읽기 전용으로 확인한다.

1. `WORK_kds\기업진단`의 전체 파일 목록과 실행 진입점
2. `landing_page\app.py`의 기존 기업분석·감사 API
3. `landing_page\audit_engine.py`와 WORK_kds 분석 로직의 중복
4. `database` 스키마와 회사 식별자 연결 방식
5. 업로드 파일이 현재 Supabase Storage와 MinIO 중 어디에 저장되는지
6. Ubuntu 운영·스테이징의 실제 Git 커밋과 서비스 상태
7. Render와 Ubuntu 중 현재 `hyean-dskim.com`이 실제로 가리키는 배포 대상

확인 후 다음 산출물을 먼저 작성하는 것이 좋다.

- 코드·데이터 분류표
- 중복 기능 비교표
- 목표 DB 스키마 초안
- API 명세 초안
- 단계별 마이그레이션 및 롤백 계획

## 11. 다음 대화용 컨텍스트

다음 세션에서 다음과 같이 요청하면 이 문서를 기준으로 대화를 이어갈 수 있다.

> `docs/summary_260728.md`를 먼저 읽고 현재 구조를 파악해 줘. 기존 기능을 수정하지 말고, WORK_kds 기업진단 코드와 landing_page의 중복 기능을 읽기 전용으로 비교해 줘.

구현을 시작할 때는 다음과 같이 범위를 명시한다.

> `docs/summary_260728.md`의 방향을 기준으로 진행하되, 먼저 1단계인 코드·데이터 분류표와 중복 기능 비교표만 작성해 줘. 운영 서버와 기존 기능은 변경하지 마.
