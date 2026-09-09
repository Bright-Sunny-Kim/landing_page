# -*- coding: utf-8 -*-
"""
Step 6 검증 스크립트 (scripts/verify_step6.py)
core/dsd_builder.py의 DSD 생성 및 core/dsd_manager.py 역추출 Round-Trip 양방향 무결성 검증
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

from core.dsd_builder import build_dsd_archive
from core.dsd_manager import parse_dsd_file
from core.notes_generator import generate_all_k_gaap_notes


class TestDSDBuilderRoundTrip(unittest.TestCase):
    """DSD 빌더 생성 및 파서 역추출 Round-Trip 무결성 검증"""

    def setUp(self):
        self.company_name = "주식회사 이노플로우"
        self.cik = "01294846"
        self.fiscal_year = 2025
        self.period = 15
        self.opinion_text = "우리의 의견으로는 별첨된 재무제표는 일반기업회계기준에 따라 중요성의 관점에서 공정하게 표시하고 있습니다."
        self.audit_firm = "회계법인 혜안"

        # 재무상태표 샘플
        self.bs_data = {
            "items": [
                {"account_name": "Ⅰ.유동자산", "current_amount": 41803907842, "prior_amount": 58560809225},
                {"account_name": "Ⅱ.비유동자산", "current_amount": 61908271846, "prior_amount": 45643732911},
                {"account_name": "자산총계", "current_amount": 103712179688, "prior_amount": 104204542136},
                {"account_name": "부채총계", "current_amount": 4557391111, "prior_amount": 6325116765},
                {"account_name": "자본총계", "current_amount": 99154788577, "prior_amount": 97879425371}
            ]
        }

        # 손익계산서 샘플
        self.is_data = {
            "items": [
                {"account_name": "Ⅰ.매출액", "current_amount": 53742298741, "prior_amount": 144081537646},
                {"account_name": "Ⅱ.매출원가", "current_amount": 45236748989, "prior_amount": 120622239193},
                {"account_name": "Ⅴ.영업이익", "current_amount": 7089311629, "prior_amount": 17657154554},
                {"account_name": "Ⅹ.당기순이익", "current_amount": 6218936783, "prior_amount": 27933736608}
            ]
        }

        # 주석 1~18번 생성
        self.notes_data = generate_all_k_gaap_notes({"company_name": self.company_name})

    def test_01_build_and_roundtrip_parse(self):
        """1. DSD 바이너리 생성 후 DSD 파서로 역추출하여 Round-Trip 일치성 검증"""
        # (1) DSD ZIP 아카이브 빌드
        dsd_stream = build_dsd_archive(
            company_name=self.company_name,
            cik=self.cik,
            fiscal_year=self.fiscal_year,
            period=self.period,
            opinion_text=self.opinion_text,
            audit_firm=self.audit_firm,
            balance_sheet_data=self.bs_data,
            income_statement_data=self.is_data,
            notes_data=self.notes_data
        )

        dsd_bytes = dsd_stream.getvalue()
        self.assertGreater(len(dsd_bytes), 1000, "DSD 바이너리 용량 1KB 이상 생성 확인")

        # (2) 파서로 즉시 역추출
        parsed = parse_dsd_file(dsd_bytes)
        self.assertTrue(parsed.get("success"), "생성된 DSD 파일 역추출 성공")
        self.assertEqual(parsed.get("company_name"), self.company_name, "회사명 일치")
        self.assertEqual(parsed.get("cik"), self.cik, "CIK 코드 일치")

        # (3) 재무상태표 수치 복원 검증
        bs_summary = parsed.get("financial_statements", {}).get("balance_sheet", {}).get("summary", {})
        self.assertEqual(bs_summary.get("current_total_assets"), 103712179688, "자산총계 복원")
        self.assertEqual(bs_summary.get("current_total_liabilities"), 4557391111, "부채총계 복원")
        self.assertEqual(bs_summary.get("current_total_equity"), 99154788577, "자본총계 복원")

        # (4) 손익계산서 수치 복원 검증
        is_summary = parsed.get("financial_statements", {}).get("income_statement", {}).get("summary", {})
        self.assertEqual(is_summary.get("current_revenue"), 53742298741, "매출액 복원")
        self.assertEqual(is_summary.get("current_operating_income"), 7089311629, "영업이익 복원")
        self.assertEqual(is_summary.get("current_net_income"), 6218936783, "당기순이익 복원")

        # (5) 18개 주석 복원 검증
        self.assertEqual(parsed.get("notes_count"), 18, "18개 주석 100% 온전 복원")


def main():
    print("=" * 65)
    print(" [Step 6 검증] DART 표준 DSD 빌더 & Round-Trip 무결성 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDSDBuilderRoundTrip)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 6 DSD 빌더 및 Round-Trip 역추출 무결성 전원 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 6 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
