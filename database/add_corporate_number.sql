-- =======================================================
-- users 테이블 법인등록번호(corporate_number) 컬럼 추가 스크립트
-- =======================================================

-- 1. users 테이블에 corporate_number 문자열 컬럼 추가
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS corporate_number TEXT;

-- 2. 해당 컬럼에 대한 설명 추가 (선택사항)
COMMENT ON COLUMN public.users.corporate_number IS '법인등록번호 (000000-0000000 형태)';
