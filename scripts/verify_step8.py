# -*- coding: utf-8 -*-
"""
Step 8 검증 스크립트 (scripts/verify_step8.py)
templates/audit.html의 4단계 원스톱 DSD 카드 대시보드 및 DART 뷰어 DOM 렌더링 무결성 검증
"""

import os
import sys
import unittest

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import app


class TestAuditHtmlDashboard(unittest.TestCase):
    """audit.html의 4단계 DSD 카드 대시보드 HTML 렌더링 검증"""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_audit_page_rendering_and_4step_elements(self):
        """1. /audit 뷰 렌더링 및 4단계 DSD 대시보드 핵심 DOM 요소 존재 확인"""
        with self.client.session_transaction() as sess:
            sess['email'] = 'cpaeastsun@gmail.com'
            sess['role'] = 'cpa'
            sess['username'] = '담당회계사'
            sess['company'] = '회계법인 혜안'

        res = self.client.get('/audit')
        self.assertEqual(res.status_code, 200, "/audit 페이지 로드 200 OK")
        
        html = res.get_data(as_text=True)

        # 1. 4단계 워크플로우 진행 바 검증
        self.assertIn('dsd-workflow-bar', html, "4단계 워크플로우 진행 바")
        self.assertIn('data-dsd-step="1"', html, "Step 1 네비")
        self.assertIn('data-dsd-step="2"', html, "Step 2 네비")
        self.assertIn('data-dsd-step="3"', html, "Step 3 네비")
        self.assertIn('data-dsd-step="4"', html, "Step 4 네비")

        # 2. 4대 카드 섹션 검증
        self.assertIn('id="dsd-pane-step-1"', html, "Step 1 카드 (전기 DSD 업로드)")
        self.assertIn('id="dsd-dropzone"', html, "DSD 드롭존")
        
        self.assertIn('id="dsd-pane-step-2"', html, "Step 2 카드 (수정분개 AJE)")
        self.assertIn('id="table-aje-entries"', html, "AJE 입력 테이블")
        self.assertIn('id="btn-apply-aje"', html, "AJE 실시간 반영 버튼")

        self.assertIn('id="dsd-pane-step-3"', html, "Step 3 카드 (주석 1~18번 검토)")
        self.assertIn('id="notes-sidebar-list"', html, "주석 목차 사이드바")
        self.assertIn('id="notes-content-viewer"', html, "주석 내용 뷰어")

        self.assertIn('id="dsd-pane-step-4"', html, "Step 4 카드 (DSD 빌드 & 다운로드)")
        self.assertIn('id="btn-export-final-dsd"', html, "DSD 다운로드 버튼")
        self.assertIn('id="dsd-view-preview"', html, "DART 서식 뷰어")
        self.assertIn('id="dsd-view-xml"', html, "DART XML 뷰어")

        # 3. JS 스크립트 연결 검증
        self.assertIn('audit_dsd_hub.js', html, "audit_dsd_hub.js 스크립트 태그 포함")


def main():
    print("=" * 65)
    print(" [Step 8 검증] audit.html 4단계 DSD 카드 대시보드 UI 렌더링 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuditHtmlDashboard)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 8 4단계 원스톱 카드 대시보드 UI 렌더링 전원 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 8 UI 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
