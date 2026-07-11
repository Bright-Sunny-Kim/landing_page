# Ubuntu 단일 노드 마이그레이션 진행 현황 (Migration Progress)

> **최종 업데이트**: 2026-07-11  
> **전략**: Blue-Green (Render 운영 유지 → Ubuntu staging 검증 → DNS 전환)  
> **목표**: Flask + Dify + ChromaDB를 Ubuntu 홈서버(`192.168.0.224`) 한 곳으로 통합하고, Cloudflare Tunnel로 외부 노출

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
| # | 작업 | 상태 |
|---|---|---|
| 0-1 | ChromaDB / Supabase / Dify Cloud DSL 백업 | ☐ |
| 0-2 | Render 환경변수 목록 확보 | ☐ |
| 0-3 | DNS TTL 300초 사전 축소 | ☐ |
| 0-4 | `staging.hyean-dskim.com` 서브도메인 준비 | ☐ |

### Phase 1 — Ubuntu Flask 앱 구동
| # | 작업 | 상태 | 비고 |
|---|---|---|---|
| 1-1 | `requirements.txt`에 `chromadb`, `cohere`, `requests` 추가 | ✅ | 2026-07-11 |
| 1-2 | `server_setup/portal/hyean-portal.service` systemd 유닛 작성 | ✅ | 2026-07-11 |
| 1-3 | `server_setup/portal/.env.example` 템플릿 작성 | ✅ | 2026-07-11 |
| 1-4 | Ubuntu SSH 원격 접속 검증 (`ssh.hyean-dskim.com`) | ✅ | cloudflared + id_server |
| 1-5 | Ubuntu Docker 서비스 확인 (ChromaDB, Dify, MinIO, NPM) | ✅ | 정상 가동 |
| 1-6 | 소스 배포 (`/opt/hyean-portal` 또는 `~/hyean-portal`) | ☐ | |
| 1-7 | venv + `pip install -r requirements.txt` | ☐ | |
| 1-8 | `.env` 생성 (`CHROMA_SERVER_HOST=localhost`) | ☐ | |
| 1-9 | Gunicorn 기동 및 헬스체크 | ☐ | |
| 1-10 | systemd 등록 (`hyean-portal.service`) | ☐ | sudo 필요 |
| 1-11 | NPM `staging.hyean-dskim.com` → `:5000` 프록시 | ☐ | |

**Phase 1 진행률: 약 40% (로컬 준비·서버 점검 완료, 실제 배포 미완)**

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

### Phase 2 — Dify Cloud → 로컬 Dify 이전
> **참고**: Docker + Dify(`dify.hyean-dskim.com`)는 **이미 Ubuntu에 구축 완료**. 신규 설치가 아닌 설정 이전.

| # | 작업 | 상태 |
|---|---|---|
| 2-1 | Dify Cloud 앱 DSL Export | ☐ |
| 2-2 | 로컬 Dify Import + OpenAI Provider 설정 | ☐ |
| 2-3 | External Tool URL → `http://172.17.0.1:5000/api/dify/retrieval` | ☐ |
| 2-4 | 로컬 Dify API Key 발급 → `.env` `DIFY_API_KEY` | ☐ |
| 2-5 | `app.py` Dify URL 환경변수화 (`DIFY_API_BASE_URL`) | ☐ |

### Phase 3 — 내부망 직결 + ngrok 제거
| # | 작업 | 상태 |
|---|---|---|
| 3-1 | `CHROMA_SERVER_HOST=localhost` 확인 | ☐ |
| 3-2 | FAQ End-to-End 검증 (staging) | ☐ |
| 3-3 | ngrok / Windows Flask 중지 | ☐ |
| 3-4 | 24시간 soak test | ☐ |

### Phase 4 — DNS 전환 (Render → Ubuntu)
| # | 작업 | 상태 |
|---|---|---|
| 4-1 | Go/No-Go 체크리스트 통과 | ☐ |
| 4-2 | NPM `hyean-dskim.com` → `:5000` 프록시 | ☐ |
| 4-3 | Cloudflare DNS 전환 | ☐ |
| 4-4 | Render Suspend (48h 롤백 대기) | ☐ |
| 4-5 | Render Delete + Dify Cloud/ngrok 정리 | ☐ |

**예상 다운타임**: DNS 전환 시 5~15분 (TTL 300초 기준)

---

## 4. Ubuntu 서버 인프라 현황 (2026-07-11 점검)

| 서비스 | 포트 | 외부 URL | 상태 |
|---|---|---|---|
| ChromaDB | 8000 | (내부 전용) | ✅ |
| Dify | 8090 | dify.hyean-dskim.com | ✅ |
| MinIO | 9000/9001 | s3.hyean-dskim.com | ✅ |
| NPM | 80/443/81 | 192.168.0.224:81 (내부) | ✅ |
| n8n | 5678 | n8n.hyean-dskim.com | ✅ |
| Nextcloud | 8080 | nextcloud.hyean-dskim.com | ✅ |
| **Flask Portal** | 5000 | (미구축) | ❌ |

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

1. **Blue-Green**: `staging.hyean-dskim.com`으로 먼저 검증, Render는 Phase 4까지 유지
2. **DNS TTL 300초**: 전환·롤백 각 5분 이내
3. **`FLASK_SECRET_KEY` 동일 유지**: DNS 전환 후 재로그인 불필요
4. **Render 48h Suspend**: 즉시 롤백 가능
5. **저트래픽 시간대 전환**: 주말 새벽 2~4시 권장

---

## 8. 관련 문서

- [analysis_results.md](./analysis_results.md) — 아키텍처 분석 및 Phase별 상세 To-Do
- [server_summary.md](./server_summary.md) — Ubuntu 하드웨어·Docker 서비스 현황
- [walkthrough.md](./walkthrough.md) — RAG 파이프라인 구축 성과
- [dify_rag_setup_guide.md](./dify_rag_setup_guide.md) — Dify External Tool 설정 가이드
- [project_master.md](./project_master.md) — 프로젝트 전체 마스터 문서
