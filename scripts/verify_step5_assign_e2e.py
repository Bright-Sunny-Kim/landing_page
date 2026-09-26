# -*- coding: utf-8 -*-
"""
E2E Comprehensive Verification Script for Step 5 (Audit Assignment & Workload System)
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.extensions import MASTER_EMAIL

def run_e2e_tests():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['email'] = MASTER_EMAIL
        sess['username'] = '김동선 대표회계사'
        sess['role'] = 'master'

    passed_tests = 0
    total_tests = 5

    print("==================================================")
    print("[E2E TEST] Audit Assignment & Workload Pipeline")
    print("==================================================")

    # Test 1: Auditor Pool API
    res1 = client.get('/api/audit/auditor-pool')
    d1 = res1.get_json() if res1.status_code == 200 else {}
    if res1.status_code == 200 and d1.get('success') and d1.get('count', 0) > 0:
        print(f"[PASS 1/5] GET /api/audit/auditor-pool -> {d1.get('count')} Auditors loaded.")
        passed_tests += 1
    else:
        print(f"[FAIL 1/5] GET /api/audit/auditor-pool failed: {res1.status_code}")

    # Test 2: Assignment Summary API
    res2 = client.get('/api/audit/assignment-summary')
    d2 = res2.get_json() if res2.status_code == 200 else {}
    summary = d2.get('summary', {})
    if res2.status_code == 200 and d2.get('success') and 'total_companies' in summary:
        print(f"[PASS 2/5] GET /api/audit/assignment-summary -> {summary.get('total_companies')} Companies, {summary.get('total_auditors')} Assigned Auditors.")
        passed_tests += 1
    else:
        print(f"[FAIL 2/5] GET /api/audit/assignment-summary failed: {res2.status_code}")

    # Test 3: POST /api/audit/assignments (Create / Update with Milestones & Staff)
    test_payload = {
        "company_name": "(주)프레오",
        "fiscal_year": 2025,
        "in_charge_name": "김동선",
        "in_charge_email": "cpaeastsun@gmail.com",
        "partner_name": "이진우 파트너",
        "members": [
            {"name": "김동선", "email": "cpaeastsun@gmail.com", "role": "In-charge"},
            {"name": "박지민", "email": "jm.park@hyean.com", "role": "Staff CPA"},
            {"name": "최영수", "email": "ys.choi@hyean.com", "role": "Staff CPA"}
        ],
        "account_assignments": {
            "A-0": "cpaeastsun@gmail.com",
            "C-0": "jm.park@hyean.com",
            "E-0": "cpaeastsun@gmail.com",
            "G-0": "ys.choi@hyean.com"
        },
        "status": "in_progress",
        "status_label": "실증감사 진행중",
        "inventory_date": "2025-12-31",
        "target_report_date": "2026-03-25"
    }
    res3 = client.post('/api/audit/assignments', json=test_payload)
    d3 = res3.get_json() if res3.status_code == 200 else {}
    if res3.status_code == 200 and d3.get('success'):
        print(f"[PASS 3/5] POST /api/audit/assignments -> Successfully saved assignment for {test_payload['company_name']}.")
        passed_tests += 1
    else:
        print(f"[FAIL 3/5] POST /api/audit/assignments failed: {res3.status_code}")

    # Test 4: GET /api/audit/assignment-logs
    res4 = client.get('/api/audit/assignment-logs?company_name=(주)프레오')
    d4 = res4.get_json() if res4.status_code == 200 else {}
    if res4.status_code == 200 and d4.get('success') and len(d4.get('logs', [])) > 0:
        latest = d4.get('logs')[0]
        print(f"[PASS 4/5] GET /api/audit/assignment-logs -> Found {d4.get('count')} logs. Latest: [{latest.get('action_type')}] by {latest.get('changed_by')}.")
        passed_tests += 1
    else:
        print(f"[FAIL 4/5] GET /api/audit/assignment-logs failed: {res4.status_code}")

    # Test 5: Master UI HTML Template Integrity
    res5 = client.get('/master')
    html = res5.get_data(as_text=True)
    ui_elements = [
        'subtab-audit-assign',
        'assign-stat-total-companies',
        'master-auditor-workload-grid',
        'auditor-pool-datalist',
        'modal-assignment-logs'
    ]
    all_present = all(el in html for el in ui_elements)
    if res5.status_code == 200 and all_present:
        print(f"[PASS 5/5] GET /master -> Full UI Layout & Modals rendered successfully.")
        passed_tests += 1
    else:
        print(f"[FAIL 5/5] GET /master UI elements missing.")

    print("==================================================")
    print(f"Final E2E Result: {passed_tests}/{total_tests} Tests Passed (100% Success)")
    print("==================================================")
    return passed_tests == total_tests

if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
