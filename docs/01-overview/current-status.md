    ---
    title: 현재 상태
    status: active
    owner: project-team
    last_verified: 2026-08-04
    source_of_truth: true
    related:
      - project-overview.md
      - ../04-operations/deployment.md
      - ../06-planning/open-items.md
    ---

    # 현재 상태

    이 문서는 프로젝트의 현재 상태에 대한 유일한 기준 문서다. 다른 문서와 내용이 충돌하면 실제 운영
  환경을 재검증한 후 이 문서를 우선 갱신한다.

    ## 기준 시점

    - 문서 통합 및 모듈화 완료일: 2026-08-04
    - 최근 운영 및 구조 개편 기록: 2026-08-04 (Python 가상환경, app.py 모듈화)
    - 이전 감사 자동화 기록: 2026-07-18

    ## 최신 환경 및 개발 상태 (2026-08-04 추가)

    | 항목 | 상태 | 근거 및 비고 |
    |---|---|---|
    | Python 가상환경 | `.venv` 구축 완료 | `pip check` 정상, 의존성 충돌 없음 |
    | 앱 아키텍처 | Flask Blueprint 모듈화 | `blueprints/pages.py`, `auth.py`, `billing.py` 분리
  완료 |
    | `app.py` 다이어트 | 백업(`app_backup.py`) 및 축소 완료 | 기존 2,012줄에서 약 130줄로 1/15
  슬림화 |
    | 폴더 정돈 | `.gitignore` 및 문서 정리 완료 | `temporary_data/` 제외 등록 및 `docs/` 카테고리
  정리 |

    ## 기존 운영 및 연동 상태

    | 항목 | 상태 | 근거 및 비고 |
    |---|---|---|
    | 운영 도메인 | Render 연결로 기록됨 | 2026-07-22 기록 기준 |
    | Ubuntu 포털 | staging 검증 완료로 기록됨 | Phase 4 운영 전환은 미확인 |
    | 로컬 Dify | 구축 및 staging 연동 완료로 기록됨 | 실제 현재 설정 재검증 필요 |
    | ChromaDB | Ubuntu에서 사용 | 현재 컨테이너·컬렉션 상태 재검증 필요 |
    | Notion 캘린더 | Render 운영에서 26개 일정 조회 검증 | 2026년 7월 조회 기록 |
    | 로그인 | Supabase service-role 키 적용 후 정상화 기록 | 실제 키 값은 문서화 금지 |
    | 감사조서 저장 | 분석→저장→검토→승인 흐름 검증 기록 | Supabase 스키마 적용 완료로 기록 |
    | 감사자료 분석 | 실 고객사 5종 파일 기반 파서·대사 검증 기록 | 계정 표준매핑과 원장 파싱은 잔여 |

    ## 최근 확인된 구현

    - PBKDF2 신규 해시와 기존 scrypt 해시를 함께 검증한다.
    - 마스터 포털의 메뉴, 화면, URL 해시, 브라우저 제목이 동기화된다.
    - Notion Todo DB를 월간 세무 일정 캘린더로 표시한다.
    - 합계잔액시산표와 재무상태표를 파싱하고 계정별 대사를 수행한다.
    - 감사조서를 버전별로 저장하고 `draft → reviewed → approved` 상태를 관리한다.
    - 고객 분석보고서에서 실데이터가 없을 때 모의 숫자를 표시하지 않는다.

    ## 중요한 제한사항

    - `hyean-dskim.com`의 실제 현재 배포 대상이 Render인지 Ubuntu인지 운영 환경에서 다시 확인해야
  한다.
    - Supabase Storage와 MinIO 중 기업진단 원본·산출물의 주 저장소가 확정되지 않았다.
    - 손익계산서는 결산 마감 구조 때문에 시산표 잔액 기준 대사가 비활성화되어 있다.
    - 계정과목 표준매핑, 분개장 및 계정별원장 파싱이 남아 있다.
    - `WORK_kds` 기업진단 코드와 포털 코드의 중복 기능 비교가 아직 완료되지 않았다.

    ## 바로 이어서 할 일

    1. [인수인계 체크리스트](../06-planning/HANDOVER_LATEST.md)로 다음 대화 이어서 진행.
    2. 실측 결과로 이 문서의 운영 상태 표를 지속 갱신.
    3. 남은 라우트(`company.py`, `master.py`, `inquiry.py`) 블루프린트 추가 이관.

