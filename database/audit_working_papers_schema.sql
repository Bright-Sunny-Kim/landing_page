-- ==============================================================================
-- 감사조서 영속화 스키마 (P0) — companies 마스터 테이블 + audit_working_papers
-- ==============================================================================

-- 1. companies (회사 마스터 — corporate_number가 진짜 자연키)
CREATE TABLE IF NOT EXISTS public.companies (
    id SERIAL PRIMARY KEY,
    corporate_number VARCHAR(20) UNIQUE NOT NULL,
    company_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. users 테이블에 company_id 컬럼 추가 (기존 company 텍스트 컬럼은 유지, 병행)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS company_id INT REFERENCES public.companies(id);

-- 3. 기존 users 데이터 백필: corporate_number 기준으로 companies 채우고 연결
INSERT INTO public.companies (corporate_number, company_name)
SELECT DISTINCT corporate_number, company FROM public.users
WHERE corporate_number IS NOT NULL
ON CONFLICT (corporate_number) DO NOTHING;

UPDATE public.users u SET company_id = c.id
FROM public.companies c
WHERE u.corporate_number = c.corporate_number AND u.company_id IS NULL;

-- 4. audit_working_papers (조서 본체, 회사/연도/버전 + draft->reviewed->approved 상태)
CREATE TABLE IF NOT EXISTS public.audit_working_papers (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES public.companies(id) ON DELETE RESTRICT,
    company_name TEXT NOT NULL, -- 조회 편의를 위한 비정규화 스냅샷 (조인 없이 목록 표시용)
    fiscal_year INT NOT NULL,
    version INT NOT NULL,
    status VARCHAR(20) CHECK (status IN ('draft', 'reviewed', 'approved')) DEFAULT 'draft',
    analysis_result_json JSONB NOT NULL,
    working_paper_md TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_by TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    approved_by TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(company_id, fiscal_year, version)
);

-- 5. audit_working_paper_logs (상태 변경 이력 — inquiry_status_logs와 동일 패턴)
CREATE TABLE IF NOT EXISTS public.audit_working_paper_logs (
    id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES public.audit_working_papers(id) ON DELETE CASCADE,
    status_from VARCHAR(20),
    status_to VARCHAR(20) NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    memo TEXT
);
