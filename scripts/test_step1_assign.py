# -*- coding: utf-8 -*-
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()
with client.session_transaction() as sess:
    sess['email'] = 'cpaeastsun@gmail.com'
    sess['role'] = 'master'

# 1. Auditor Pool API Test
res1 = client.get('/api/audit/auditor-pool')
print('=== 1. Auditor Pool API Response ===')
print('Status:', res1.status_code)
d1 = res1.get_json()
print('Auditors Count:', d1.get('count'))
if d1.get('auditors'):
    print('Sample Auditor:', d1.get('auditors')[0])

# 2. Assignment Summary API Test
res2 = client.get('/api/audit/assignment-summary')
print('\n=== 2. Assignment Summary API Response ===')
print('Status:', res2.status_code)
d2 = res2.get_json()
summary = d2.get('summary', {})
print('Total Companies:', summary.get('total_companies'))
print('In Progress:', summary.get('in_progress_count'))
print('Total Assigned Auditors:', summary.get('total_auditors'))
if summary.get('workload'):
    print('Workload Sample:', summary.get('workload')[0])
