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
print('=== Master Page Modal & Datalist Render Test ===')
print('HTTP Status:', res.status_code)
html = res.get_data(as_text=True)

checks = [
    ('auditor-pool-datalist', '감사인 풀 Datalist 태그'),
    ('assign-staff-checkboxes-container', '참여 감사팀원 다중 선택 컨테이너'),
    ('assign-inventory-date', '기초 재고실사일 입력 필드'),
    ('assign-target-report-date', '보고서 발행 예정일 입력 필드'),
    ('assign-acc-A-0', '금융 계정 조서 담당자 필드'),
    ('assign-acc-C-0', '채권 계정 조서 담당자 필드'),
    ('assign-acc-E-0', '재고 계정 조서 담당자 필드'),
    ('assign-acc-G-0', '유형 계정 조서 담당자 필드')
]

for tag, desc in checks:
    present = tag in html
    status_str = "PASS" if present else "FAIL"
    print(f"[{status_str}] {desc} ({tag})")
