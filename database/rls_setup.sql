-- =======================================================
-- Supabase DB 접근 원천 차단 RLS (Row Level Security) 설정
-- =======================================================

-- 1. users 테이블 RLS 활성화
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 2. company_files 테이블 RLS 활성화
ALTER TABLE public.company_files ENABLE ROW LEVEL SECURITY;

-- 3. dart_audit_reports 테이블 RLS 활성화
ALTER TABLE public.dart_audit_reports ENABLE ROW LEVEL SECURITY;

-- 4. dart_report_chunks 테이블 RLS 활성화
ALTER TABLE public.dart_report_chunks ENABLE ROW LEVEL SECURITY;

-- 5. document_chunks 테이블 RLS 활성화
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- 6. companies 테이블 RLS 활성화
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

-- 7. audit_working_papers 테이블 RLS 활성화
ALTER TABLE public.audit_working_papers ENABLE ROW LEVEL SECURITY;

-- 8. audit_working_paper_logs 테이블 RLS 활성화
ALTER TABLE public.audit_working_paper_logs ENABLE ROW LEVEL SECURITY;

-- 참고:
-- 위 명령어들로 RLS를 켜기만 하고 별도의 허용(POLICY)을 정의하지 않으면,
-- 기본적으로 anon(공개) 사용자나 권한이 불충분한 사용자는 어떤 데이터도 읽거나 쓸 수 없게 됩니다.
-- 단, 마스터 권한(service_role) 키를 사용하는 Flask 백엔드(`app.py`)는 
-- Postgres 기본 동작에 의해 RLS를 우회하므로 아무런 영향을 받지 않고 정상 작동합니다.
