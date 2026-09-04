-- ==============================================================================
-- AI 회계감사 전용 포털 & K-GAAP 2023 RAG 고도화 스키마 (Step 1)
-- ==============================================================================

-- 1. users 테이블에 회계사 역할(role) 및 라이선스 정보 컬럼 추가
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'client' CHECK (role IN ('master', 'cpa', 'auditor', 'client'));
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS cpa_number VARCHAR(30); -- 공인회계사 등록번호 (선택)

-- 기존 최고 관리자 계정에 master 역할 부여
UPDATE public.users SET role = 'master' WHERE email = 'cpaeastsun@gmail.com' OR is_admin = TRUE;

-- 2. 감사 프로젝트 테이블 (고객사-사업연도 단위)
CREATE TABLE IF NOT EXISTS public.audit_projects (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES public.companies(id) ON DELETE RESTRICT,
    fiscal_year INT NOT NULL,
    in_charge_id INT REFERENCES public.users(id), -- 주관 회계사 (In-charge)
    engagement_partner_id INT REFERENCES public.users(id), -- 업무수행 파트너 (EP)
    status VARCHAR(20) CHECK (status IN ('planned', 'in_progress', 'reviewing', 'completed')) DEFAULT 'planned',
    target_report_date DATE, -- 감사보고서 발행 목표일
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, fiscal_year)
);

-- 3. 감사 프로젝트 참여 회계사 배정 테이블
CREATE TABLE IF NOT EXISTS public.audit_project_members (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES public.audit_projects(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role VARCHAR(30) DEFAULT 'staff', -- 'in_charge', 'staff', 'reviewer', 'partner'
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- 4. K-GAAP 2023 조서 템플릿 마스터 테이블
CREATE TABLE IF NOT EXISTS public.audit_template_documents (
    id SERIAL PRIMARY KEY,
    section_code VARCHAR(10) NOT NULL, -- '1000', '2000', '3000', '4000', '7000', '8000'
    section_name VARCHAR(100) NOT NULL, -- '감사계약', '위험평가', '계정별 입증감사절차' 등
    account_code VARCHAR(20), -- 'A-0', 'C-0', 'E-0', 'G-0', '2700A' 등
    account_name VARCHAR(100) NOT NULL, -- '현금및현금성자산', '매출채권', '중요성산정' 등
    template_file_name TEXT NOT NULL, -- 'A-0_현금및현금성자산_2023개정.xlsx'
    file_path TEXT NOT NULL,
    version VARCHAR(20) DEFAULT '2023_KGAAP',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. K-GAAP 2023 조서 절차 및 RAG 청크 테이블 (pgvector)
CREATE TABLE IF NOT EXISTS public.audit_template_chunks (
    id SERIAL PRIMARY KEY,
    template_doc_id INT REFERENCES public.audit_template_documents(id) ON DELETE CASCADE,
    section_code VARCHAR(10) NOT NULL,
    account_code VARCHAR(20),
    account_name VARCHAR(100) NOT NULL,
    procedure_type VARCHAR(50) NOT NULL, -- 'Part 1. 필수 기본 실증절차', 'Part 2. 추가 고려 절차' 등
    procedure_title TEXT NOT NULL, -- 절차 명칭 (예: '금융기관 등에 대한 조회')
    target_assertions TEXT[], -- 경영진 주장 ['E', 'C', 'V', 'RO', 'Cutoff', 'CL']
    k_gaas_standards TEXT[], -- 관련 회계감사기준서 ['K-GAAS 330', 'K-GAAS 505']
    content TEXT NOT NULL, -- 감사절차 상세 지침 및 체크포인트
    sample_form_md TEXT, -- 조서 서식 마크다운 템플릿
    embedding vector(1536), -- OpenAI text-embedding-3-small (1536 차원)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. 감사일정 캘린더 테이블
CREATE TABLE IF NOT EXISTS public.audit_schedules (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES public.audit_projects(id) ON DELETE SET NULL,
    company_id INT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    schedule_type VARCHAR(30) NOT NULL, -- '사전감사', '기말감사', '재고실사', '금융조회발송', '보고서제출', '기타'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    assigned_user_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    color VARCHAR(20) DEFAULT '#2563eb', -- 캘린더 배지 색상
    memo TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_audit_projects_company ON public.audit_projects(company_id, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_audit_schedules_date ON public.audit_schedules(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_audit_schedules_company ON public.audit_schedules(company_id);
CREATE INDEX IF NOT EXISTS idx_audit_chunks_section ON public.audit_template_chunks(section_code, account_code);
