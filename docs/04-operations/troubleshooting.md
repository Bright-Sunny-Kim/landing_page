---
title: 트러블슈팅
status: active
owner: operations
last_verified: 2026-07-28
source_of_truth: true
related:
  - deployment.md
  - environment-variables.md
---

# 트러블슈팅

## 로그인에서 `db_error`

확인 순서:

1. 서버 로그의 Supabase 상태 코드 확인
2. `users` 테이블 RLS 정책 확인
3. 서버용 `SUPABASE_KEY`가 의도한 권한인지 확인
4. 키 자체는 출력하지 않고 환경변수 반영 후 재배포

과거 원인은 Render에서 anon 키를 사용해 `users` 쓰기가 차단된 것이었다.

## Notion `401 unauthorized` 또는 `API token is invalid`

1. Installation access token이 유효한지 확인
2. 대상 Todo DB에 해당 connection이 공유되었는지 확인
3. 환경변수 이름과 DB ID 확인
4. 서비스 재시작 후 API를 다시 검증

## 화면 또는 JavaScript가 이전 상태로 보임

- 정적 자산 URL의 버전 식별자 확인
- CDN과 브라우저 캐시 확인
- 실제 배포 커밋 확인

## RAG 응답이 없거나 느림

1. Dify API 상태와 URL 확인
2. retrieval API 로그 확인
3. ChromaDB heartbeat 확인
4. rerank 외부 API 타임아웃 확인
5. 빈 검색 결과와 오류 응답을 구분

## Ubuntu 포털이 응답하지 않음

1. systemd 사용자 서비스 상태 확인
2. 최근 로그 확인
3. 환경변수 파일 경로 확인
4. 로컬 bind 주소에서 HTTP 응답 확인
5. Cloudflare Tunnel 상태 확인

