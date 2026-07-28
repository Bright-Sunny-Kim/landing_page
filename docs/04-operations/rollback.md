---
title: 롤백
status: active
owner: operations
last_verified: 2026-07-28
source_of_truth: true
---

# 롤백

## 원칙

- 배포 전 정상 동작 커밋과 환경 설정 스냅샷을 식별한다.
- DB 스키마 변경은 하위 호환과 역마이그레이션 가능성을 검토한다.
- 운영 도메인 전환 시 이전 환경을 즉시 삭제하지 않는다.
- 실제 종료·삭제는 안정화 확인과 명시적 승인 후 수행한다.

## Ubuntu 전환 롤백

1. 장애 범위와 시작 시각 기록
2. Cloudflare hostname을 기존 Render 대상으로 복원
3. Render 서비스 정상 응답 확인
4. 로그인·핵심 포털·업로드 스모크 테스트
5. Ubuntu 로그 보존
6. 원인과 후속 조치를 changelog에 기록

## 애플리케이션 롤백

저장소의 정상 커밋을 기준으로 새 배포를 수행한다. 사용자 변경을 잃을 수 있는 `git reset --hard` 같은 방식은 운영 절차로 사용하지 않는다.

