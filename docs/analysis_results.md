# 시스템 현황 분석 및 향후 마이그레이션 로드맵

## 1. 현재 아키텍처 상태 분석 (Current State)

현재 시스템은 **로컬 개발 환경(Windows)**과 **클라우드 서비스(Dify Cloud)**, 그리고 **원격 데이터베이스(Ubuntu ChromaDB)**가 혼합된 하이브리드 형태로 구성되어 있습니다.

### 현재 구조의 장점
- **빠른 개발 및 테스트**: ngrok을 통해 윈도우 로컬의 코드를 즉시 Dify Cloud와 연동하여 실시간 디버깅이 가능했습니다.
- **분산 처리**: 가장 무거운 RAG 검색(ChromaDB)은 원격 우분투 서버가 담당하고, 로직 처리는 로컬 윈도우가 담당하여 부하를 분산했습니다.
- **고도화된 RAG 파이프라인**: 1차 Vector Search (ChromaDB) + 2차 Reranking (Cohere)의 완벽한 파이프라인이 백엔드에 구축되었습니다.

### 현재 구조의 한계 (해결 필요 사항)
- **보안 및 안정성 취약**: ngrok 무료 버전은 세션이 끊기면 URL이 변경되어 상용 서비스로 부적합하며, 외부망에 5000번 포트가 노출됩니다.
- **네트워크 지연(Latency)**: `사용자 ➡️ 윈도우(로컬) ➡️ Dify Cloud ➡️ 윈도우(로컬 API) ➡️ 우분투(ChromaDB) ➡️ 윈도우(로컬 리랭크) ➡️ Dify Cloud ➡️ 사용자` 라는 매우 복잡하고 비효율적인 네트워크 왕복(Round Trip)이 발생합니다.

---

## 2. 향후 아키텍처 목표 (Future State)

사용자님의 계획대로 모든 컴포넌트를 **우분투 서버(Ubuntu Server)** 한 곳으로 모으고(On-Premise/Single Node), **Cloudflare Tunnel**로 강력한 보안을 씌우는 것이 아키텍처의 최종 완성형입니다.

### 기대 효과 (To-Be Architecture)
- **초고속 응답 속도 (Zero Network Latency)**: Flask 앱(app.py), ChromaDB, Dify가 모두 같은 우분투 서버 내부망(localhost)에서 통신하므로 네트워크 지연이 사실상 0이 됩니다.
- **완벽한 데이터 보안**: Dify Cloud 대신 오픈소스 Dify를 Docker로 직접 호스팅하므로, 회사 내부의 중요한 회계/감사 데이터가 외부 클라우드로 전혀 유출되지 않습니다.
- **Cloudflare Zero Trust**: 방화벽 포트(Inbound)를 단 하나도 열지 않고 Cloudflare Tunnel을 통해서만 외부 트래픽을 안전하게 수신하며, 디도스(DDoS) 방어와 SSL 인증서를 무료로 완벽히 적용받습니다.

---

## 3. 마이그레이션(이전) 실행 계획 (To-Do List)

향후 성공적인 이전을 위해 아래와 같은 순서로 작업을 진행할 예정입니다.

### [Phase 1] 우분투 서버 내 Flask 앱 구동
- [ ] 윈도우에서 개발한 전체 소스코드(app.py, templates, static 등)를 우분투 서버로 업로드 (Git 또는 SCP 활용)
- [ ] 우분투 서버에 Python 가상환경(venv) 세팅 및 `requirements.txt` 패키지 설치
- [ ] Gunicorn(또는 uWSGI)과 Nginx를 사용하여 상용 환경(Production) 수준으로 Flask 서버 백그라운드 구동

### [Phase 2] Dify 로컬(Docker) 구축
- [ ] 우분투 서버에 Docker 및 Docker Compose 설치
- [ ] Dify 공식 깃허브에서 소스를 클론받아 `docker-compose up -d`로 Dify Community Edition 로컬 구동
- [ ] 기존 Dify Cloud에서 만들었던 챗봇 프롬프트 및 설정값들을 로컬 Dify로 마이그레이션

### [Phase 3] 내부망(Localhost) API 연동
- [ ] 로컬 Dify의 '외부 데이터 도구(External Data Tool)' URL을 우분투 내부망 주소(예: `http://localhost:5000/api/dify/retrieval`)로 변경하여 내부망 직결 통신망 구축

### [Phase 4] Cloudflare Tunnel (Zero Trust) 적용
- [ ] 도메인(hyean-dskim.com)의 네임서버를 Cloudflare로 이전
- [ ] 우분투 서버에 `cloudflared` 데몬 설치
- [ ] 인바운드 포트를 모두 막고, Cloudflare Tunnel을 통해 `https://chat.hyean-dskim.com` 등 특정 도메인으로만 안전하게 접속되도록 라우팅 설정
