# Backend Logging Rule

모든 백엔드(Python) 코드 작성 및 수정 시, 디버깅과 유지보수를 위해 다음 사항을 절대 규칙으로 준수한다.

1. **로깅 모듈 사용 의무화**: 단순 `print()` 대신 Python 표준 `logging` 모듈(`logger.info`, `logger.debug`, `logger.error` 등)을 사용하여 시간, 로그 레벨, 발생 모듈을 포함하는 구조화된 로그를 남긴다.
2. **요청/응답 로깅**: 클라이언트로부터 들어오는 API 요청(Request Parameter)과 중요 분기점에서의 응답(Response)은 무조건 `INFO` 또는 `DEBUG` 레벨로 기록한다.
3. **에러 로깅**: 예외(`try-except`) 처리 블록에서는 반드시 `logger.error()`를 사용하여 상세한 에러 트레이스백과 상황적 컨텍스트를 기록한다.
4. **외부 API 및 DB 호출 로깅**: OpenAI API, ChromaDB 등 외부 서비스 호출 시, 호출 시작점과 종료점, 그리고 반환된 데이터의 크기나 상태를 명확히 기록한다.

# Git Publish Rule

사용자가 "깃허브에 반영", "add push", "커밋하고 푸시"처럼 GitHub 게시를 명시적으로 요청하면 다음 절차를 따른다.

1. 현재 작업과 직접 관련된 파일만 선별한다.
2. 관련 없는 변경과 사용자의 다른 미추적 파일은 스테이징하지 않는다.
3. 변경 범위에 맞는 검증을 수행하고 결과를 확인한다.
4. 변경 목적을 설명하는 간결한 메시지로 커밋한다.
5. 현재 브랜치를 `origin`에 push한다.
6. 커밋 SHA, 대상 브랜치, push 및 검증 결과를 사용자에게 보고한다.
7. Pull Request는 사용자가 명시적으로 요청할 때만 생성한다.

단순한 코드 또는 문서 수정 요청은 GitHub 게시 권한을 포함하지 않는다. 사용자가 게시를 명시한 경우에만 commit과 push를 수행한다.

## Authentication

- HTTPS 원격 저장소는 Git Credential Manager에 저장된 자격증명을 사용한다.
- 일반적인 `git add`, `git commit`, `git push` 작업에서 매번 `gh auth login`을 요구하지 않는다.
- `gh` 인증은 Pull Request 생성이나 GitHub API 작업이 필요한 경우에만 확인한다.
- `GH_TOKEN`, `GITHUB_TOKEN`, 접근 토큰 및 기타 비밀값을 로그, 문서, 커밋 메시지에 출력하지 않는다.
- 인증이 실패하면 자격증명을 우회하거나 토큰을 직접 요구하지 않고, 실패한 인증 계층이 Git인지 `gh`인지 구분해 안내한다.
