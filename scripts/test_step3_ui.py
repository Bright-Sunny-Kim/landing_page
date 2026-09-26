# -*- coding: utf-8 -*-
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.extensions import MASTER_EMAIL

client = app.test_client()
with client.session_transaction() as sess:
    sess['email'] = MASTER_EMAIL
    sess['username'] = '마스터 관리자'
    sess['role'] = 'master'

# Master 페이지 렌더링 테스트
res = client.get('/master')
print('=== Master Page Render Test ===')
print('HTTP Status:', res.status_code)
html = res.get_data(as_text=True)

checks = [
    ('subtab-audit-assign', '감사팀 배정 서브탭'),
    ('assign-stat-total-companies', '총 수임사 통계 카드'),
    ('assign-stat-inprogress', '실증감사 진행중 통계 카드'),
    ('assign-stat-total-auditors', '감사인 풀 통계 카드'),
    ('master-auditor-workload-grid', '감사인 Workload 매트릭스 그리드'),
    ('filter-assign-company', '배정 목록 검색 인풋'),
    ('modal-assignment-logs', '감사팀 배정 변경 이력 모달')
]

for tag, desc in checks:
    present = tag in html
    status_str = "PASS" if present else "FAIL"
    print(f"[{status_str}] {desc} ({tag})")
