-- 1. pgvector 확장 기능 활성화 (Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. K-GAAP 기준서 데이터 테이블 생성 (RAG 용)
CREATE TABLE IF NOT EXISTS public.k_gaap_standards (
    id SERIAL PRIMARY KEY,
    standard_no VARCHAR(50) NOT NULL,    -- 예: '제6장 금융자산'
    paragraph_no VARCHAR(50) NOT NULL,   -- 예: '문단 6.17'
    title TEXT NOT NULL,                  -- 제목 (예: '수취채권의 손상(대손)평가')
    content TEXT NOT NULL,                -- 내용
    embedding VECTOR(384)                 -- 로컬 sentence-transformers (all-MiniLM-L6-v2) 384차원 임베딩 저장
);

-- 3. 코사인 유사도 기반 pgvector 검색 RPC 함수 정의
CREATE OR REPLACE FUNCTION public.match_k_gaap_standards (
  query_embedding VECTOR(384),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id INT,
  standard_no VARCHAR(50),
  paragraph_no VARCHAR(50),
  title TEXT,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    k.id,
    k.standard_no,
    k.paragraph_no,
    k.title,
    k.content,
    1 - (k.embedding <=> query_embedding) AS similarity
  FROM public.k_gaap_standards k
  WHERE 1 - (k.embedding <=> query_embedding) > match_threshold
  ORDER BY k.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
