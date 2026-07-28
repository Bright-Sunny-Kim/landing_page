---
title: 테스트
status: active
owner: development-team
last_verified: 2026-07-28
source_of_truth: true
---

# 테스트

## 최소 검증

```powershell
python -m py_compile app.py audit_engine.py
node --check static/js/main.js
```

파일이 존재하는 경우에만 해당 검사를 실행한다.

## 변경 영역별 확인

| 변경 | 확인 |
|---|---|
| 인증 | 신규·기존 비밀번호 해시 로그인, 권한 차단 |
| 마스터 UI | 메뉴, 화면, URL 해시, 제목 동기화 |
| Notion | 인증, 날짜 검증, 페이지네이션, 속성 매핑 |
| 감사 분석 | 파싱, 대차평형, 대사, 위험, 조서 생성 |
| 조서 저장 | 버전 증가, 상태 순서, 이력 |
| RAG | 검색 후보, rerank, 근거, 실패 처리 |
| 배포 | 로그인, 업로드, 핵심 API, 로그 |

## 테스트 데이터

- 실제 고객자료를 저장소에 추가하지 않는다.
- 최소 재현이 가능한 비식별 fixture를 사용한다.
- 실데이터 검증 결과는 수치와 판정만 기록하고 원본 경로·내용은 노출하지 않는다.

