# -*- coding: utf-8 -*-
"""
Step 7 검증 스크립트 (scripts/verify_step7.py)
blueprints/audit.py의 4대 핵심 REST API 엔드포인트 E2E 호출 및 응답 무결성 검증
"""

import os
import sys
import json
import unittest

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import app


class TestAuditAPIEndpoints(unittest.TestCase):
    """4대 핵심 DSD 및 AJE/주석 REST API 엔드포인트 통합 테스트"""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_api_dsd_parse_prior(self):
        """1. POST /api/audit/dsd/parse-prior API 테스트"""
        payload = {"filename": "(주)이노플로우_감사보고서_25.dsd"}
        res = self.client.post('/api/audit/dsd/parse-prior', json=payload)
        self.assertEqual(res.status_code, 200, "상태코드 200 OK")
        
        data = res.get_json()
        self.assertTrue(data.get("success"), "API 응답 성공")
        dsd_data = data.get("data", {})
        self.assertEqual(dsd_data.get("company_name"), "주식회사 이노플로우")
        self.assertEqual(dsd_data.get("notes_count"), 18, "주석 18개 파싱")

    def test_02_api_aje_apply(self):
        """2. POST /api/audit/aje/apply API 테스트"""
        payload = {
            "raw_tb": [
                {"Account": "현금", "AccountCode": "10100", "Current": 10000000},
                {"Account": "매출채권", "AccountCode": "10800", "Current": 50000000},
                {"Account": "외상매입금", "AccountCode": "25100", "Current": 20000000},
                {"Account": "자본금", "AccountCode": "33100", "Current": 10000000},
                {"Account": "매출액", "AccountCode": "40100", "Current": 60000000},
                {"Account": "급여", "AccountCode": "80100", "Current": 30000000}
            ],
            "adjustments": [
                {
                    "description": "대손충당금 추가설정",
                    "entries": [
                        {"account_name": "대손상각비", "debit": 5000000, "credit": 0},
                        {"account_name": "매출채권", "debit": 0, "credit": 5000000}
                    ]
                }
            ]
        }
        res = self.client.post('/api/audit/aje/apply', json=payload)
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get("success"))
        adj_sum = data.get("data", {}).get("adjusted_summary", {})
        self.assertEqual(adj_sum.get("balance_diff"), 0, "대차평형 diff 0원")
        self.assertTrue(adj_sum.get("is_balanced"))

    def test_03_api_notes_generate(self):
        """3. POST /api/audit/notes/generate API 테스트"""
        payload = {
            "company_name": "주식회사 이노플로우",
            "fiscal_year": 2025
        }
        res = self.client.post('/api/audit/notes/generate', json=payload)
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("notes_count"), 18, "18개 K-GAAP 주석 생성")

    def test_04_api_dsd_build_export(self):
        """4. POST /api/audit/dsd/build-export API 파일 스트리밍 테스트"""
        payload = {
            "company_name": "주식회사 이노플로우",
            "cik": "01294846",
            "fiscal_year": 2025,
            "period": 15,
            "opinion_text": "적정의견입니다.",
            "audit_firm": "회계법인 혜안",
            "balance_sheet_data": {"items": [{"account_name": "자산총계", "current_amount": 1000000, "prior_amount": 900000}]},
            "income_statement_data": {"items": [{"account_name": "매출액", "current_amount": 500000, "prior_amount": 400000}]},
            "notes_data": [{"note_number": 1, "title": "1. 회사의 개요", "paragraphs": ["개요 본문"], "tables": []}]
        }
        res = self.client.post('/api/audit/dsd/build-export', json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/x-zip-compressed", res.headers.get("Content-Type", ""))
        self.assertGreater(len(res.data), 500, "DSD 바이너리 다운로드 확인")


def main():
    print("=" * 65)
    print(" [Step 7 검증] Flask REST API 4대 엔드포인트 E2E 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuditAPIEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 7 4대 신규 API 엔드포인트 전원 검증 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 7 API 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
