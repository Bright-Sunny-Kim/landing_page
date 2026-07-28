---
title: 환경변수
status: active
owner: operations
last_verified: 2026-07-28
source_of_truth: true
---

# 환경변수

이 문서는 변수 이름과 용도만 관리한다. 실제 값은 Render 또는 서버의 추적 제외된 `.env`에서 관리한다.

| 변수 | 용도 | 비고 |
|---|---|---|
| `FLASK_SECRET_KEY` | Flask 세션 서명 | 환경 간 의도된 동일성 여부 확인 |
| `SUPABASE_URL` | Supabase 프로젝트 URL | 서버 전용 |
| `SUPABASE_KEY` | Supabase 서버 접근 | service-role 키 노출 금지 |
| `NOTION_ACCESS_TOKEN` | Notion Todo DB 조회 | 브라우저 전달 금지 |
| `NOTION_TODO_DATABASE_ID` | Notion DB 식별 | 환경별 확인 |
| `DIFY_API_KEY` | Dify 앱 호출 | 환경별 키 분리 |
| `DIFY_API_BASE_URL` | Dify API 주소 | Cloud/로컬 경로 확인 |
| `CHROMA_SERVER_HOST` | ChromaDB 호스트 | 배포 환경별 확인 |
| `COHERE_API_KEY` | rerank API | 로그 출력 금지 |

코드에서 사용되는 전체 변수는 배포 전 검색하여 이 목록과 대조한다. 값이 없어도 조용히 잘못된 기본값으로 운영되지 않도록 필수 여부를 검증한다.

