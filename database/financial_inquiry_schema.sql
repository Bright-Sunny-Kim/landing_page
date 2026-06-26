-- 1. financial_institutions (금융기관 마스터)
CREATE TABLE IF NOT EXISTS public.financial_institutions (
    id SERIAL PRIMARY KEY,
    institution_name VARCHAR(100) NOT NULL,
    institution_code VARCHAR(50),
    inquiry_type VARCHAR(20) CHECK (inquiry_type IN ('online', 'paper')) NOT NULL,
    form_template_url VARCHAR(255),
    form_type VARCHAR(20) CHECK (form_type IN ('bank', 'insurance', 'securities', 'card', 'other')),
    online_url VARCHAR(255) DEFAULT 'https://audit.kftc.or.kr/',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. inquiry_requests (조회 신청 내역)
CREATE TABLE IF NOT EXISTS public.inquiry_requests (
    id SERIAL PRIMARY KEY,
    request_no VARCHAR(50) UNIQUE NOT NULL,
    client_id TEXT NOT NULL, -- references users.email (users 테이블의 PK가 email이므로)
    company_name VARCHAR(100) NOT NULL,
    fiscal_year INT NOT NULL,
    institution_id INT REFERENCES public.financial_institutions(id) ON DELETE RESTRICT,
    inquiry_type VARCHAR(20) CHECK (inquiry_type IN ('online', 'paper')) NOT NULL,
    status VARCHAR(50) CHECK (status IN ('draft', 'submitted', 'fee_pending', 'fee_paid', 'form_downloaded', 'mail_sent', 'received', 'completed', 'cancelled')) DEFAULT 'draft',
    fee_amount DECIMAL(15, 2),
    fee_paid_at TIMESTAMP WITH TIME ZONE,
    form_downloaded_at TIMESTAMP WITH TIME ZONE,
    mail_sent_at TIMESTAMP WITH TIME ZONE,
    mail_tracking_no VARCHAR(100),
    received_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    assigned_staff TEXT, -- references users.email
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. inquiry_status_logs (진행이력)
CREATE TABLE IF NOT EXISTS public.inquiry_status_logs (
    id SERIAL PRIMARY KEY,
    request_id INT REFERENCES public.inquiry_requests(id) ON DELETE CASCADE,
    status_from VARCHAR(50),
    status_to VARCHAR(50) NOT NULL,
    changed_by TEXT, -- references users.email
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    memo TEXT
);

-- RLS 활성화 (기존 RLS 정책에 맞춤)
ALTER TABLE public.financial_institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inquiry_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inquiry_status_logs ENABLE ROW LEVEL SECURITY;

-- 더미 데이터 삽입 (예시)
INSERT INTO public.financial_institutions (institution_name, institution_code, inquiry_type, form_type, is_active) VALUES
('국민은행', '004', 'online', 'bank', true),
('신한은행', '088', 'online', 'bank', true),
('우리은행', '020', 'online', 'bank', true),
('농협은행', '011', 'online', 'bank', true),
('하나은행', '081', 'online', 'bank', true),
('삼성생명', 'L01', 'paper', 'insurance', true),
('교보생명', 'L02', 'paper', 'insurance', true),
('미래에셋증권', 'S01', 'paper', 'securities', true),
('현대카드', 'C01', 'paper', 'card', true);
