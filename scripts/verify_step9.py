# -*- coding: utf-8 -*-
"""
Step 9 검증 스크립트 (scripts/verify_step9.py)
static/js/audit_dsd_hub.js의 프론트엔드 비동기 컨트롤러 및 정적 에셋 서빙 검증
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


class TestAuditDsdHubJs(unittest.TestCase):
    """audit_dsd_hub.js 파일 구조 및 Flask 정적 파일 서빙 검증"""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_js_file_structure_and_handlers(self):
        """1. static/js/audit_dsd_hub.js 핵심 함수 및 이벤트 핸들러 검증"""
        js_path = os.path.join("static", "js", "audit_dsd_hub.js")
        self.assertTrue(os.path.exists(js_path), "audit_dsd_hub.js 파일 존재")
        
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        # 핵심 함수 및 핸들러 포함 여부 검증
        self.assertIn("window.switchDsdStep", js_content, "4단계 전환 함수")
        self.assertIn("handleDsdFileUpload", js_content, "Step 1 DSD 드래그앤드롭 업로드 핸들러")
        self.assertIn("applyParsedDsdData", js_content, "전기 데이터 렌더링 핸들러")
        self.assertIn("/api/audit/aje/apply", js_content, "Step 2 AJE 비동기 API 호출")
        self.assertIn("/api/audit/notes/generate", js_content, "Step 3 주석 자동생성 API 호출")
        self.assertIn("renderNotesSidebar", js_content, "주석 1~18번 사이드바 렌더러")
        self.assertIn("/api/audit/dsd/build-export", js_content, "Step 4 DSD 다운로드 API 호출")

    def test_02_static_serving(self):
        """2. Flask 앱을 통한 /static/js/audit_dsd_hub.js HTTP 200 서빙 검증"""
        res = self.client.get('/static/js/audit_dsd_hub.js')
        self.assertEqual(res.status_code, 200, "JS 파일 서빙 200 OK")
        self.assertIn("javascript", res.headers.get("Content-Type", "").lower())
        self.assertGreater(len(res.data), 1000, "JS 파일 크기 1KB 이상")


def main():
    print("=" * 65)
    print(" [Step 9 검증] audit_dsd_hub.js 프론트엔드 비동기 컨트롤러 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuditDsdHubJs)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 9 프론트엔드 JS 연동 및 서빙 전원 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 9 JS 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
