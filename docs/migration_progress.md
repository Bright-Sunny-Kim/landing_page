# Ubuntu 단일 노드 마이그레이션 진행 현황 (Migration Progress)

> **최종 업데이트**: 2026-07-14  
> **전략**: Blue-Green (Render 운영 유지 → Ubuntu staging 검증 → DNS 전환)  
> **목표**: Flask + Dify + ChromaDB를 Ubuntu 홈서버(`192.168.0.224`) 한 곳으로 통합하고, Cloudflare Tunnel로 외부 노출

## 🔜 다음 세션에서 할 일 (우선순위 순)
1. **soak test 결과 확인** — `hyean-portal-soak-test` 클라우드 스케줄이 2026-07-15 21:06 KST경 자동 종료되며 최종 판정을 알림으로 전달함. 이상 없으면 Go/No-Go 첫 항목 통과.
2. **저트래픽 시간대 확정 + 롤백 리허설** (Go/No-Go 남은 2개 항목) → 이 둘까지 끝나면 **Phase 4 실행(4-2~4-5) 가능**
3. **Phase 4 실행**: `hyean-dskim.com`을 Cloudflare Tunnel Public Hostname으로 전환(staging과 동일 방식, NPM 불필요) → Render Suspend(48h 대기) → 문제없으면 Render Delete + **3-3(ngrok/Windows Flask 중지)**까지 정리
4. Phase 4 완료 후: [audit_master.md](./audit_master.md)의 Track A 기능 로드맵(계정과목 표준매핑, 감사조서 DB 저장·PDF 출력, DART RAG 실가동, 감사보고서 초안 자동생성, 교차검증 워크플로)으로 이어서 진행

---

## 1. 현재 아키텍처 (As-Is)

```
[사용자] → hyean-dskim.com → Render (Flask/Gunicorn)
                ↓ FAQ 질의
           Dify Cloud (api.dify.ai)
                ↓ External Data Tool
           Windows PC + ngrok → /api/dify/retrieval
                ↓
           Ubuntu ChromaDB (:8000) + Cohere Rerank + OpenAI
```

### 분산 구조의 주요 단점
| 문제 | 영향 |
|---|---|
| ngrok URL 불안정 / Windows PC 의존 | FAQ 24/7 SLA 불가 |
| Render ↔ ChromaDB(사설 IP) 네트워크 단절 | Tailscale/VPN 없으면 검색 실패 |
| 6~8 hop 네트워크 왕복 | FAQ 응답 3~8초 |
| Dify Cloud 경유 | 회계/감사 데이터 외부 SaaS 유출 |
| 인프라 중복 | Render + Ubuntu + ngrok 동시 운영 |

---

## 2. 목표 아키텍처 (To-Be)

```
[사용자] → Cloudflare Tunnel / NPM
                ↓
[Ubuntu 192.168.0.224]
    ├── Gunicorn Flask     :5000  ← hyean-dskim.com
    ├── Dify Docker        :8090  ← dify.hyean-dskim.com (이미 구축됨)
    ├── ChromaDB           :8000  ← localhost only
    ├── MinIO              :9000  ← s3.hyean-dskim.com (이미 구축됨)
    ├── n8n                :5678
    └── Nextcloud          :8080

[외부 SaaS — 최소화]
    Supabase, OpenAI(임베딩/LLM), Cohere(Rerank)

[제거 대상]
    Render, ngrok, Windows 24/7 Flask, Dify Cloud(FAQ 경로)
```

---

## 3. Phase별 실행 계획 및 진행 상태

### Phase 0 — 사전 준비
| # | 작업 | 상태 | 비고 |
|---|---|---|---|
| 0-1 | ChromaDB / Supabase / Dify Cloud DSL 백업 | ✅ | Dify DSL은 2-1에서 Export 완료. ChromaDB/Supabase는 기존 데이터 그대로 유지(별도 마이그레이션 아님)라 백업 불필요로 재평가 |
| 0-2 | Render 환경변수 목록 확보 | ✅ | 4-0a에서 수행 (아래 Phase 4 참조) |
| 0-3 | DNS TTL 300초 사전 축소 | ⏸ **불필요로 재평가** | Cloudflare 프록시 구조라 전통적 TTL 전파 대기가 필요 없음 (Phase 4 설명 참조) |
| 0-4 | `staging.hyean-dskim.com` 서브도메인 준비 | ✅ | 1-11에서 Cloudflare Tunnel Public Hostname으로 완료 |

### Phase 1 — Ubuntu Flask 앱 구동
| # | 작업 | 상태 | 비고 |
|---|---|---|---|
| 1-1 | `requirements.txt`에 `chromadb`, `cohere`, `requests` 추가 | ✅ | 2026-07-11 |
| 1-2 | `server_setup/portal/hyean-portal.service` systemd 유닛 작성 | ✅ | 2026-07-11 |
| 1-3 | `server_setup/portal/.env.example` 템플릿 작성 | ✅ | 2026-07-11 |
| 1-4 | Ubuntu SSH 원격 접속 검증 (`ssh.hyean-dskim.com`) | ✅ | cloudflared + id_server |
| 1-5 | Ubuntu Docker 서비스 확인 (ChromaDB, Dify, MinIO, NPM) | ✅ | 정상 가동 |
| 1-6 | 소스 배포 (`~/hyean-portal`, git clone) | ✅ | 2026-07-14, sudo 없이 `~/hyean-portal` 경로 |
| 1-7 | venv + `pip install -r requirements.txt` | ✅ | 2026-07-14, Python 3.14 `ensurepip` 미탑재로 `--without-pip` + `get-pip.py` 우회. `sentence-transformers`가 끌어오는 GPU torch(2GB+) 대신 CPU 전용 torch(`torch==2.13.0+cpu`)로 전환 설치 |
| 1-8 | `.env` 생성 (`CHROMA_SERVER_HOST=localhost`) | ✅ | 2026-07-14, `chmod 600`. `FLASK_SECRET_KEY`는 임시 랜덤값 — Phase 4 DNS 전환 전 Render 값과 동일하게 맞춰야 세션 유지됨 |
| 1-9 | Gunicorn 기동 및 헬스체크 | ✅ | 2026-07-14, `curl 127.0.0.1:5000` → HTTP 200, 실제 로그인 페이지 렌더링 확인 |
| 1-10 | systemd 등록 (`hyean-portal-user.service`) | ✅ | 2026-07-14, sudo 불필요(`~/.config/systemd/user`), `loginctl enable-linger dskim` 확인(`Linger=yes`)으로 SSH 종료/재부팅에도 유지 |
| 1-11 | `staging.hyean-dskim.com` → `:5000` 외부 노출 | ✅ | 2026-07-14, **NPM 대신 Cloudflare Tunnel Public Hostname**으로 직결(`my-ubuntu-server` 터널에 `staging.hyean-dskim.com → http://localhost:5000` 라우트 추가). 외부 `curl -I https://staging.hyean-dskim.com` → `HTTP/1.1 200`, `Cf-Cache-Status: DYNAMIC`, 앱의 `no-store` 헤더까지 확인되어 실제 앱 응답 확인. NPM(`192.168.0.224:81`)은 이 경로에서는 불필요 — Phase 4의 `hyean-dskim.com` 본도메인 전환도 동일 방식(Cloudflare Tunnel Public Hostname 추가) 적용 예정 |

**Phase 1 진행률: 100% 완료 (2026-07-14)** — `staging.hyean-dskim.com`이 Render를 거치지 않고 Ubuntu 서버에서 직접 서빙됨. Phase 2(Dify Cloud → 로컬 Dify 이전)로 진행 가능.

#### Phase 1 원격 진행 가능 여부
- **SSH만 있으면** `~/hyean-portal` + `systemctl --user` 로 sudo 없이 대부분 진행 가능
- `/opt`·시스템 systemd·NPM 웹 UI(`192.168.0.224:81`)는 sudo 또는 LAN/SSH 터널 필요
- Render(`hyean-dskim.com`) 운영에는 **영향 없음**

#### Phase 1 배포 경로 (sudo 없는 대안)
```bash
/home/dskim/hyean-portal          # 앱 루트
/home/dskim/logs/hyean-portal/    # 로그
systemctl --user enable hyean-portal   # 사용자 서비스
```

### Phase 2 — Dify Cloud → 로컬 Dify 이전 ✅ 완료 (2026-07-14)
> **참고**: Docker + Dify(`dify.hyean-dskim.com`)는 **이미 Ubuntu에 구축 완료**. 신규 설치가 아닌 설정 이전.

| # | 작업 | 상태 |
|---|---|---|
| 2-1 | Dify Cloud 앱 DSL Export | ✅ |
| 2-2 | 로컬 Dify Import + LLM Provider 설정 (OpenAI 대신 **Gemini**로 확인) | ✅ |
| 2-3 | External Tool(Hyean RAG Retrieval API) 재등록 → `http://172.17.0.1:5000/api/dify/retrieval` | ✅ — Custom Tool은 워크스페이스 단위라 DSL Import로 자동 이관 안 됨, 로컬 Dify에 재등록 필요했음 |
| 2-4 | 로컬 Dify API Key 발급 → `.env` `DIFY_API_KEY` | ✅ |
| 2-5 | `app.py` Dify URL 환경변수화 (`DIFY_API_BASE_URL`) | ✅ |

**트러블슈팅 기록**: Gunicorn이 `127.0.0.1`에만 바인딩되어 있어 Dify Docker 컨테이너(`172.17.0.1`)가 접근 불가 → `0.0.0.0:5000`으로 변경. 서버에 배포된 `app.py`가 로컬 수정사항(2-5)을 반영 못 해 옛 Cloud URL로 요청이 가서 401 발생 → git commit/push 후 서버 `git pull`로 동기화하여 해결. `curl`로 `/api/faq/ask` 스트리밍 응답 및 access log의 `172.20.0.5`(Dify 컨테이너) → `/api/dify/retrieval` 호출까지 실증 확인.

### Phase 3 — 내부망 직결 + ngrok 제거 (진행 중, 순서 조정)
| # | 작업 | 상태 |
|---|---|---|
| 3-1 | `CHROMA_SERVER_HOST=localhost` 확인 | ✅ — ChromaDB heartbeat 정상, 실제 시드 문서(K-GAAP 제7장 등) 검색 확인 |
| 3-2 | FAQ End-to-End 검증 (staging) | ✅ — Agent → Custom Tool → Flask → ChromaDB 전체 체인 access log로 교차 검증 |
| 3-4 | 24시간 soak test | 🕐 진행 중 — 클라우드 스케줄(`hyean-portal-soak-test`, 매시간)로 자동화, 기준 시각 2026-07-14 21:06:20 KST, 종료 2026-07-15 21:06:20 KST |
| 3-3 | ngrok / Windows Flask 중지 | ⏸ **Phase 4 이후로 순서 변경**. 이유: 현재 프로덕션(`hyean-dskim.com`, Dify Cloud)이 이 ngrok 터널에 의존 중이라 지금 끄면 실서비스 챗봇이 즉시 중단됨 |

### Phase 4 — DNS 전환 (Render → Ubuntu)
> **2026-07-14 재점검 결과**: `hyean-dskim.com`과 `staging.hyean-dskim.com`의 `nslookup` 결과가 **완전히 동일한 Cloudflare 엣지 IP**(`104.21.33.129`, `172.67.145.48` 등)로 나옴 — 즉 운영 도메인도 이미 Cloudflare 프록시(오렌지 클라우드)를 거치고 있음. 실제 목적지(Render vs Ubuntu)는 클라이언트 DNS 캐시가 아니라 **Cloudflare 엣지 내부 라우팅 설정**이 결정하므로, 기존에 가정했던 "TTL 300초 기다려야 하는 전통적 DNS 전파" 방식이 아니다. NPM도 필요 없이 staging과 동일하게 **Cloudflare Tunnel Public Hostname 전환**만으로 처리 가능할 것으로 재평가됨.

| # | 작업 | 상태 | 비고 |
|---|---|---|---|
| 4-0a | Render 환경변수 전체 목록 백업 (`FLASK_SECRET_KEY` 포함) | ✅ | 2026-07-14. Render는 "My Workspace → landing_page" 서비스(`srv-d89moagjo6nc73e0fae0`)에서 확인. 개별 Environment Variables(`FLASK_SECRET_KEY`, `SUPABASE_KEY`, `SUPABASE_URL`) + Secret File(로컬 `.env`와 동일 내용) 둘 다 존재. `OPENAI_API_KEY`/`COHERE_API_KEY`는 Render에 없었음 — 구조상 정상(옛 아키텍처에서 `/api/dify/retrieval`은 Render가 아닌 Windows PC+ngrok에서 실행됐기 때문에 Render가 쓸 일이 없었음). 서버 `.env`에는 이미 확보되어 있고 실제 ChromaDB 검색 테스트로 정상 작동 확인됨. 유일한 의도된 차이는 `CHROMA_SERVER_HOST`(Render: Tailscale IP `100.74.25.71` vs 서버: `localhost`) |
| 4-0b | `FLASK_SECRET_KEY` 서버 `.env`에 Render 값과 동일하게 반영 | ✅ | 2026-07-14. `hyean-partners-secret-secure-key-90210`로 서버 `.env` 갱신 및 재기동 완료 — 전환 시 기존 로그인 세션 유지됨 |
| 4-1 | Go/No-Go 체크리스트 통과 (아래 참조) | ☐ | |
| 4-2 | ~~NPM 프록시~~ → **Cloudflare Tunnel Public Hostname 추가** (`hyean-dskim.com` → `http://localhost:5000`) | ☐ | 기존 Render용 DNS 레코드 먼저 제거/교체 필요 |
| 4-3 | Cloudflare 라우팅 전환 확인 | ☐ | 오렌지 클라우드 특성상 즉시 반영 예상 (기존 5~15분 다운타임 추정치보다 짧을 가능성) |
| 4-4 | Render Suspend (48h 롤백 대기) | ☐ | 문제 시 4-2에서 바꾼 라우팅만 되돌리면 즉시 롤백 |
| 4-5 | Render Delete + Dify Cloud/ngrok 정리 (3-3 포함) | ☐ | |

#### Go/No-Go 체크리스트 (4-1)
- [ ] 3-4 soak test 24시간 무중단·무에러 통과 (자동 진행 중, 종료 예정: 2026-07-15 21:06 KST)
- [x] Render 환경변수 백업 완료 및 서버 `.env`와 diff 확인
- [x] `FLASK_SECRET_KEY` 처리 방침 결정 → 동일화 완료
- [ ] 저트래픽 시간대(주말 새벽 2~4시 등) 확보
- [ ] 롤백 절차(Cloudflare 라우팅 원복) 사전 리허설

> **참고**: Render가 GitHub `main` 브랜치 Auto-Deploy를 사용 중이라, 오늘 push한 커밋(`5664a47`)이 Render에도 이미 자동 배포됨. `DIFY_API_BASE_URL` 미설정 시 기존 Cloud URL로 폴백하도록 설계해서 Render 쪽 동작에는 영향 없음(의도된 안전한 하위호환).

---

## 4. Ubuntu 서버 인프라 현황 (2026-07-14 갱신)

| 서비스 | 포트 | 외부 URL | 상태 |
|---|---|---|---|
| ChromaDB | 8000 | (내부 전용) | ✅ |
| Dify | 8090 | dify.hyean-dskim.com | ✅ |
| MinIO | 9000/9001 | s3.hyean-dskim.com | ✅ |
| NPM | 80/443/81 | 192.168.0.224:81 (내부) | ✅ (Phase 1 경로에서는 미사용) |
| n8n | 5678 | n8n.hyean-dskim.com | ✅ |
| Nextcloud | 8080 | nextcloud.hyean-dskim.com | ✅ |
| **Flask Portal** | 5000 | staging.hyean-dskim.com (Cloudflare Tunnel 직결) | ✅ |

- **SSH**: `dskim@ssh.hyean-dskim.com` (Cloudflare Access + `~/.ssh/id_server`)
- **sudo**: passwordless sudo **미설정** → `/opt` 배포 시 비밀번호 필요

---

## 5. 코드 변경 사항 (Phase 1 준비)

### requirements.txt 추가 패키지
```
chromadb>=0.4.0
cohere>=5.0.0
requests>=2.31.0
```
> `app.py`의 `/api/dify/retrieval`에서 사용 중이었으나 requirements.txt에 누락되어 있던 패키지.

### server_setup/portal/
| 파일 | 용도 |
|---|---|
| `hyean-portal.service` | systemd 시스템 유닛 (Gunicorn, `/opt/hyean-portal`, sudo 필요) |
| `hyean-portal-user.service` | systemd 사용자 유닛 (`~/hyean-portal`, sudo 불필요) |
| `.env.example` | Ubuntu 배포용 환경변수 템플릿 |
| `deploy.sh` | 원격 SSH 배포 스크립트 (`~/hyean-portal` clone + venv) |

### Phase 2 예정 코드 변경
`app.py` Dify API URL 하드코딩 제거:
```python
# 현재: https://api.dify.ai/v1/chat-messages (하드코딩)
# 변경: os.environ.get("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
```

---

## 6. 환경변수 (Ubuntu .env)

```bash
FLASK_SECRET_KEY=           # Render와 동일 값 권장 (세션 유지)
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
COHERE_API_KEY=
DIFY_API_KEY=               # Phase 2에서 로컬 Dify 키로 교체
CHROMA_SERVER_HOST=localhost
CHROMA_SERVER_PORT=8000
MINIO_ENDPOINT=https://s3.hyean-dskim.com
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
# Phase 2+
# DIFY_API_BASE_URL=http://127.0.0.1:8090/v1
```

---

## 7. 다운타임 최소화 전략

1. **Blue-Green**: `staging.hyean-dskim.com`으로 먼저 검증, Render는 Phase 4까지 유지 — ✅ 검증 완료
2. ~~DNS TTL 300초~~ → **Cloudflare Tunnel Public Hostname 전환**: 오렌지 클라우드 프록시 구조라 전통적 TTL 전파 대기 없이 즉시 반영 예상 (2026-07-14 재평가)
3. **`FLASK_SECRET_KEY` 동일 유지**: ✅ Render 값(`hyean-partners-secret-secure-key-90210`)으로 서버 `.env` 동일화 완료 — 전환 후 재로그인 불필요
4. **Render 48h Suspend**: 즉시 롤백 가능 (Phase 4 실행 시 적용 예정)
5. **저트래픽 시간대 전환**: 주말 새벽 2~4시 권장 (Phase 4 실행 시 확정 필요)

---

## 8. 관련 문서

- [analysis_results.md](./analysis_results.md) — 아키텍처 분석 및 Phase별 상세 To-Do
- [server_summary.md](./server_summary.md) — Ubuntu 하드웨어·Docker 서비스 현황
- [walkthrough.md](./walkthrough.md) — RAG 파이프라인 구축 성과
- [dify_rag_setup_guide.md](./dify_rag_setup_guide.md) — Dify External Tool 설정 가이드
- [project_master.md](./project_master.md) — 프로젝트 전체 마스터 문서
