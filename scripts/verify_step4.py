# -*- coding: utf-8 -*-
"""
Step 4 검증 스크립트 (scripts/verify_step4.py)
core/audit_engine.py의 apply_audit_adjustments() 엔진 기능 및 대차평형 실시간 재계산 검증
"""

import os
import sys
import unittest
import pandas as pd

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.audit_engine import apply_audit_adjustments, classify_account_type


class TestAuditAdjustmentEngine(unittest.TestCase):
    """결산 수정분개(AJE) 엔진 및 수정후 T/B 대차평형 검증"""

    def setUp(self):
        # 1. 기초 원시 시산표(Raw T/B) 세팅
        self.raw_tb = [
            {"Account": "현금및현금성자산", "AccountCode": "10100", "Current": 10000000},
            {"Account": "매출채권", "AccountCode": "10800", "Current": 50000000},
            {"Account": "외상매입금", "AccountCode": "25100", "Current": 20000000},
            {"Account": "자본금", "AccountCode": "33100", "Current": 10000000},
            {"Account": "상품매출", "AccountCode": "40100", "Current": 60000000},
            {"Account": "급여", "AccountCode": "80100", "Current": 30000000},
        ]

        # 2. 회계사 결산 수정분개(AJE) 2건 세팅
        self.adjustments = [
            {
                "id": 1,
                "description": "매출채권 대손충당금 추가 설정",
                "entries": [
                    {"account_name": "대손상각비", "debit": 5000000, "credit": 0},
                    {"account_name": "매출채권", "debit": 0, "credit": 5000000}
                ]
            },
            {
                "id": 2,
                "description": "결산일 미지급 수수료 비용 추가 계상",
                "entries": [
                    {"account_name": "지급수수료", "debit": 2000000, "credit": 0},
                    {"account_name": "미지급금", "debit": 0, "credit": 2000000}
                ]
            }
        ]

    def test_01_account_classification(self):
        """1. 계정과목 자동 분류(자산/부채/자본/수익/비용) 검증"""
        self.assertEqual(classify_account_type("보통예금", "10300"), "ASSET")
        self.assertEqual(classify_account_type("단기차입금", "26000"), "LIABILITY")
        self.assertEqual(classify_account_type("이익잉여금", "37500"), "EQUITY")
        self.assertEqual(classify_account_type("제품매출", "40400"), "REVENUE")
        self.assertEqual(classify_account_type("감가상각비", "81800"), "EXPENSE")

    def test_02_aje_application_and_balance_integrity(self):
        """2. AJE 적용 후 수정후 T/B 및 대차평형 ($0 오차) 검증"""
        result = apply_audit_adjustments(self.raw_tb, self.adjustments)
        self.assertTrue(result.get("success"), "AJE 엔진 실행 성공")

        unadj = result.get("unadjusted_summary", {})
        adj = result.get("adjusted_summary", {})
        aje_sum = result.get("adjustments_summary", {})

        # (1) 수정전 상태 점검
        self.assertEqual(unadj.get("total_assets"), 60000000, "수정전 자산총계")
        self.assertEqual(unadj.get("total_liabilities"), 20000000, "수정전 부채총계")
        self.assertEqual(unadj.get("net_income"), 30000000, "수정전 당기순이익 (6000만 - 3000만)")
        self.assertEqual(unadj.get("balance_diff"), 0, "수정전 대차평형 오차 0원")
        self.assertTrue(unadj.get("is_balanced"))

        # (2) AJE 분개 집계 점검
        self.assertEqual(aje_sum.get("total_aje_count"), 2, "AJE 건수 2건")
        self.assertEqual(aje_sum.get("total_debit"), 7000000, "AJE 차변 합계 (500만 + 200만)")
        self.assertEqual(aje_sum.get("total_credit"), 7000000, "AJE 대변 합계 (500만 + 200만)")
        self.assertTrue(aje_sum.get("is_balanced"), "AJE 자체 대차평형 일치")

        # (3) 수정후 최종 상태 점검
        # 자산: 6000만 - 500만 = 5500만
        self.assertEqual(adj.get("total_assets"), 55000000, "수정후 자산총계")
        # 부채: 2000만 + 200만 = 2200만
        self.assertEqual(adj.get("total_liabilities"), 22000000, "수정후 부채총계")
        # 비용: 3000만 + 700만 = 3700만 -> 순익: 6000만 - 3700만 = 2300만
        self.assertEqual(adj.get("net_income"), 23000000, "수정후 당기순이익")
        # 실질자본: 자본금 1000만 + 순익 2300만 = 3300만
        self.assertEqual(adj.get("total_equity"), 33000000, "수정후 자본총계")
        # 부채(2200만) + 자본(3300만) = 5500만 = 자산(5500만)
        self.assertEqual(adj.get("balance_diff"), 0, "수정후 대차평형 오차 0원")
        self.assertTrue(adj.get("is_balanced"), "수정후 대차평형 무결성 보장")


def main():
    print("=" * 65)
    print(" [Step 4 검증] 결산 수정분개(AJE) 엔진 & 실시간 대차평형 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuditAdjustmentEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 4 AJE 엔진 및 대차 무결성 검증 완벽 통과!")
        print("=" * 65)
        print(" 📊 [AJE 시뮬레이션 결과 요약]")
        print("   - 수정전: 자산 60,000,000 | 부채 20,000,000 | 자본 40,000,000 (순익 30,000,000)")
        print("   - 수정분개(AJE): 대손충당금 5,000,000 설정 + 미지급수수료 2,000,000 계상")
        print("   - 수정후: 자산 55,000,000 | 부채 22,000,000 | 자본 33,000,000 (순익 23,000,000)")
        print("   - 대차평형 검증: 자산(55,000,000) == 부채(22,000,000) + 자본(33,000,000) (오차: 0원)")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 4 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
