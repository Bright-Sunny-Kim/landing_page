---
title: 미완료 작업
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - roadmap.md
  - handover-checklist.md
---

# 미완료 작업

## P0 — 현재 운영 상태 실측

- [ ] `hyean-dskim.com`의 실제 배포 대상 확인
- [ ] Render와 Ubuntu의 현재 커밋 비교
- [ ] Ubuntu systemd 서비스, Dify, ChromaDB 상태 확인
- [ ] 운영 환경변수 이름과 필수 여부 대조
- [ ] 백업 및 롤백 경로 확인

## P1 — 데이터 저장 정책

- [ ] 기업진단 원본·산출물의 표준 스토리지 확정
- [ ] Supabase Storage와 MinIO의 기존 사용 현황 확인
- [ ] 보존기간, 접근권한, 삭제 정책 정의

## P2 — 기업진단 연계 준비

- [ ] `WORK_kds/기업진단` 파일 목록과 실행 진입점 정리
- [ ] `audit_engine.py`와 중복 기능 비교표 작성
- [ ] 코드·데이터·샘플·비밀값 분류
- [ ] 목표 DB 스키마와 API 명세 초안 작성

## P3 — 감사 자동화 잔여

- [ ] 계정과목 표준매핑 및 수동 오버라이드 설계
- [ ] 분개장 파싱
- [ ] 계정별원장 파싱
- [ ] 교차검증과 오류 표시 정책 보강

## 상태 갱신 규칙

- 완료 시 체크하고 세부 이력은 월별 changelog에 기록한다.
- 우선순위나 범위가 바뀌면 변경 이유를 ADR 또는 changelog에 남긴다.
- 운영 상태가 바뀌면 반드시 `current-status.md`도 갱신한다.

