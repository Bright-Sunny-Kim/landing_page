# -*- coding: utf-8 -*-
"""
AI 회계감사 자동화 시스템 및 독립 포털 단위/통합 테스트 스크립트
(scripts/test_audit_automation.py)
"""
import os
import sys
import json
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import app
from core.audit_engine import (
    load_template_index_data,
    get_template_by_account_code,
    generate_kgaap_account_working_paper,
    export_working_paper_excel
)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("AUDIT_TEST")

def test_template_index():
    logger.info("=== [테스트 1] K-GAAP 2023 조서 템플릿 인덱스 검증 ===")
    templates = load_template_index_data()
    assert len(templates) > 0, "템플릿 인덱스가 비어 있습니다."
    logger.info("✅ 총 %d개 조서 템플릿 인덱스 로드 확인", len(templates))
    
    # 핵심 계정과목 검색 테스트
    sample_codes = ['A-0', 'C-0', 'E-0', 'G-0']
    for code in sample_codes:
        t = get_template_by_account_code(code)
        assert t is not None, f"계정 {code}를 템플릿 인덱스에서 찾을 수 없습니다."
        logger.info("✅ [%s] %s (절차수: %d건) 검색 성공", code, t.get('account_name'), t.get('procedure_count', 0))


def test_working_paper_generation():
    logger.info("\n=== [테스트 2] K-GAAP 2023 조서 자동생성 엔진 검증 ===")
    res = generate_kgaap_account_working_paper(
        company_name="(주)프레오",
        fiscal_year=2025,
        account_code="C-0",
        author="김동선 공인회계사"
    )
    assert res is not None, "조서 생성 결과가 None입니다."
    assert "working_paper_md" in res, "working_paper_md가 누락되었습니다."
    assert len(res["working_paper_md"]) > 200, "조서 본문 길이가 너무 짧습니다."
    logger.info("✅ [C-0 매출채권] 조서 마크다운 생성 성공 (%d 글자)", len(res["working_paper_md"]))
    logger.info("   대사 수치: 당기 %s원, 전기 %s원", 
                f"{res['reconciliation']['current_val']:,.0f}", 
                f"{res['reconciliation']['prior_val']:,.0f}")


def test_excel_export():
    logger.info("\n=== [테스트 3] 원본 서식 보존 엑셀 조서 내보내기 검증 ===")
    sample_md = "# [C-0] 매출채권 감사조서\n## 1. 감사목적\n실재성 및 완전성 검토 완료."
    sample_recon = {"prior_val": 100000000, "current_val": 150000000, "variance_val": 50000000, "variance_pct": 50.0}
    
    stream = export_working_paper_excel(
        company_name="(주)프레오",
        fiscal_year=2025,
        account_code="C-0",
        working_paper_md=sample_md,
        reconciliation_data=sample_recon
    )
    assert stream is not None, "엑셀 스트림이 None입니다."
    excel_bytes = stream.getvalue()
    assert len(excel_bytes) > 1000, "생성된 엑셀 파일 크기가 비정상적입니다."
    logger.info("✅ [C-0 매출채권] 엑셀(.xlsx) 파일 생성 성공 (%d 바이트)", len(excel_bytes))


def test_flask_audit_routes():
    logger.info("\n=== [테스트 4] Flask API 엔드포인트 통합 검증 ===")
    app.config['TESTING'] = True
    client = app.test_client()
    
    # 1. 미인증 시 /audit 접근 -> /login_page 리다이렉트 확인
    res = client.get('/audit')
    assert res.status_code == 302, f"미인증 접근 상태코드 에러: {res.status_code}"
    logger.info("✅ 미인증 사용자 /audit 접근 차단 및 리다이렉트(302) 검증 성공")
    
    # 2. 회계사 세션 주입 후 /audit 접근 확인
    with client.session_transaction() as sess:
        sess['email'] = 'auditor@hyean.com'
        sess['username'] = '김회계사'
        sess['role'] = 'cpa'
        sess['company'] = '회계법인 혜안'
        sess['task_type'] = '회계감사'
        
    res_auth = client.get('/audit')
    assert res_auth.status_code == 200, f"회계사 /audit 접근 에러: {res_auth.status_code}"
    logger.info("✅ 회계사 세션 /audit 뷰 렌더링(200 OK) 성공")
    
    # 3. /api/audit/companies
    res_comp = client.get('/api/audit/companies')
    assert res_comp.status_code == 200, "companies API 에러"
    logger.info("✅ GET /api/audit/companies 정상 응답")
    
    # 4. /api/audit/templates/tree
    res_tree = client.get('/api/audit/templates/tree')
    assert res_tree.status_code == 200, "templates tree API 에러"
    tree_data = res_tree.get_json()
    assert len(tree_data.get('tree', [])) == 6, "6대 섹션이 모두 반환되지 않았습니다."
    logger.info("✅ GET /api/audit/templates/tree 6대 섹션 정상 응답")
    
    # 5. /api/audit/working-papers/generate
    res_gen = client.post('/api/audit/working-papers/generate', json={
        "company_name": "(주)프레오",
        "fiscal_year": 2025,
        "account_code": "A-0"
    })
    assert res_gen.status_code == 200, "조서 생성 API 에러"
    logger.info("✅ POST /api/audit/working-papers/generate 정상 응답")
    
    # 6. /api/audit/schedules
    res_cal = client.get('/api/audit/schedules')
    assert res_cal.status_code == 200, "일정 조회 API 에러"
    logger.info("✅ GET /api/audit/schedules 정상 응답")
    
    # 7. /api/audit/projects
    res_proj = client.get('/api/audit/projects')
    assert res_proj.status_code == 200, "프로젝트 조회 API 에러"
    logger.info("✅ GET /api/audit/projects 정상 응답")

if __name__ == '__main__':
    logger.info("🎯 AI 회계감사 자동화 시스템 전수 검증 시작\n" + "="*55)
    test_template_index()
    test_working_paper_generation()
    test_excel_export()
    test_flask_audit_routes()
    logger.info("\n" + "="*55 + "\n🎉 모든 단위/통합 테스트 100% 통과 완료!")
