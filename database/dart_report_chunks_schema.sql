-- 감사보고서 본문 청크 적재용 테이블
create table if not exists dart_report_chunks (
    id bigserial primary key,
    corp_name text not null,       -- 기업명
    bsns_year text not null,       -- 사업연도
    rcept_no text not null,        -- DART 접수번호 (출처 매핑)
    chunk_text text not null,      -- 분할된 본문 텍스트
    embedding vector(1536),        -- text-embedding-3-large 벡터
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- HNSW 인덱스 생성 (유사도 검색 속도 최적화)
create index if not exists dart_report_chunks_embedding_idx on dart_report_chunks using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- DART 감사보고서 본문 검색용 RPC
create or replace function match_dart_chunks (
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    filter_corp_name text default null,
    filter_bsns_year text default null
)
returns table (
    id bigint,
    corp_name text,
    bsns_year text,
    rcept_no text,
    chunk_text text,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        dart_report_chunks.id,
        dart_report_chunks.corp_name,
        dart_report_chunks.bsns_year,
        dart_report_chunks.rcept_no,
        dart_report_chunks.chunk_text,
        1 - (dart_report_chunks.embedding <=> query_embedding) as similarity
    from dart_report_chunks
    where 1 - (dart_report_chunks.embedding <=> query_embedding) > match_threshold
        and (filter_corp_name is null or dart_report_chunks.corp_name = filter_corp_name)
        and (filter_bsns_year is null or dart_report_chunks.bsns_year = filter_bsns_year)
    order by dart_report_chunks.embedding <=> query_embedding
    limit match_count;
end;
$$;
