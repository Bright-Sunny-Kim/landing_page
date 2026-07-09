-- ==============================================================================
-- 견적서, 제안서, 청구서 관리 스키마 (문서 자동화)
-- ==============================================================================

-- 1. documents 테이블 생성
CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL CHECK (type IN ('quote', 'proposal', 'invoice')), -- 문서 종류
    doc_number TEXT NOT NULL,          -- 문서 번호 (예: 2024-001)
    client_name TEXT NOT NULL,         -- 의뢰인/고객명
    title TEXT NOT NULL,               -- 건명/제목
    author_email TEXT NOT NULL,        -- 작성자 이메일 (users 테이블 참조 가능)
    total_amount NUMERIC DEFAULT 0,    -- 총 합계 금액
    status TEXT DEFAULT 'draft',       -- 진행 상태 (draft, issued, completed 등)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 2. document_items 테이블 생성 (견적 내역)
CREATE TABLE public.document_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    category TEXT NOT NULL,            -- 구분 (항목명)
    unit_price NUMERIC NOT NULL,       -- 단위 금액
    quantity NUMERIC NOT NULL,         -- 수량
    total_price NUMERIC NOT NULL,      -- 총 금액 (단가 * 수량)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 인덱스 추가 (빠른 조회를 위해)
CREATE INDEX idx_documents_author ON public.documents(author_email);
CREATE INDEX idx_documents_type ON public.documents(type);
CREATE INDEX idx_document_items_doc_id ON public.document_items(document_id);
