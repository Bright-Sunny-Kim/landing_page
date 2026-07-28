---
title: 서버 인벤토리
status: verification-required
owner: operations
last_verified: 2026-07-14
source_of_truth: true
related:
  - deployment.md
---

# 서버 인벤토리

민감정보 노출을 줄이기 위해 이 문서에는 서비스 역할과 검증 항목만 기록한다. 내부 IP, 계정, 인증 방식의 상세값은 승인된 비밀관리 또는 운영 채널에서 관리한다.

## Ubuntu 서버

- OS: Ubuntu Server 24.04 LTS로 기록
- 역할: Flask staging, Dify, ChromaDB 및 자동화 서비스
- 외부 연결: Cloudflare Tunnel 사용 기록
- 포털 서비스: 사용자 systemd 서비스 사용 기록

## 서비스 확인표

| 서비스 | 용도 | 확인 방법 |
|---|---|---|
| Flask/Gunicorn | 포털 | systemd 상태와 HTTP 응답 |
| Dify | AI 워크플로 | 컨테이너 상태와 API 응답 |
| ChromaDB | 벡터 검색 | heartbeat와 컬렉션 조회 |
| Nginx Proxy Manager | 내부 프록시 | 관리 화면과 프록시 상태 |
| Cloudflare Tunnel | 외부 연결 | tunnel 상태와 hostname |
| MinIO | 객체 스토리지 후보 | 콘솔·bucket 상태 |
| n8n | 자동화 후보 | 컨테이너·워크플로 상태 |

## 갱신 규칙

서버를 실제 확인한 날짜, 서비스 버전, 상태, 담당자를 표에 추가한다. 토큰·비밀번호·개인키는 기록하지 않는다.

