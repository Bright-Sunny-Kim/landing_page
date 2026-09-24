-- ==============================================================================
-- 회원정보 및 권한 변경 이력 관리 테이블 (Audit Trail)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.user_change_logs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,            -- 변경된 회원 계정 이메일
    changed_by VARCHAR(255) NOT NULL,            -- 수정한 사람 (본인 또는 마스터 관리자)
    change_type VARCHAR(50) NOT NULL,            -- 변경 유형 (ROLE_CHANGE, PROFILE_UPDATE 등)
    before_data JSONB DEFAULT '{}'::jsonb,       -- 변경 전 데이터 (예: {"role": "client"})
    after_data JSONB DEFAULT '{}'::jsonb,        -- 변경 후 데이터 (예: {"role": "cpa"})
    ip_address VARCHAR(45),                      -- 변경 당시 접속 IP
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 변경 일시
);

-- 검색 속도 최적화를 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_user_change_logs_email ON public.user_change_logs(user_email);
CREATE INDEX IF NOT EXISTS idx_user_change_logs_created ON public.user_change_logs(created_at DESC);
