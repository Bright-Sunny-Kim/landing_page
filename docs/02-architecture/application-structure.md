---
title: 애플리케이션 구조
status: proposed
owner: development-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - system-architecture.md
  - ../03-features/company-diagnosis.md
---

# 애플리케이션 구조

## 현재 원칙

`app.py`에 신규 업무 로직을 계속 직접 추가하지 않는다. 기존 기능을 한 번에 재작성하지 않고, 새 기능부터 라우트·서비스·파서·분석기·보고서 책임을 분리한다.

## 권장 구조

```text
landing_page/
├── app.py
├── audit_engine.py
├── modules/
│   └── company_diagnosis/
│       ├── routes.py
│       ├── service.py
│       ├── models.py
│       ├── parsers/
│       ├── analyzers/
│       └── reports/
├── workers/
├── scripts/
├── database/
│   └── migrations/
├── templates/
├── static/
├── tests/
└── server_setup/
```

이 구조는 목표안이며 현재 저장소에 모두 구현되어 있다는 의미가 아니다.

## 모듈 편입 규칙

- `WORK_kds` 전체를 복사하지 않는다.
- 코드, 입력 샘플, 업무 데이터, 생성물, 비밀값을 먼저 분류한다.
- `audit_engine.py`와 중복되는 파싱·분석 기능을 비교한다.
- 공통 로직은 하나의 서비스로 추출하고 기존 호출 경로를 유지한다.
- 실제 고객자료는 `static`이나 Git 추적 디렉터리에 두지 않는다.

