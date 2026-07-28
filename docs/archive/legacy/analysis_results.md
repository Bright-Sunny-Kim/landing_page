# 시스템 현황 분석 및 향후 마이그레이션 로드맵

> **최종 업데이트**: 2026-07-11  
> **진행 현황 상세**: [migration_progress.md](./migration_progress.md)

---

## 1. 현재 아키텍처 상태 분석 (Current State)

현재 시스템은 **Render(Flask)**, **Windows+ngrok(RAG Retrieval API)**, **Dify Cloud**, **Ubuntu ChromaDB**가 혼합된 하이브리드 형태로 구성되어 있습니다.

### 현재 구조의 장점
- **빠른 개발 및 테스트**: ngrok을 통해 윈도우 로컬의 코드를 즉시 Dify Cloud와 연동하여 실시간 디버깅이 가능했습니다.
- **분산 처리**: RAG 검색(ChromaDB)은 Ubuntu 서버, 로직 처리는 Windows/Render가 담당하여 부하를 분산했습니다.
- **고도화된 RAG 파이프라인**: 1차 Vector Search (ChromaDB) + 2차 Reranking (Cohere) 파이프라인이 `app.py`에 구축되었습니다.
- **Ubuntu 인프라 선행 구축**: Dify, ChromaDB, MinIO, n8n, Nextcloud, NPM, Cloudflare Tunnel(SSH)이 이미 가동 중입니다.

### 현재 구조의 한계 (해결 필요 사항)
- **보안 및 안정성 취약**: ngrok 무료 버전은 세션이 끊기면 URL이 변경되어 상용 서비스로 부적합하며, 외부망에 5000번 포트가 노출됩니다.
- **Windows PC SPOF**: PC 종료·절전·ngrok 중단 시 FAQ 전체 장애.
- **Render ↔ ChromaDB 네트워크 단절**: Render(클라우드)는 Ubuntu 사설 IP(`192.168.0.224`)에 직접 접근 불가. Tailscale/VPN 없으면 검색 실패.
- **네트워크 지연(Latency)**: `사용자 → Render → Dify Cloud → ngrok(Windows) → ChromaDB(Ubuntu) → Cohere → Dify Cloud → 사용자` — 6~8 hop, FAQ 3~8초.
- **데이터 주권**: 회계/감사 질의·조문이 Dify Cloud(해외 SaaS)를 경유.
- **인프라 중복**: Render + Ubuntu(24/7) + ngrok + Dify Cloud 동시 과금·운영.

---

## 2. 향후 아키텍처 목표 (Future State)

모든 컴포넌트를 **Ubuntu Server(`192.168.0.224`)** 한 곳으로 통합(On-Premise Single Node)하고, **Cloudflare Tunnel**로 외부 노출합니다.

### 기대 효과 (To-Be Architecture)
- **초고속 응답**: Flask, ChromaDB, Dify가 localhost에서 통신 → 검색 구간 ms 단위.
- **데이터 보안**: Dify Cloud 대신 로컬 Dify(`dify.hyean-dskim.com`) 사용 → 회계 데이터 외부 SaaS 미경유.
- **Cloudflare Zero Trust**: 인바운드 포트 0, Tunnel로만 HTTPS 수신, DDoS·SSL 무료 적용.
- **운영 단순화**: 장애 지점 Render+ngrok+Windows → Ubuntu 단일 노드.

### 전환 전략: Blue-Green
```
[현재]   hyean-dskim.com → Render (운영)
[Phase1] staging.hyean-dskim.com → Ubuntu Flask (검증, 운영 무영향)
[Phase4] hyean-dskim.com DNS → Ubuntu (5~15분 다운타임)
         Render 48h Suspend (롤백용)
```

---

## 3. 마이그레이션 실행 계획 (Phase 1~4)

### [Phase 1] Ubuntu Flask 앱 구동 — **진행 중 (약 40%)**
- [x] `requirements.txt`에 `chromadb`, `cohere`, `requests` 추가 (2026-07-11)
- [x] `server_setup/portal/hyean-portal.service` systemd 유닛 작성 (2026-07-11)
- [x] `server_setup/portal/.env.example` 환경변수 템플릿 작성 (2026-07-11)
- [x] Ubuntu SSH·Docker 서비스 사전 점검 (2026-07-11)
- [ ] 소스 배포 (`git clone` → `/opt/hyean-portal` 또는 `~/hyean-portal`)
- [ ] Python venv + `pip install -r requirements.txt`
- [ ] `.env` 생성 (`CHROMA_SERVER_HOST=localhost`, `FLASK_SECRET_KEY` 포함)
- [ ] Gunicorn `--bind 127.0.0.1:5000` 기동 및 헬스체크
- [ ] systemd 등록 (`hyean-portal.service`) — sudo 필요, 또는 `systemctl --user` 대안
- [ ] NPM `staging.hyean-dskim.com` → `:5000` 프록시

### [Phase 2] Dify Cloud → 로컬 Dify 이전
> Docker + Dify는 **이미 Ubuntu에 구축 완료** (`dify.hyean-dskim.com`). 설정 이전만 필요.

- [ ] Dify Cloud 앱 DSL Export → 로컬 Dify Import
- [ ] External Tool URL → `http://172.17.0.1:5000/api/dify/retrieval` (Docker Hairpin)
- [ ] 로컬 Dify API Key → `.env` `DIFY_API_KEY`
- [ ] `app.py`: `DIFY_API_BASE_URL` 환경변수화 (현재 `api.dify.ai` 하드코딩)

### [Phase 3] 내부망 직결 + ngrok 제거
- [ ] `CHROMA_SERVER_HOST=localhost` FAQ End-to-End 검증 (staging)
- [ ] ngrok / Windows 24/7 Flask 중지
- [ ] 24시간 soak test

### [Phase 4] DNS 전환 (Render → Ubuntu)
- [ ] Go/No-Go 체크리스트 (로그인·업로드·FAQ·청구·서면조회)
- [ ] NPM `hyean-dskim.com` → `:5000`
- [ ] Cloudflare DNS 전환 (TTL 300초 사전 축소)
- [ ] Render Suspend → 48h 후 Delete
- [ ] Dify Cloud / ngrok 정리

---

## 4. Phase 1 원격 배포 참고

Ubuntu 서버에 물리적으로 있지 않아도 **SSH(`ssh.hyean-dskim.com`)** 로 Phase 1 대부분 진행 가능합니다.

| 작업 | sudo | 원격 |
|---|---|---|
| `~/hyean-portal` 배포 + venv + Gunicorn | ❌ | ✅ |
| systemd 시스템 서비스 (`/opt`) | ✅ | ⚠️ 비밀번호 필요 |
| NPM staging 프록시 | — | ⚠️ LAN 또는 SSH 터널 (`-L 8181:127.0.0.1:81`) |

---

## 5. 권장 작업 일정

| 일차 | 작업 | 운영 영향 |
|---|---|---|
| D-1 | Phase 0 (백업, TTL, env) | 없음 |
| D+1 | Phase 1 완료 (Ubuntu Flask + staging) | 없음 |
| D+2 | Phase 2 (로컬 Dify 연동) | 없음 |
| D+3 | Phase 3 (E2E, ngrok 제거) | 없음 |
| D+4~5 | 24h soak test | 없음 |
| D+6 | Phase 4 DNS 전환 (새벽) | **5~15분** |
| D+8 | Render 종료 | 없음 |
