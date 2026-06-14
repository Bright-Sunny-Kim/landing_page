-- pgvector 익스텐션 활성화 (Supabase SQL Editor에서 실행)
create extension if not exists vector;

-- document_chunks 테이블 생성
create table if not exists document_chunks (
  id bigserial primary key,
  document_id text not null,
  category text, -- 6대 기준 분류 (예: 일반기업회계기준, K-IFRS 등)
  article_name text,
  chunk_text text not null,
  embedding vector(1536), -- text-embedding-3-large(dimensions=1536) 차원수에 맞춰 1536 사용
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- HNSW 인덱스 생성 (유사도 검색 속도 최적화, 코사인 거리 연산자 vector_cosine_ops 사용)
create index on document_chunks using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- Dify 연동용: 유사도 검색을 수행할 RPC(Remote Procedure Call) 함수 생성
create or replace function match_document_chunks (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_category text default null -- 옵션: 특정 카테고리 내에서만 검색
)
returns table (
  id bigint,
  document_id text,
  category text,
  article_name text,
  chunk_text text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.category,
    document_chunks.article_name,
    document_chunks.chunk_text,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
    and (filter_category is null or document_chunks.category = filter_category)
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
end;
$$;
