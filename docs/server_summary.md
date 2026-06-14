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
1.  향후 스토리지 용량 증설 필요 시 3.5인치 내장형 HDD 추가 구매 및 장착 검토.
2.  리눅스 GUI 원격 데스크톱(RDP) 제어 기능 구축:
    *   리눅스 서버에 `xrdp` 관련 패키지 설치.
    *   Cloudflare Tunnel에 `rdp.hyean-dskim.com` ➔ `tcp://localhost:3389` 연결 활성화.
    *   외부 PC에서 `cloudflared access tcp` 터널을 개방하여 윈도우 원격 데스크톱 연결 성공 여부 검증.

---
*본 요약서는 2026년 6월 10일에 최종 업데이트 및 완료 처리되었습니다.*
