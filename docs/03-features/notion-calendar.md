---
title: Notion 세무 일정 캘린더
status: active
owner: portal-development
last_verified: 2026-07-22
source_of_truth: true
related:
  - ../04-operations/environment-variables.md
  - ../04-operations/troubleshooting.md
---

# Notion 세무 일정 캘린더

## 기능

마스터 포털의 세무 일정 메뉴가 Notion Todo DB를 조회해 월간 캘린더와 일정 상세를 표시한다.

## 데이터 매핑

- 제목, 날짜, 상태, 분류, 상세 내용
- 중요, 긴급, Must-DO 표시
- Notion 원문 링크

## 보안

- Notion 토큰은 Flask 서버 환경변수에서만 읽는다.
- 브라우저 코드와 API 응답에 토큰을 포함하지 않는다.
- 캘린더 API는 마스터 세션을 요구한다.

## 마지막 검증 기록

2026-07-22 Render 운영 환경에서 2026년 7월 범위 26개 일정이 반환된 것으로 기록되어 있다.

