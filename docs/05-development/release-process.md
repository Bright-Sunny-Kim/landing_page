---
title: 릴리스 절차
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - ../04-operations/deployment.md
---

# 릴리스 절차

## 완료 조건

- 요청 범위 구현
- 관련 테스트 통과
- 사용자 변경과 충돌 여부 확인
- DB·환경변수 변경 사항 명시
- 관련 활성 문서 갱신
- `current-status.md`에 영향을 주면 함께 갱신
- 배포 후 스모크 테스트
- 날짜별 변경 내용을 changelog에 기록

## 문서 갱신 판단

| 변경 | 문서 |
|---|---|
| 운영 상태 | `01-overview/current-status.md` |
| 구조·저장 방식 | `02-architecture` |
| 기능 동작 | `03-features` |
| 배포·장애 대응 | `04-operations` |
| 미완료 범위 | `06-planning/open-items.md` |
| 완료 이력 | `archive/changelog/YYYY-MM.md` |
| 중요한 설계 결정 | `07-decisions/ADR-XXXX-*.md` |

