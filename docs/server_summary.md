
### 2026-06-25 벡터 DB 마이그레이션 안내
- 기존 Local SQLite (pgvector 호환용) 구조에서, **Ubuntu Home Server의 ChromaDB Docker 컨테이너** 환경으로 전면 마이그레이션되었습니다.
- 연결 정보:
  - Host: 192.168.0.224 (Ubuntu Server)
  - Port: 8000
- 텍스트 청킹(Chunking)은 LlamaParse 기반의 MarkdownHeaderTextSplitter를 사용하여 의미 단위로 정확하게 분할되어 ChromaDB의 document_chunks 컬렉션에 적재됩니다.

# 🚀 홈 서버 구축 프로젝트 진척 상황 요약 보고서 (Home Server Specification & Setup Status)

본 문서는 개인용 개발/자동화 서버 및 NAS(스토리지) 구축 프로젝트의 하드웨어 스펙, 네트워크 정보, OS, 도커 인프라 및 웹 서비스 배포 상황을 요약한 보고서입니다. 

---

## 1. 하드웨어 사양 (Hardware Specifications)
*   **CPU:** Intel 프로세서 (순정 쿨러 장착)
*   **메인보드:** GIGABYTE B560M-DS3H-PLUS
*   **GPU:** MSI GeForce GTX 시리즈 (외장 그래픽)
*   **RAM:** 삼성 DDR4 32GB (16GB x 2개, 듀얼 채널 구성 완료 ⭐)
*   **메인 스토리지 (OS 설치용):** 삼성 NVMe SSD (삼성 980 제품군 추정)
*   **서브 스토리지 (NAS/데이터 저장용):** 도시바(TOSHIBA) 1TB 외장 하드디스크 (ext4 포맷 완료, `/mnt/storage` 영구 마운트 완료)

---

## 2. 네트워크 및 인프라 기본 정보 (Network & OS)
*   **운영체제 (OS):** Ubuntu Server 24.04 LTS (GUI 데스크톱 환경 포함)
*   **서버 내부 IP 주소:** `192.168.0.224`
*   **마스터 관리자 계정 ID:** `dskim`
*   **외부 원격 접속 (Cloudflare Tunnel 적용 완료):**
    *   **SSH 접속 도메인:** `ssh.hyean-dskim.com` (포트: `22` 매핑)
    *   **원격 데스크톱 도메인 (RDP):** `rdp.hyean-dskim.com` (포트: `3389` 매핑, 단 서버측 GUI 서비스 활성화 대기 상태)
*   **외부 접속 환경 및 무암호 SSH 인증 세팅:**
    *   윈도우 PC의 `~/.ssh/config`에 `ProxyCommand`를 통해 `ssh.hyean-dskim.com`으로 직접 접속 설정 완료.
    *   윈도우 로컬의 `2222` 포트가 `ssh.hyean-dskim.com`으로 매핑되어 Xshell/Xftp로 원격 제어 가능.
    *   비밀번호가 없는 SSH 키 쌍(`id_server`)을 생성 및 등록하여 무암호 로그인 자동화 적용 완료.
*   **전원 관리 세팅:** 24시간 상시 구동을 위해 시스템 자동 절전 모드(Suspend, Sleep, Hibernate) 완전 비활성화(Masking) 완료.

---

## 3. 구축 및 배포 완료된 서비스 목록 (Deployed Services & Domains)

Nginx Proxy Manager(대표 웹 관문)와 Cloudflare Tunnel 설정을 연동하여 모든 서비스에 대하여 개별 서브도메인을 연결하고 **HTTPS(보안 연결) 연동**을 완료했습니다.

| 서비스 이름 | 외부 접속 주소 (HTTPS) | 호스트 내부 포트 | 용도 및 연동 세부 내용 |
| :--- | :--- | :--- | :--- |
| **Nginx Proxy Manager** | `http://192.168.0.224:81` (내부용) | `81` (Admin Web) | 대표 웹 역방향 프록시 관문 (`80`, `443` 포트 제어) |
| **Dify** | [https://dify.hyean-dskim.com](https://dify.hyean-dskim.com) | `8090` (HTTP) / `8443` (SSL) | LLM 앱 개발 및 AI 에이전트 빌더 (최초 관리자 셋업 완료) |
| **Nextcloud** | [https://nextcloud.hyean-dskim.com](https://nextcloud.hyean-dskim.com) | `8080` (HTTP) | 개인 드라이브 클라우드 (1TB 외장하드 `/mnt/storage/nextcloud/data` 연동 완료) |
| **n8n** | [https://n8n.hyean-dskim.com](https://n8n.hyean-dskim.com) | `5678` (HTTP) | 워크플로우 자동화 엔진 (PostgreSQL 16 DB 연동 및 관리자 셋업 완료) |

---

## 4. 완료된 작업 히스토리 (Completed Progress)
1.  **[완료]** 우분투 서버 OS 설치 및 시스템 절전모드 강제 비활성화
2.  **[완료]** 최신 Docker Engine 및 Docker Compose v2 설치 및 dskim 계정에 실행 권한 부여
3.  **[완료]** 도시바 1TB 외장 HDD ext4 포맷 및 `/mnt/storage` 경로에 `/etc/fstab` 영구 자동 마운트 적용
4.  **[완료]** SSH 접속용 Cloudflare Tunnel 프록시 구성 및 Xshell/Xftp 연동 스크립트 구축
5.  **[완료]** Docker Compose 기반 PostgreSQL 16 연동형 n8n 배포 및 최초 계정 생성 완료
6.  **[완료]** 서버 메모리 32GB 듀얼채널 업그레이드 장착
7.  **[완료]** Docker Compose 기반 AI 에이전트 빌더 Dify 배포 및 내부 포트 조정(8090) 완료
8.  **[완료]** 1TB 외장하드와 마운트된 개인 클라우드 Nextcloud 배포 및 MariaDB 10.11 연동 완료
9.  **[완료]** 대표 웹 관문 Nginx Proxy Manager 배포 및 포트(80, 81, 443) 연동 완료
10. **[완료]** NPM 및 Cloudflare Tunnel 연계를 통해 3대 핵심 웹 서비스(Dify, Nextcloud, n8n)에 보안 연결(HTTPS) 및 개별 도메인 연동 완료

---

## 5. 향후 대기 및 장기 과제 (Future To-Do List)

### [2026-07-11] Flask Portal Ubuntu 이전 (Phase 1~4 마이그레이션)
- **현황**: ChromaDB, Dify, MinIO, NPM 등 Docker 인프라는 가동 중. **Flask Portal(:5000)은 미배포**.
- **목표**: Render + ngrok + Dify Cloud 분산 구조 → Ubuntu 단일 노드 + Cloudflare Tunnel 통합.
- **Phase 1 준비 완료**: `server_setup/portal/hyean-portal.service`, `.env.example`, `requirements.txt` 패키지 추가.
- **Phase 1 잔여**: `/opt/hyean-portal`(또는 `~/hyean-portal`) 배포, Gunicorn, `staging.hyean-dskim.com` NPM 프록시.
- **상세**: [migration_progress.md](./migration_progress.md)

1.  향후 스토리지 용량 증설 필요 시 3.5인치 내장형 HDD 추가 구매 및 장착 검토.
2.  리눅스 GUI 원격 데스크톱(RDP) 제어 기능 구축:
    *   리눅스 서버에 `xrdp` 관련 패키지 설치.
    *   Cloudflare Tunnel에 `rdp.hyean-dskim.com` ➔ `tcp://localhost:3389` 연결 활성화.
    *   외부 PC에서 `cloudflared access tcp` 터널을 개방하여 윈도우 원격 데스크톱 연결 성공 여부 검증.

---
*본 요약서는 2026년 6월 10일에 최종 업데이트 및 완료 처리되었습니다.*


## [2026-06-16] AI 회계기준 어시스턴트(RAG) 고도화 및 버그 수정
- **앱 백엔드 (pp.py)**: /api/faq/ask 라우트에서 OpenAI 및 Supabase 클라이언트 지연 초기화 적용. 프롬프트를 결론-설명-출처 구조로 개선.
- **문서 파싱 (chunker_standards.py)**: 회계기준서 청킹 정규식을 정교화하여 날짜/수식 오인식 방지. 8192 토큰 제한 초과 방지를 위해 3000자 초과 청크 자동 분할.
- **문서 업로드 (process_local_pdfs.py)**: 한글(Non-ASCII) 문자열로 인한 Supabase InvalidKey 에러 해결을 위해 카테고리 영문화 및 영문+해시 파일명 변환 적용.
- **UI 변경 (company.html)**: 담당 회계사 문의 탭 이름을 AI 회계사 문의로 변경.


## [2026-06-16] K-IFRS 문단 분할(Chunking) 고도화 적용
- **K-IFRS 정규식 추가 (chunker_standards.py)**: 1, 102A, 한1, B1, IE1 등 K-IFRS 고유의 복잡한 문단 번호 패턴을 완벽히 인식하여 분할하도록 ifrs_pattern 적용.
- **카테고리 연동 (process_local_pdfs.py)**: 문서의 카테고리 정보(category)를 Chunker 모듈로 전달하여, K-GAAP과 K-IFRS가 각각 자신에게 맞는 정규식을 동적으로 선택하도록 개선.


## [2026-06-16] K-IFRS 폴더 및 카테고리 병합 적용
- **폴더 구조 단순화**: 기존 한국채택국제회계기준(K-IFRS)(시행중) 및 (조기적용가능) 폴더를 한국채택국제회계기준(K-IFRS) 단일 폴더로 통합.
- **카테고리 매핑 수정 (process_local_pdfs.py)**: 스크립트가 단일 통합 폴더를 정상 인식하고 K-IFRS 영문 스토리지 경로로 업로드하도록 CATEGORIES 및 CATEGORY_MAP 설정 업데이트.

## [2026-06-19] MinIO Ʈ 丮   ̱׷̼
- **丮 Ҵ**:   1TB ϵ (/mnt/storage/minio_data) ̳  ƮϿ 뷮 丮  Ȯ.
- **Ʈũ **: Nginx Proxy Manager  Cloudflare Tunnel ȰϿ MinIO API Ʈ(9000) s3.hyean-dskim.com, Console   Ʈ(9001) minio.hyean-dskim.com 굵 HTTPS    Ϸ.
- **Docker Hairpin ȸ**: NPM   172.17.0.1 Ŀ Ʈ̸ Ͽ  502 Bad Gateway  ذ Ϸ.
