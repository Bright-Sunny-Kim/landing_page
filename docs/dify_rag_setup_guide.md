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
