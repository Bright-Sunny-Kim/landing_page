# -*- coding: utf-8 -*-
"""
End-to-End Verification Script for Audit Control Portal Redesign
(회계감사통제 개편 요구사항 6대 항목 E2E 종합 검증)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from app import app
from core.extensions import MASTER_EMAIL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_verification():
    logger.info("=== [START] 회계감사통제 포털 개편 종합 E2E 검증 ===")
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['email'] = MASTER_EMAIL
            sess['role'] = 'master'
            sess['username'] = '김동선'

        # 1. HTML 마스터 포털 렌더링 검증
        logger.info("[TEST 1] 마스터 포털 뷰 렌더링 검증 (/master/audit)")
        resp = client.get('/master/audit')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        html = resp.data.decode('utf-8')
        
        # 1-1. 페이지 이름 변경: 회계감사통제
        assert "회계감사통제" in html, "메뉴/페이지명 '회계감사통제' 누락"
        logger.info("  ✓ 요구사항 1: 메뉴/페이지명 '회계감사통제' 정상 반영")
        
        # 1-2. 금융기관조회 관리 & 감사 증빙 문서 관리 서브탭 삭제 검증
        assert "subtab-audit-finance" not in html, "금융기관조회 관리 서브탭이 삭제되지 않음"
        assert "subtab-audit-evidence" not in html, "감사 증빙 문서 관리 서브탭이 삭제되지 않음"
        logger.info("  ✓ 요구사항 2 & 3: 구 서브탭(금융기관조회 관리, 감사 증빙 문서 관리) 삭제 완료")
        
        # 1-3. 신설 서브탭 마크업 검증 (감사인 인력 풀, 감사대상회사현황)
        assert "subtab-auditor-pool" in html, "감사인 인력 풀 서브탭(#subtab-auditor-pool) 마크업 누락"
        assert "subtab-audit-target-companies" in html, "감사대상회사현황 서브탭(#subtab-audit-target-companies) 마크업 누락"
        logger.info("  ✓ 요구사항 4 & 5: 감사인 인력 풀 및 감사대상회사현황 서브탭 마크업 정상 탑재")
        
        # 1-4. Job Assign 모달 및 감사인 배정 상세 팝오버 모달 검증
        assert "assign-company-select" in html, "회사명 선택 드롭다운(#assign-company-select) 누락"
        assert "assign-fiscal-year" in html, "사업연도 선택 드롭다운(#assign-fiscal-year) 누락"
        assert "assign-procedures-container" in html, "전체 절차 배정 컨테이너(#assign-procedures-container) 누락"
        assert "modal-auditor-assigned-detail" in html, "감사인 배정 상세 팝오버 모달(#modal-auditor-assigned-detail) 누락"
        logger.info("  ✓ 요구사항 6 & 연동 모달: 회사명/연도 드롭다운, 전체 절차 배정 UI, 감사인 팝오버 모달 정상 반영")

        # 2. 백엔드 API 엔드포인트 검증
        # 2-1. 감사인 인력 풀 API (assigned_companies 및 procedures 번들링 검증)
        logger.info("[TEST 2] 감사인 인력 풀 API (/api/audit/auditor-pool)")
        r_pool = client.get('/api/audit/auditor-pool?refresh=true')
        assert r_pool.status_code == 200, f"Auditor pool API error: {r_pool.status_code}"
        pool_data = r_pool.json
        assert pool_data.get('success') is True, "Auditor pool API failed"
        assert pool_data.get('count', 0) > 0, "No auditors returned"
        auditors = pool_data.get('auditors', [])
        
        # 감사인 배정 상세 번들링 검증
        sample_aud = next((a for a in auditors if a.get('email') == 'cpaeastsun@gmail.com'), auditors[0])
        assert 'assigned_companies' in sample_aud, "assigned_companies 누락"
        logger.info("  ✓ 감사인 풀 반환: %d명 (Sample: %s, 배정 수임사: %d개사)", 
                    pool_data.get('count'), sample_aud['name'], len(sample_aud.get('assigned_companies', [])))
        if sample_aud.get('assigned_companies'):
            first_comp = sample_aud['assigned_companies'][0]
            logger.info("    ➔ 배정 수임사: %s (%d년, 역할: %s, 절차 수: %d개)",
                        first_comp.get('company_name'), first_comp.get('fiscal_year'),
                        first_comp.get('role'), first_comp.get('procedure_count'))

        # 2-2. 개별 감사인 워크로드 조회 API (/api/audit/auditor-workload/<email>)
        logger.info("[TEST 3] 개별 감사인 워크로드 API (/api/audit/auditor-workload/cpaeastsun@gmail.com)")
        r_workload = client.get('/api/audit/auditor-workload/cpaeastsun@gmail.com')
        assert r_workload.status_code == 200, f"Auditor workload API error: {r_workload.status_code}"
        wl_data = r_workload.json
        assert wl_data.get('success') is True, "Auditor workload API failed"
        logger.info("  ✓ 감사인 워크로드 API 성공 (배정 회사: %d건)", wl_data.get('company_count', 0))

        # 2-3. 감사대상회사현황 API (연도별 필터링 지원)
        logger.info("[TEST 4] 감사대상회사현황 API (/api/audit/target-companies)")
        r_target = client.get('/api/audit/target-companies?fiscal_year=2025')
        assert r_target.status_code == 200, f"Target companies API error: {r_target.status_code}"
        target_data = r_target.json
        assert target_data.get('success') is True, "Target companies API failed"
        assert target_data.get('count', 0) > 0, "No target companies returned"
        assert 'companies' in target_data, "Missing companies key"
        logger.info("  ✓ 2025년 감사대상회사: %d개사 (Sample: %s, 장부: %s, 주임: %s)",
                    target_data.get('count'), 
                    target_data['companies'][0]['company_name'],
                    target_data['companies'][0]['ledger_status'],
                    target_data['companies'][0]['in_charge_name'])

        # 2-4. 전체 105개 감사 절차 목록 API (우분투 audit_procedure 및 K-GAAP 1000~8000)
        logger.info("[TEST 5] 전체 감사 절차 목록 API (/api/audit/procedures/all)")
        r_proc = client.get('/api/audit/procedures/all')
        assert r_proc.status_code == 200, f"Procedures API error: {r_proc.status_code}"
        proc_data = r_proc.json
        assert proc_data.get('success') is True, "Procedures API failed"
        assert proc_data.get('total_count') == 105, f"Expected 105 procedures, got {proc_data.get('total_count')}"
        assert len(proc_data.get('sections', [])) == 6, f"Expected 6 sections, got {len(proc_data.get('sections', []))}"
        logger.info("  ✓ K-GAAP 6대 섹션 105대 감사 절차 전량 반환 정상")

        # 2-5. Job Assign 저장 및 실시간 인력 풀 동기화 검증
        logger.info("[TEST 6] Job Assign 저장 및 감사인 인력 풀 실시간 동기화 검증")
        test_payload = {
            "company_name": "(주)프레오",
            "fiscal_year": 2025,
            "in_charge_name": "김동선",
            "in_charge_email": "cpaeastsun@gmail.com",
            "partner_name": "이진우 파트너",
            "members": [
                {"name": "김동선", "email": "cpaeastsun@gmail.com", "role": "In-charge"},
                {"name": "김동선(CPA)", "email": "cpaeastsun@naver.com", "role": "Staff CPA"}
            ],
            "account_assignments": {
                "1100A": "cpaeastsun@gmail.com",
                "2100": "cpaeastsun@naver.com",
                "A-0": "cpaeastsun@gmail.com",
                "C-0": "cpaeastsun@naver.com"
            },
            "status": "in_progress",
            "status_label": "실증감사 진행중",
            "target_report_date": "2026-03-20"
        }
        r_save = client.post('/api/audit/assignments', json=test_payload)
        assert r_save.status_code == 200, f"Assignment save failed: {r_save.status_code}"
        save_data = r_save.json
        assert save_data.get('success') is True, "Save response success is not True"
        logger.info("  ✓ Job Assign 저장 성공: %s (FY %d)", 
                    save_data['assignment']['company_name'], save_data['assignment']['fiscal_year'])

        # 저장 후 캐시 자동 무효화 및 인력 풀 즉시 갱신 확인
        r_pool_after = client.get('/api/audit/auditor-pool')
        assert r_pool_after.status_code == 200
        pool_after_data = r_pool_after.json
        naver_cpa = next((a for a in pool_after_data['auditors'] if a['email'] == 'cpaeastsun@naver.com'), None)
        assert naver_cpa is not None, "cpaeastsun@naver.com not found in pool"
        assert naver_cpa.get('assigned_count', 0) >= 1, "naver CPA assigned count not updated"
        logger.info("  ✓ 저장 후 감사인 풀 실시간 동기화 확인 (cpaeastsun@naver.com 배정 건수: %d)", naver_cpa.get('assigned_count'))

    logger.info("=== [ALL PASS] 회계감사통제 감사인 인력 풀 및 Job Assign 완전 연계 E2E 검증 100% 통과! ===")

if __name__ == '__main__':
    run_verification()
