---
title: 배포 가이드
status: active
owner: operations
last_verified: 2026-07-28
source_of_truth: true
related:
  - server-inventory.md
  - environment-variables.md
  - rollback.md
---

# 배포 가이드

## 배포 전 확인

- 작업 트리와 대상 커밋 확인
- Python·JavaScript 구문 및 관련 테스트 통과
- DB 마이그레이션 필요 여부 확인
- 환경변수 추가·변경 목록 확인
- 운영 도메인의 현재 대상 확인
- 롤백 기준 커밋과 담당자 확인

## Render

기존 문서 기준으로 `main` 반영 후 Render 자동 배포를 사용한다. 실제 서비스와 브랜치 설정은 배포 전에 Render 대시보드에서 확인한다.

배포 후 확인:

- 로그인
- 마스터 포털 탭 전환
- 고객 포털 접근
- Notion 캘린더 API
- 파일 업로드
- RAG 질의
- 서버 오류 로그

## Ubuntu staging

기존 기록의 사용자 서비스 이름은 `hyean-portal-user.service`다.

```bash
systemctl --user status hyean-portal-user.service
systemctl --user restart hyean-portal-user.service
```

서비스 이름, 저장소 경로, `.env` 위치는 실제 서버에서 다시 확인한 후 사용한다.

## 운영 전환

Ubuntu 전환은 다음 순서로 수행한다.

1. staging 전체 기능 검증
2. 저트래픽 시간대 확정
3. 롤백 리허설
4. Cloudflare Tunnel의 운영 hostname 전환
5. 운영 스모크 테스트
6. 안정화 기간 동안 Render 유지
7. 명시적 승인 후 이전 환경 종료

