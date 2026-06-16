-- Open DART 감사보고서 메타데이터 적재용 테이블
create table if not exists dart_audit_reports (
    id bigserial primary key,
    rcept_no text not null,        -- DART 접수번호 (고유키 활용)
    corp_code text not null,       -- DART 고유번호
    corp_name text not null,       -- 기업명
    bsns_year text,                -- 사업연도
    adtor_nm text,                 -- 감사인 명칭
    adt_opinion text,              -- 감사의견
    adt_reprt_rcept_dt text,       -- 감사보고서 접수일자
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    unique(rcept_no, corp_code)    -- 접수번호와 기업코드 조합으로 중복 방지
);

-- RLS 활성화 및 권한 설정 (필요시)
-- alter table dart_audit_reports enable row level security;
