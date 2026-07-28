---
title: 프로젝트 개요
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
related:
  - current-status.md
  - ../02-architecture/system-architecture.md
---

# 프로젝트 개요

## 목적

HyeAn 포털은 고객사와 회계법인 담당자가 자료 제출, 조회, 분석, 감사조서 관리 및 회계기준 질의를 하나의 인증 체계에서 수행하도록 지원한다.

## 주요 사용자

- 고객사 사용자: 회사 자료 제출, 진행 상황 및 분석 결과 조회
- 마스터 사용자: 고객사·업무 요청·청구·서면조회·감사 파이프라인 관리
- 운영 담당자: 배포, 외부 서비스 연동, 장애 대응

## 핵심 기능

- 로그인, 세션 및 고객사 소속 관리
- 고객·마스터 포털
- 기업자료 업로드와 조회
- 수수료·청구 및 금융기관 서면조회
- Notion 기반 세무 일정 캘린더
- 회계감사 자료 파싱, 대사, 위험 분석 및 조서 저장
- Dify·ChromaDB 기반 회계기준 RAG
- Supabase DB 및 파일 스토리지 연동

## 기술 구성

- 백엔드: Python, Flask, Gunicorn
- 프론트엔드: Jinja 템플릿, JavaScript, CSS
- 데이터베이스: Supabase PostgreSQL
- 파일 저장소: Supabase Storage 또는 MinIO
- AI/RAG: Dify, ChromaDB, Cohere rerank, 연결된 LLM
- 운영: Render 운영 환경과 Ubuntu 홈서버 전환 구조

## 범위 원칙

- 기존 포털의 인증과 회사 식별 체계를 모든 신규 기능에서 재사용한다.
- 기업진단 기능은 별도 사이트가 아니라 포털의 업무 모듈로 편입한다.
- 장시간 분석은 웹 요청과 분리된 작업 실행 구조로 발전시킨다.
- DB는 업무 상태와 메타데이터, 스토리지는 원본 및 산출물, ChromaDB는 검색용 벡터를 담당한다.

