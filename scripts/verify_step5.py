# -*- coding: utf-8 -*-
"""
Step 5 검증 스크립트 (scripts/verify_step5.py)
core/notes_generator.py의 K-GAAP 주석 1~18번 자동 생성 및 상세 표 집계 무결성 검증
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

from core.notes_generator import (
    generate_note_company_overview,
    generate_note_equity_method_investments,
    generate_note_tangible_assets,
    generate_note_retained_earnings,
    generate_note_related_parties,
    generate_all_k_gaap_notes
)


class TestNotesGenerator(unittest.TestCase):
    """K-GAAP 주석 자동 생성기 단위 테스트"""

    def test_01_note_13_related_parties(self):
        """1. 주석 13번: 특수관계자 채권·채무 잔액 집계 검증"""
        note = generate_note_related_parties()
        self.assertEqual(note.get("note_number"), 13)
        self.assertEqual(len(note.get("tables", [])), 2, "특수관계자 표 2개 생성")
        # 채권/채무 표 합계 행 검증
        balance_table = note["tables"][1]
        self.assertEqual(balance_table[-1][0], "합 계")
        self.assertIn("1,520,000,000", balance_table[-1][1])

    def test_02_note_06_tangible_assets(self):
        """2. 주석 6번: 유형자산 취득/처분/감가상각 변동명세표 검증"""
        note = generate_note_tangible_assets()
        self.assertEqual(note.get("note_number"), 6)
        table = note["tables"][0]
        # 토지, 건물, 기계장치, 차량운반구, 비품 + 헤더 + 합계 = 7행
        self.assertEqual(len(table), 7)
        self.assertEqual(table[-1][0], "합 계")

    def test_03_note_10_retained_earnings(self):
        """3. 주석 10번: 이익잉여금 처분계산서 수치 일관성 검증"""
        note = generate_note_retained_earnings({
            "prior_unappropriated": 5000000000,
            "net_income": 6218936783,
            "dividends": 1000000000,
            "legal_reserve": 100000000
        })
        self.assertEqual(note.get("note_number"), 10)
        table = note["tables"][0]
        # 미처분이익잉여금(11,218,936,783) = 전기이월(50억) + 당기순익(62.18억)
        self.assertIn("11,218,936,783", table[1][1])

    def test_04_full_bundle_generation(self):
        """4. 주석 1~18번 전수 번들 생성 검증"""
        bundle = generate_all_k_gaap_notes(company_meta={"company_name": "주식회사 이노플로우"})
        self.assertEqual(len(bundle), 18, "총 18개 표준 주석 완벽 생성")
        note_numbers = [n["note_number"] for n in bundle]
        self.assertEqual(note_numbers, list(range(1, 19)), "1번부터 18번까지 연속 번호 일치")


def main():
    print("=" * 65)
    print(" [Step 5 검증] K-GAAP 주석(Notes 1~18) 자동 생성기 테스트")
    print("=" * 65)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNotesGenerator)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 65)
        print(" [ALL PASS] Step 5 주석 자동 생성기 4개 테스트 전원 통과!")
        print("=" * 65)
    else:
        print("\n[FAIL] Step 5 검증 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
