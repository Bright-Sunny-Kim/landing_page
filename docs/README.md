---
title: HyeAn 포털 문서 안내
status: active
owner: project-team
last_verified: 2026-08-04
source_of_truth: true
---

# HyeAn 포털 문서

이 디렉터리는 회계법인 혜안 고객 포털의 개발·운영·인수인계 문서를 관리한다.

`landing_page`는 단순 랜딩 페이지가 아니라 인증, 고객·마스터 포털, 문서 업로드, 감사 자동화,
회계기준 RAG, Notion 일정 연동을 포함하는 Flask 통합 애플리케이션이다.

## 처음 읽는 순서

1. [현재 상태](./01-overview/current-status.md)
2. [최신 인수인계 일지](./06-planning/HANDOVER_LATEST.md)
3. [프로젝트 개요](./01-overview/project-overview.md)
4. [시스템 아키텍처](./02-architecture/system-architecture.md)
5. [배포 가이드](./04-operations/deployment.md)
6. [트러블슈팅](./04-operations/troubleshooting.md)
7. [미완료 작업](./06-planning/open-items.md)

## 문서 구분

| 경로 | 역할 |
|---|---|
| `01-overview` | 프로젝트 범위와 현재 상태 |
| `02-architecture` | 애플리케이션, 데이터, 외부 연동 구조 |
| `03-features` | 기능별 동작과 제한사항 |
| `04-operations` | 배포, 서버, 환경변수, 장애 대응 |
| `05-development` | 로컬 개발, 테스트, 릴리스 규칙 |
| `06-planning` | 로드맵, 미완료 작업, 인수인계 |
| `07-decisions` | 중요한 설계 결정 기록 |
| `archive` | 과거 시점 기록과 기존 문서 원본 |

## 관리 원칙

- 현재 상태는 [current-status.md](./01-overview/current-status.md)에서만 관리한다.
- 활성 문서에는 현재도 유효한 정보만 적는다.
- 완료 작업과 날짜별 변경 이력은 `archive/changelog`에 기록한다.
- 계획은 `06-planning`, 운영 절차는 `04-operations`에 기록한다.
- 토큰, 비밀번호, service-role 키 등 비밀값은 문서나 Git에 기록하지 않는다.
- 실제 동작을 확인하지 않은 항목은 `확인 필요`로 표시한다.
- 기능 또는 운영 변경을 완료할 때 관련 문서의 `last_verified`도 갱신한다.
