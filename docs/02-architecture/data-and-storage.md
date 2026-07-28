---
title: 데이터 및 저장소
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
---

# 데이터 및 저장소

## 저장 원칙

| 데이터 | 저장 위치 |
|---|---|
| 사용자, 회사, 권한 | Supabase DB |
| 업무 요청과 처리 상태 | Supabase DB |
| 분석 결과와 승인 이력 | Supabase DB |
| 원본 Excel·CSV·PDF | 지정 객체 스토리지 |
| 생성 PDF·Word·Excel | 지정 객체 스토리지 |
| RAG 지식 청크와 벡터 | ChromaDB |
| 로그·캐시·중간 파일 | Ubuntu 로컬 디스크 |

## 회사 식별

- 회사 관계는 표시명 문자열이 아니라 `companies.id`와 `users.company_id`로 연결한다.
- 사업자등록번호는 회사 생성과 매핑에 사용하는 자연키로 기록되어 있다.
- 신규 기능은 별도 회사·회원 체계를 만들지 않는다.

## 감사조서

- `audit_working_papers`가 회사, 회계연도, 버전, 상태와 분석 결과를 보관한다.
- 상태는 `draft → reviewed → approved` 순서로만 전이한다.
- 상태 변경은 이력 테이블에 남긴다.
- 저장은 자동이 아니라 마스터 사용자의 명시적 작업으로 수행한다.

## 미확정 사항

기업진단 원본과 생성 보고서의 표준 객체 스토리지를 Supabase Storage 또는 MinIO 중 하나로 확정해야 한다. 확정 전에는 두 곳에 중복 저장하는 신규 구현을 추가하지 않는다.

