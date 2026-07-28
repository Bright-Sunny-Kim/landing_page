# 작업 요약 (Walkthrough)

## 2026-07-22 운영 장애 및 마스터 포털 후속 수정

1. 로그인 시 `db_error`가 발생한 원인을 Render의 anon Supabase 키와 `users` RLS 차단으로 특정하고, service-role 키로 교체하여 정상 로그인까지 검증했습니다.
2. PBKDF2 신규 해시와 기존 scrypt 해시를 모두 읽을 수 있도록 비밀번호 검증 경로를 보강했습니다.
3. 마스터 사이드바 탭을 누르면 활성 메뉴뿐 아니라 실제 화면, URL 해시, 브라우저 탭 제목이 실시간으로 동기화되도록 수정했습니다. 이전 금융조회·청구 화면이 다른 탭에 남는 현상도 제거했습니다.
4. `main`에서 누락됐던 Notion 세무 일정 캘린더 구현을 복원하고 정적 CSS/JS 캐시 버전을 갱신했습니다.
5. Render에 `NOTION_ACCESS_TOKEN`과 `NOTION_TODO_DATABASE_ID`를 등록하고 환경 갱신 배포를 완료했습니다.
6. 운영 사이트에서 2026년 7월 범위의 Notion 일정 26건이 실제 캘린더에 동기화되는 것을 확인했습니다.

관련 운영 커밋은 `3bfc635`(캘린더 통합), `3804326`(탭 동기화), `1f8830d`(정적 자산 캐시 갱신)입니다.

## 2026-07-22 Notion 세무 일정 캘린더

마스터 포털의 준비 중 화면이었던 `세무 일정 캘린더`를 Notion Todo DB 기반의 실제 월간 캘린더로 전환했습니다.

- Flask 서버가 환경변수의 Notion Installation access token으로 Todo DB를 조회하므로 토큰이 브라우저 코드나 응답에 노출되지 않습니다.
- 일정 제목·날짜·상태·분류·상세 내용과 중요·긴급·Must-DO 속성을 월간 캘린더 및 상세 패널에 표시합니다.
- 월 이동, 오늘 이동, 새로고침, 다건 일정 목록, Notion 원문 링크와 모바일 반응형 레이아웃을 지원합니다.
- 배포 환경은 `NOTION_ACCESS_TOKEN`, `NOTION_TODO_DATABASE_ID`를 설정하고 실행 중인 Gunicorn 서비스를 재시작해야 합니다.
- Ubuntu 사용자 서비스 이름은 `hyean-portal-user.service`이며 재시작 명령은 `systemctl --user restart hyean-portal-user.service`입니다.
- `API token is invalid` 오류는 Installation access token을 다시 발급하고 Todo DB에서 해당 connection을 공유한 뒤 해결해야 합니다.

검증은 Python/JavaScript 구문 검사와 모킹 기반 API 인증·입력·속성 매핑 테스트로 완료했습니다.
성공적으로 RAG(검색 증강 생성) 파이프라인의 핵심 백엔드 구성을 완료했습니다. 

## 🎯 주요 달성 성과

1. **Dify 외부 데이터 도구(External Data Tool) 연동 성공**
   - 윈도우 로컬 개발 환경과 Dify Cloud를 잇기 위해 **ngrok** 터널링을 성공적으로 구성했습니다.
   - OpenAPI(Swagger) 스펙 기반으로 Dify에 `Hyean RAG Retrieval API` 도구를 정식 장착하여, Dify 챗봇이 우리 서버의 DB를 직접 검색할 수 있는 길을 열었습니다.
   - UI 채팅창에 마크다운 포맷이 완벽히 렌더링되도록 CSS와 Dify 프롬프트를 최적화했습니다.

2. **2-Stage Retrieval (Cohere Rerank) 고도화**
   - 단순 크로마DB 유사도 검색의 환각(Hallucination) 한계를 극복하기 위해 `cohere`의 다국어 리랭크 모델(rerank-multilingual-v3.0)을 도입했습니다.
   - 30개의 넉넉한 후보 문서를 뽑아낸 후, AI가 문맥을 정밀 분석하여 가장 연관성 높은 5개의 핵심 조항만 필터링하도록 `app.py` 통신 로직을 전면 개편했습니다.

3. **입력 데이터 필터링 (Fast Cut-off) 최적화**
   - 인사말("안녕", "고마워")이나 비속어("시발", "미친") 등 회계와 무관한 일상어/금칙어가 입력되었을 때, Dify API를 호출하지 않고 백엔드 서버에서 0.01초 만에 즉시 답변을 스트리밍 반환하도록 방어 로직을 `app.py`에 구축했습니다.
   - 이를 통해 불필요한 LLM 비용 낭비를 막고 서버 자원을 최적화했습니다.

## 🔜 넥스트 스텝 (2026-07-14 업데이트)

### Ubuntu 단일 노드 마이그레이션 (진행 중)
상세 계획·진행률: **[migration_progress.md](./migration_progress.md)**

| Phase | 내용 | 상태 |
|---|---|---|
| **1** | Ubuntu Flask(Gunicorn) 배포, staging 검증 | ✅ 완료 |
| **2** | Dify Cloud → 로컬 Dify(`dify.hyean-dskim.com`) 이전 | ✅ 완료 (LLM은 Gemini로 확인) |
| **3** | localhost ChromaDB 직결, ngrok 제거 | 🔄 직결·FAQ 검증 완료, soak test 자동 진행 중, ngrok 제거는 Phase 4 이후로 순서 조정 |
| **4** | `hyean-dskim.com` DNS Render → Ubuntu 전환 | 🔄 사전 준비 완료(환경변수 대조, `FLASK_SECRET_KEY` 동일화), soak test 결과 대기 중 |

- **전략**: Blue-Green — Render 운영 유지, `staging.hyean-dskim.com`으로 Ubuntu 먼저 검증. ✅ 검증 완료(`curl https://staging.hyean-dskim.com` HTTP 200, 실제 앱 응답 확인)
- **DNS 전환 방식 재평가**: 운영 도메인도 이미 Cloudflare 프록시를 거치고 있어, 기존 예상(TTL 300초/5~15분 다운타임)과 달리 Cloudflare Tunnel Public Hostname 전환만으로 즉시 처리 가능할 전망.
- **다음 세션**: soak test(`hyean-portal-soak-test` 클라우드 스케줄, ~2026-07-15 21:06 KST 종료) 결과 확인 → Phase 4 실행 → [audit_master.md](./audit_master.md)의 감사 자동화 기능 로드맵으로 진행.
