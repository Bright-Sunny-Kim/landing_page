---
title: 시스템 아키텍처
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - application-structure.md
  - data-and-storage.md
  - integrations.md
---

# 시스템 아키텍처

## 현재 논리 구조

```text
사용자 브라우저
      │ HTTPS
      ▼
Flask 포털
├── 인증 및 세션
├── 고객·마스터 화면
├── 파일 업로드와 업무 API
├── 감사·기업진단 모듈
├── Supabase DB/Storage
├── Dify
└── ChromaDB
```

## 배포 구조

기존 문서에는 Render 운영과 Ubuntu staging이 병행된 Blue-Green 전환 상태로 기록되어 있다.

```text
운영 도메인 ──► Render Flask

staging 도메인 ──► Cloudflare Tunnel ──► Ubuntu Flask
                                      ├── Dify
                                      └── ChromaDB
```

운영 도메인의 실제 현재 연결 대상은 재검증해야 한다. 확인 전에는 Ubuntu 단일 노드 전환이 완료되었다고 간주하지 않는다.

## 목표 구조

- 포털, Dify, ChromaDB 및 분석 실행 환경을 Ubuntu에서 가깝게 배치한다.
- 외부 노출은 Cloudflare Tunnel을 통해 제한한다.
- 업무 상태는 Supabase에 영속화한다.
- 원본과 보고서는 지정된 객체 스토리지에 저장한다.
- 장시간 분석은 비동기 작업으로 분리한다.

## 책임 경계

| 구성요소 | 책임 |
|---|---|
| Flask 포털 | 인증, 권한, 요청 검증, 화면, 업무 API |
| 분석 모듈 | 파싱, 계산, 대사, 보고서 생성 |
| Supabase | 사용자, 회사, 업무 상태, 분석 결과, 승인 이력 |
| 객체 스토리지 | 원본 Excel·CSV·PDF와 생성 보고서 |
| ChromaDB | RAG 검색용 벡터와 메타데이터 |
| Dify | 대화 및 검색 증강 워크플로 |
| Ubuntu 로컬 디스크 | 로그, 캐시, 재생성 가능한 임시 파일 |

