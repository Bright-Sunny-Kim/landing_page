---
title: 로컬 개발
status: verification-required
owner: development-team
last_verified: 2026-07-28
source_of_truth: true
---

# 로컬 개발

## 기본 절차

1. Python 가상환경 생성
2. `requirements.txt` 설치
3. 추적 제외된 `.env` 준비
4. 필요한 외부 서비스 연결 또는 테스트 대역 준비
5. Flask 애플리케이션 실행
6. 로그인과 대상 기능 확인

정확한 Python 버전, 실행 명령 및 필수 환경변수는 저장소 코드와 배포 환경을 재검증한 후 이 문서에 확정한다.

## 개발 원칙

- 실제 고객자료를 로컬 샘플이나 Git에 복사하지 않는다.
- 테스트 자료는 비식별화한다.
- 운영 service-role 키를 로컬 프론트엔드나 로그에 노출하지 않는다.
- 백엔드 `print()` 대신 표준 `logging`을 사용한다.
- 예외는 상황 정보와 traceback을 포함해 기록하되 비밀값은 제외한다.

