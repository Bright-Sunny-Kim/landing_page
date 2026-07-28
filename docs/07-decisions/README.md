---
title: 아키텍처 결정 기록
status: active
owner: project-team
last_verified: 2026-07-28
source_of_truth: true
---

# 아키텍처 결정 기록

되돌리기 어렵거나 여러 기능에 영향을 주는 결정을 ADR로 기록한다.

## 파일 형식

```text
ADR-0001-short-title.md
ADR-0002-next-title.md
```

## 템플릿

```markdown
---
title: 결정 제목
status: proposed
date: YYYY-MM-DD
decision_owners:
  - 담당자
---

# 결정 제목

## 배경
## 고려한 선택지
## 결정
## 결과와 트레이드오프
## 검증 또는 재검토 조건
```

과거 문서에서 추론한 내용을 승인 없이 소급 ADR로 만들지 않는다. 새 결정 또는 담당자가 확인한 기존 결정부터 기록한다.

