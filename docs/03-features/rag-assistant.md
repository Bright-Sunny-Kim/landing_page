---
title: 회계기준 RAG
status: active
owner: ai-development
last_verified: 2026-07-14
source_of_truth: true
related:
  - ../02-architecture/integrations.md
  - ../04-operations/troubleshooting.md
---

# 회계기준 RAG

## 처리 흐름

```text
사용자 질문
  → Flask 입력 필터
  → Dify 워크플로
  → Flask retrieval API
  → ChromaDB 후보 검색
  → Cohere rerank
  → 관련 문서 반환
  → 답변 생성
```

## 구현 기록

- 회계와 무관한 단순 입력을 백엔드에서 빠르게 차단한다.
- ChromaDB에서 넓게 후보를 검색한 후 다국어 rerank로 결과를 축소한다.
- Ubuntu staging에서 Dify와 ChromaDB 로컬 직결이 검증된 것으로 기록되어 있다.
- 과거 ngrok·Dify Cloud 경로는 마이그레이션 이력이며 현재 연결 경로를 재검증해야 한다.

## 운영 검증 항목

- Dify API URL과 앱 키가 현재 환경에 맞는지 확인
- ChromaDB heartbeat 및 컬렉션 확인
- retrieval API 인증과 응답 형식 확인
- 샘플 질의의 검색 문서와 답변 근거 확인
- 타임아웃, 빈 검색 결과, 외부 API 실패 처리 확인

