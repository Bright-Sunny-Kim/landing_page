# Backend Logging Rule

모든 백엔드(Python) 코드 작성 및 수정 시, 디버깅과 유지보수를 위해 다음 사항을 절대 규칙으로 준수한다.

1. **로깅 모듈 사용 의무화**: 단순 `print()` 대신 Python 표준 `logging` 모듈(`logger.info`, `logger.debug`, `logger.error` 등)을 사용하여 시간, 로그 레벨, 발생 모듈을 포함하는 구조화된 로그를 남긴다.
2. **요청/응답 로깅**: 클라이언트로부터 들어오는 API 요청(Request Parameter)과 중요 분기점에서의 응답(Response)은 무조건 `INFO` 또는 `DEBUG` 레벨로 기록한다.
3. **에러 로깅**: 예외(`try-except`) 처리 블록에서는 반드시 `logger.error()`를 사용하여 상세한 에러 트레이스백과 상황적 컨텍스트를 기록한다.
4. **외부 API 및 DB 호출 로깅**: OpenAI API, ChromaDB 등 외부 서비스 호출 시, 호출 시작점과 종료점, 그리고 반환된 데이터의 크기나 상태를 명확히 기록한다.
