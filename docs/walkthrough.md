# 작업 요약 (Walkthrough)

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

## 🔜 넥스트 스텝 (2026-07-11 업데이트)

### Ubuntu 단일 노드 마이그레이션 (진행 중)
상세 계획·진행률: **[migration_progress.md](./migration_progress.md)**

| Phase | 내용 | 상태 |
|---|---|---|
| **1** | Ubuntu Flask(Gunicorn) 배포, staging 검증 | 🔄 약 40% (로컬 준비 완료, 서버 배포 대기) |
| **2** | Dify Cloud → 로컬 Dify(`dify.hyean-dskim.com`) 이전 | ☐ |
| **3** | localhost ChromaDB 직결, ngrok 제거 | ☐ |
| **4** | `hyean-dskim.com` DNS Render → Ubuntu 전환 | ☐ |

- **전략**: Blue-Green — Render 운영 유지, `staging.hyean-dskim.com`으로 Ubuntu 먼저 검증.
- **Phase 1 잔여**: Ubuntu에 소스 배포, venv, `.env`, Gunicorn, systemd, NPM staging 프록시.
- **원격 진행**: SSH(`ssh.hyean-dskim.com`)만으로 Phase 1 대부분 가능 (`~/hyean-portal` + sudo 없는 경로).
