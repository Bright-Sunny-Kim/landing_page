# Dify RAG 설정 및 검증 가이드

이 문서는 Supabase pgvector에 적재된 회계기준/감사기준 데이터를 Dify AI 에이전트와 연동하고 테스트하기 위한 가이드입니다.

## 1. Supabase pgvector 데이터 소스 연결
Dify는 외부 API(External Data Tool)를 통해 데이터베이스에 쿼리할 수 있습니다. 

1. **API 생성**:
   * Dify가 Supabase 함수를 호출할 수 있도록 중간 API 서버(기존의 Flask 서버 `app.py`)에 엔드포인트를 추가하거나, Supabase의 PostgREST API를 직접 호출합니다.
   * `supabase_pgvector_setup.sql`에서 생성한 `match_document_chunks` RPC를 호출하는 엔드포인트를 생성하는 것이 가장 쉽습니다.

2. **Dify 외부 데이터 도구(External Data Tool) 등록**:
   * Dify 관리자 패널 > `Tools` > `Custom` > `Create Custom Tool`
   * OpenAPI 스키마 포맷으로 방금 만든 API 엔드포인트(예: `POST https://hyean-dskim.com/api/rag/search`)를 등록합니다.
   * 입력 파라미터로 `query` (사용자 질문)를 받도록 설정합니다.

## 2. 에이전트 시스템 프롬프트 (System Prompt)
Dify 챗봇 혹은 워크플로우의 시스템 프롬프트를 아래와 같이 설정하여 환각(Hallucination)을 억제하고 철저하게 기준서 기반 답변을 생성하게 만듭니다.

```text
당신은 '회계법인 혜안'의 AI 회계감사 리뷰어입니다.
사용자가 회계처리나 감사 절차에 대해 질문하면, 당신은 항상 [External Data Tool: Audit Standards Search]를 사용하여 먼저 K-GAAP 및 K-GAAS 기준서를 검색해야 합니다.

답변 규칙:
1. 검색된 기준서 내용(Context)에 기반하여 답변하십시오.
2. 답변 시 반드시 근거가 된 기준서 명칭과 조/항 번호를 명시하십시오. (예: "일반기업회계기준 제10조 제2항에 따르면...")
3. 검색된 내용에 답이 없다면, "제공된 기준서 내에서 정확한 규정을 찾을 수 없습니다."라고 답변하고 유추하여 지어내지 마십시오.
```

## 3. Retrieval 성능 검증 시나리오 (샘플 질의)
설정 완료 후, 아래의 샘플 질의를 통해 제대로 된 조/항을 끌어오는지 수동 검증을 진행하십시오.

* **테스트 1**: "재고자산을 순실현가능가치로 평가해야 하는 경우는 언제인가요?"
  * *기대 결과*: K-GAAP 재고자산 기준서의 저가법 평가 항목 내용 반환.
* **테스트 2**: "감사인이 계속기업가정에 대한 중대한 불확실성을 발견했을 때 감사보고서에 어떻게 기재해야 하나요?"
  * *기대 결과*: K-GAAS 감사보고서 작성 기준서의 관련 조항 반환.


## [2026-06-16] AI 회계기준 어시스턴트(RAG) 고도화 및 버그 수정
- **앱 백엔드 (pp.py)**: /api/faq/ask 라우트에서 OpenAI 및 Supabase 클라이언트 지연 초기화 적용. 프롬프트를 결론-설명-출처 구조로 개선.
- **문서 파싱 (chunker_standards.py)**: 회계기준서 청킹 정규식을 정교화하여 날짜/수식 오인식 방지. 8192 토큰 제한 초과 방지를 위해 3000자 초과 청크 자동 분할.
- **문서 업로드 (process_local_pdfs.py)**: 한글(Non-ASCII) 문자열로 인한 Supabase InvalidKey 에러 해결을 위해 카테고리 영문화 및 영문+해시 파일명 변환 적용.
- **UI 변경 (company.html)**: 담당 회계사 문의 탭 이름을 AI 회계사 문의로 변경.


## [2026-06-16] K-IFRS 문단 분할(Chunking) 고도화 적용
- **K-IFRS 정규식 추가 (chunker_standards.py)**: 1, 102A, 한1, B1, IE1 등 K-IFRS 고유의 복잡한 문단 번호 패턴을 완벽히 인식하여 분할하도록 ifrs_pattern 적용.
- **카테고리 연동 (process_local_pdfs.py)**: 문서의 카테고리 정보(category)를 Chunker 모듈로 전달하여, K-GAAP과 K-IFRS가 각각 자신에게 맞는 정규식을 동적으로 선택하도록 개선.


## [2026-06-16] K-IFRS 폴더 및 카테고리 병합 적용
- **폴더 구조 단순화**: 기존 한국채택국제회계기준(K-IFRS)(시행중) 및 (조기적용가능) 폴더를 한국채택국제회계기준(K-IFRS) 단일 폴더로 통합.
- **카테고리 매핑 수정 (process_local_pdfs.py)**: 스크립트가 단일 통합 폴더를 정상 인식하고 K-IFRS 영문 스토리지 경로로 업로드하도록 CATEGORIES 및 CATEGORY_MAP 설정 업데이트.

## [2026-06-29] RAG 파이프라인 로컬 환경 완전 구축 및 포트 충돌 해결
- **로컬 파싱 파이프라인 전면 개편**: LlamaParse API 제한 문제를 해결하기 위해, 무료 오픈소스인 `Marker`와 `Unstructured API`를 로컬(Ubuntu 서버)에 구축하여 무제한/초고속으로 파싱하도록 아키텍처 변경.
- **텍스트/스캔본 라우팅 최적화 (`n8n_pdf_processor.py`)**: 무거운 API 통신 대신 로컬 라이브러리 `pdfplumber`를 사용하여 0.1초 만에 텍스트 포함 여부를 100% 확실하게 라우팅하도록 개선.
- **포트 충돌 해결 및 백업 로직 구성**: Unstructured 파싱 서버와 ChromaDB 간의 포트 충돌(8000번) 문제를 식별하여, Unstructured API를 8001번 포트로 이관. Marker 파싱 실패 시 Unstructured로 자동 대체되는 든든한 폴백(Fallback) 로직 추가.
- **DB 적재 및 빈 결과 예외처리 수정 (`embedder_standards.py`, `n8n_pdf_processor.py`)**: 파싱 결과가 비어있거나 ChromaDB 적재에 실패할 경우, 강제로 '성공' 처리되던 버그를 수정하고 예외를 명확히 발생시켜 트래커(`parse_tracker.json`)에 정확히 기록되도록 개선.
