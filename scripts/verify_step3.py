# -*- coding: utf-8 -*-
"""
Step 3 단위 테스트 스크립트 (scripts/verify_step3.py)
(주)이노플로우_감사보고서_25.dsd 대상 상세 항목별 파싱 정확도 및 대차 무결성 전수 검증
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

from core.dsd_manager import parse_dsd_file, clean_amount


class TestDSDParserAccuracy(unittest.TestCase):
    """DSD 파서의 세부 항목 추출 정확도 및 K-GAAP 무결성 테스트"""

    @classmethod
    def setUpClass(cls):
        cls.dsd_path = os.path.join("uploads", "dsd", "(주)이노플로우_감사보고서_25.dsd")
        if not os.path.exists(cls.dsd_path):
            raise FileNotFoundError(f"DSD file not found: {cls.dsd_path}")
        cls.result = parse_dsd_file(cls.dsd_path)
        cls.bs = cls.result.get("financial_statements", {}).get("balance_sheet", {})
        cls.income = cls.result.get("financial_statements", {}).get("income_statement", {})
        cls.notes = cls.result.get("notes", [])

    def test_01_metadata_extraction(self):
        """1. 기업명 및 CIK 메타데이터 검증"""
        self.assertTrue(self.result.get("success"), "DSD 파싱 성공 여부")
        self.assertEqual(self.result.get("company_name"), "주식회사 이노플로우", "기업명 일치 여부")
        self.assertEqual(self.result.get("cik"), "01294846", "CIK 코드 일치 여부")

    def test_02_balance_sheet_integrity(self):
        """2. 재무상태표 대차평형 (자산 = 부채 + 자본) 무결성 검증"""
        summary = self.bs.get("summary", {})
        cur_assets = summary.get("current_total_assets")
        cur_liab = summary.get("current_total_liabilities")
        cur_equity = summary.get("current_total_equity")
        
        pri_assets = summary.get("prior_total_assets")
        pri_liab = summary.get("prior_total_liabilities")
        pri_equity = summary.get("prior_total_equity")

        # 당기 검증 (2025년 / 제 15기)
        self.assertEqual(cur_assets, 103712179688, "당기 자산총계 정확도")
        self.assertEqual(cur_liab, 4557391111, "당기 부채총계 정확도")
        self.assertEqual(cur_equity, 99154788577, "당기 자본총계 정확도")
        self.assertEqual(cur_assets, cur_liab + cur_equity, "당기 대차평형 (자산 = 부채 + 자본)")

        # 전기 검증 (2024년 / 제 14기)
        self.assertEqual(pri_assets, 104204542136, "전기 자산총계 정확도")
        self.assertEqual(pri_liab, 6325116765, "전기 부채총계 정확도")
        self.assertEqual(pri_equity, 97879425371, "전기 자본총계 정확도")
        self.assertEqual(pri_assets, pri_liab + pri_equity, "전기 대차평형 (자산 = 부채 + 자본)")

    def test_03_income_statement_accuracy(self):
        """3. 손익계산서 주요 계정 수치 정확도 검증"""
        summary = self.income.get("summary", {})
        
        # 당기 주요 지표
        self.assertEqual(summary.get("current_revenue"), 53742298741, "당기 매출액")
        self.assertEqual(summary.get("current_operating_income"), 7089311629, "당기 영업이익")
        self.assertEqual(summary.get("current_net_income"), 6218936783, "당기 순이익")

        # 전기 주요 지표
        self.assertEqual(summary.get("prior_revenue"), 144081537646, "전기 매출액")
        self.assertEqual(summary.get("prior_operating_income"), 17657154554, "전기 영업이익")
        self.assertEqual(summary.get("prior_net_income"), 27933736608, "전기 순이익")

    def test_04_notes_count_and_titles(self):
        """4. 주석(Notes) 18개 전수 매핑 및 핵심 주석 번호 확인"""
        self.assertEqual(len(self.notes), 18, "총 주석 개수 18개 일치")
        
        note_dict = {n["note_number"]: n for n in self.notes}
        
        # 핵심 주석 존재 여부 점검
        self.assertIn(1, note_dict, "주석 1번: 회사의 개요")
        self.assertIn(5, note_dict, "주석 5번: 지분법적용투자주식")
        self.assertIn(6, note_dict, "주석 6번: 유형자산")
        self.assertIn(10, note_dict, "주석 10번: 이익잉여금")
        self.assertIn(13, note_dict, "주석 13번: 특수관계자와의 거래")
        self.assertIn(18, note_dict, "주석 18번: 재무제표의 최종승인")

        # 주석 13번(특수관계자) 테이블 개수 검증 (11개 표 포함)
        self.assertEqual(len(note_dict[13]["tables"]), 11, "주석 13번 특수관계자 내부 표 개수")


def main():
    print("=" * 65)
    print(" [Step 3 단위 테스트] DSD 파서 정밀도 & K-GAAP 대차 무결성 전수 검증")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDSDParserAccuracy)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] 총 4개 핵심 테스트 항목(15개 세부 assertion) 전원 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] 일부 테스트가 실패하였습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
