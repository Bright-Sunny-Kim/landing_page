# -*- coding: utf-8 -*-
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()
with client.session_transaction() as sess:
    sess['email'] = 'cpaeastsun@gmail.com'
    sess['username'] = '김동선 대표회계사'
    sess['role'] = 'master'

# 1. 배정 수정/생성 테스트 (POST /api/audit/assignments)
payload = {
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
    "target_report_date": "2026-03-25"
}

res_post = client.post('/api/audit/assignments', json=payload)
print('=== 1. Assignment Save & Log Record Response ===')
print('POST Status:', res_post.status_code)
d_post = res_post.get_json()
print('Success:', d_post.get('success'))

# 2. 배정 변경 이력 조회 테스트 (GET /api/audit/assignment-logs)
res_logs = client.get('/api/audit/assignment-logs?company_name=(주)프레오')
print('\n=== 2. Assignment Logs Query Response ===')
print('GET Status:', res_logs.status_code)
d_logs = res_logs.get_json()
print('Logs Count:', d_logs.get('count'))
if d_logs.get('logs'):
    latest_log = d_logs.get('logs')[0]
    print('Latest Log:', {
        'id': latest_log.get('id'),
        'created_at': latest_log.get('created_at'),
        'company_name': latest_log.get('company_name'),
        'action_type': latest_log.get('action_type'),
        'changed_by': latest_log.get('changed_by'),
        'diff_summary': latest_log.get('diff_summary')
    })
