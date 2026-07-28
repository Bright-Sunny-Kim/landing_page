---
title: 기업진단 연계
status: proposed
owner: development-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - ../02-architecture/application-structure.md
  - ../06-planning/open-items.md
---

# 기업진단 연계

## 결정된 방향

`WORK_kds` 전체를 포털로 복사하거나 별도 인증 웹사이트를 만들지 않는다. 웹에서 필요한 기업진단 코드만 기존 포털의 업무 모듈로 편입한다.

## 편입 전 분류

| 분류 | 처리 |
|---|---|
| 파싱·분석 Python 코드 | 중복 비교 후 업무 모듈로 편입 |
| 보고서 생성 코드 | `reports` 책임으로 분리 |
| 일회성 변환 스크립트 | `scripts` 또는 `workers` |
| 테스트 샘플 | 비식별화 후 `tests/fixtures` |
| 실제 기업자료 | Git 외부 객체 스토리지 |
| 토큰·비밀번호 | 환경변수 |
| 로그·중간 결과 | 서버 임시 경로 |

## 목표 처리 흐름

```text
고객 자료 업로드
  → DB에 문서 메타데이터 저장
  → 객체 스토리지에 원본 저장
  → 진단 작업 생성(pending)
  → 분석 실행(processing)
  → 결과·보고서 저장
  → completed 또는 failed
  → 고객·마스터 화면에서 조회·승인
```

## 착수 조건

1. `WORK_kds/기업진단` 전체 파일 목록과 실행 진입점을 확인한다.
2. `audit_engine.py`와 파싱·계산·보고서 기능 중복표를 작성한다.
3. 입력·출력 데이터와 스토리지 정책을 확정한다.
4. DB 스키마와 API 명세를 작성한다.
5. 운영 기능을 변경하지 않는 테스트 경로부터 구현한다.

