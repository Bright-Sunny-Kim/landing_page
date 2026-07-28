---
title: 외부 연동
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - ../04-operations/environment-variables.md
---

# 외부 연동

| 서비스 | 용도 | 현재 기록 |
|---|---|---|
| Supabase | 인증 보조, 업무 DB, 스토리지 | 운영 사용 |
| Notion | 세무 일정 Todo DB | 운영 캘린더 연동 검증 |
| Dify | 회계기준 대화·RAG 워크플로 | 로컬 구성 및 staging 검증 기록 |
| ChromaDB | 회계·감사 벡터 검색 | Ubuntu 사용 기록 |
| Cohere | 검색 결과 rerank | 다국어 rerank 적용 기록 |
| Cloudflare Tunnel | Ubuntu 서비스 외부 연결 | staging 및 서버 접속 사용 기록 |
| Render | Flask 운영 배포 | 2026-07-22 운영 대상으로 기록 |

## 연동 원칙

- 토큰은 서버 환경변수에서만 읽고 브라우저로 전달하지 않는다.
- 외부 API 호출에는 타임아웃과 오류 처리를 둔다.
- Python 백엔드의 외부 호출은 시작, 종료, 상태와 결과 크기를 구조화 로그로 남긴다.
- 운영용 키와 테스트용 키를 구분한다.
- 연결 확인 시 실제 비밀값을 로그나 문서에 출력하지 않는다.

