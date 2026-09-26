-- ==============================================================================
-- 📋 감사 수임 프로젝트 및 105개 전체 절차별 감사인 배정 정규화 스키마
-- (audit_engagements & audit_procedure_assignments)
-- ==============================================================================

-- 1. 수임 감사 프로젝트 마스터 테이블 (audit_engagements)
CREATE TABLE IF NOT EXISTS public.audit_engagements (
    id BIGSERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    corporate_number VARCHAR(50),
    fiscal_year INTEGER NOT NULL DEFAULT 2025,
    in_charge_name VARCHAR(100) NOT NULL DEFAULT '김동선',
    in_charge_email VARCHAR(150) NOT NULL DEFAULT 'cpaeastsun@gmail.com',
    partner_name VARCHAR(100) DEFAULT '이진우 파트너',
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress', -- 'planned', 'interim', 'in_progress', 'final_review', 'completed'
    status_label VARCHAR(100) NOT NULL DEFAULT '실증감사 진행중',
    inventory_date DATE,
    target_report_date DATE DEFAULT '2026-03-20',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(company_name, fiscal_year)
);

-- 2. 105개 감사 절차별 전담 감사인 배정 상세 테이블 (audit_procedure_assignments)
CREATE TABLE IF NOT EXISTS public.audit_procedure_assignments (
    id BIGSERIAL PRIMARY KEY,
    engagement_id BIGINT NOT NULL REFERENCES public.audit_engagements(id) ON DELETE CASCADE,
    company_name VARCHAR(150) NOT NULL,
    fiscal_year INTEGER NOT NULL DEFAULT 2025,
    section_code VARCHAR(50) NOT NULL, -- '1000', '2000', '3000', '4000', '7000', '8000'
    section_title VARCHAR(200),
    account_code VARCHAR(50) NOT NULL, -- '1100', '4100', 'A-0', etc.
    account_name VARCHAR(200) NOT NULL,
    auditor_name VARCHAR(100) NOT NULL DEFAULT '김동선',
    auditor_email VARCHAR(150) NOT NULL DEFAULT 'cpaeastsun@gmail.com',
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress', -- 'not_started', 'in_progress', 'completed'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(engagement_id, account_code)
);

-- 3. 고속 조회를 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_proc_assign_auditor ON public.audit_procedure_assignments(auditor_email);
CREATE INDEX IF NOT EXISTS idx_proc_assign_engagement ON public.audit_procedure_assignments(engagement_id);
CREATE INDEX IF NOT EXISTS idx_proc_assign_comp_year ON public.audit_procedure_assignments(company_name, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_engagement_incharge ON public.audit_engagements(in_charge_email);
