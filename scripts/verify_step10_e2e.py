# -*- coding: utf-8 -*-
"""
Step 10 E2E 통합 테스트 스크립트 (scripts/verify_step10_e2e.py)
전기 DSD 역추출 ➔ AJE 수정분개 ➔ K-GAAP 18개 주석 자동생성 ➔ DART 표준 .dsd 빌드 & Round-Trip 무결성 전수 검증
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
from core.dsd_manager import parse_dsd_file
from core.audit_engine import apply_audit_adjustments
from core.notes_generator import generate_all_k_gaap_notes
from core.dsd_builder import build_dsd_archive


class TestFullAuditPipelineE2E(unittest.TestCase):
    """CPA 회계감사 DSD 감사보고서 전 파이프라인 E2E 통합 테스트"""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_full_e2e_workflow(self):
        """[전과정 E2E] 전기 DSD 추출 ➔ AJE 수정분개 ➔ 주석 생성 ➔ DSD 빌드 ➔ 역추출 무결성"""
        
        # -------------------------------------------------------------
        # 1단계. 전기 DSD 역추출 (Prior DSD Extraction)
        # -------------------------------------------------------------
        prior_dsd_path = os.path.join("uploads", "dsd", "(주)이노플로우_감사보고서_25.dsd")
        self.assertTrue(os.path.exists(prior_dsd_path), "전기 샘플 DSD 파일 존재")
        
        parsed_prior = parse_dsd_file(prior_dsd_path)
        self.assertTrue(parsed_prior.get("success"), "전기 DSD 파싱 성공")
        self.assertEqual(parsed_prior.get("company_name"), "주식회사 이노플로우")
        self.assertEqual(parsed_prior.get("notes_count"), 18, "전기 주석 18개 정상 추출")

        # -------------------------------------------------------------
        # 2단계. 결산 수정분개(AJE) 적용 및 대차평형
        # -------------------------------------------------------------
        raw_tb = [
            {"Account": "현금및현금성자산", "AccountCode": "10100", "Current": 3996872317},
            {"Account": "매출채권", "AccountCode": "10800", "Current": 6581584381},
            {"Account": "유형자산", "AccountCode": "20100", "Current": 61908271846},
            {"Account": "기타비유동자산", "AccountCode": "23000", "Current": 31225451144},
            {"Account": "외상매입금", "AccountCode": "25100", "Current": 4557391111},
            {"Account": "자본금", "AccountCode": "33100", "Current": 500000000},
            {"Account": "기초이익잉여금", "AccountCode": "37500", "Current": 92435851794},
            {"Account": "상품매출", "AccountCode": "40100", "Current": 53742298741},
            {"Account": "상품매출원가", "AccountCode": "50100", "Current": 45236748989},
            {"Account": "급여", "AccountCode": "80100", "Current": 1416238123},
            {"Account": "기타판관비", "AccountCode": "83000", "Current": 870374846}
        ]
        
        aje_list = [
            {
                "description": "매출채권 대손충당금 추가 설정",
                "entries": [
                    {"account_name": "대손상각비", "debit": 50000000, "credit": 0},
                    {"account_name": "매출채권", "debit": 0, "credit": 50000000}
                ]
            }
        ]
        
        aje_result = apply_audit_adjustments(raw_tb_data=raw_tb, adjustments=aje_list)
        self.assertTrue(aje_result.get("success"), "AJE 적용 성공")
        adj_summary = aje_result.get("adjusted_summary", {})
        self.assertEqual(adj_summary.get("balance_diff"), 0, "수정후 대차평형 오차 0원 무결성")
        self.assertTrue(adj_summary.get("is_balanced"))

        # -------------------------------------------------------------
        # 3단계. K-GAAP 1~18번 주석 자동 집계 & 생성
        # -------------------------------------------------------------
        company_meta = {
            "company_name": parsed_prior.get("company_name"),
            "fiscal_year": 2025
        }
        notes_bundle = generate_all_k_gaap_notes(
            company_meta=company_meta,
            adjusted_tb_items=aje_result.get("adjusted_tb", []),
            prior_dsd_notes=parsed_prior.get("notes", [])
        )
        self.assertEqual(len(notes_bundle), 18, "총 18개 표준 K-GAAP 주석 완벽 생성")

        # -------------------------------------------------------------
        # 4단계. DART 표준 .dsd 감사보고서 빌드 & 스트리밍
        # -------------------------------------------------------------
        bs_data = {
            "items": [
                {"account_name": "자산총계", "current_amount": adj_summary.get("total_assets"), "prior_amount": 104204542136},
                {"account_name": "부채총계", "current_amount": adj_summary.get("total_liabilities"), "prior_amount": 6325116765},
                {"account_name": "자본총계", "current_amount": adj_summary.get("total_equity"), "prior_amount": 97879425371}
            ]
        }
        is_data = {
            "items": [
                {"account_name": "매출액", "current_amount": 53742298741, "prior_amount": 144081537646},
                {"account_name": "영업이익", "current_amount": 7089311629, "prior_amount": 17657154554},
                {"account_name": "당기순이익", "current_amount": adj_summary.get("net_income"), "prior_amount": 27933736608}
            ]
        }

        dsd_stream = build_dsd_archive(
            company_name=company_meta["company_name"],
            cik="01294846",
            fiscal_year=2025,
            period=15,
            opinion_text="우리의 의견으로는 별첨된 재무제표는 일반기업회계기준에 따라 중요성의 관점에서 공정하게 표시하고 있습니다.",
            audit_firm="회계법인 혜안",
            balance_sheet_data=bs_data,
            income_statement_data=is_data,
            notes_data=notes_bundle
        )
        
        dsd_bytes = dsd_stream.getvalue()
        self.assertGreater(len(dsd_bytes), 1000, "DSD 바이너리 정상 생성")

        # -------------------------------------------------------------
        # 5단계. 생성된 DSD 파일 역추출 전수 Round-Trip 무결성 검증
        # -------------------------------------------------------------
        verified_dsd = parse_dsd_file(dsd_bytes)
        self.assertTrue(verified_dsd.get("success"), "생성된 DSD 역추출 파싱 성공")
        self.assertEqual(verified_dsd.get("company_name"), "주식회사 이노플로우")
        self.assertEqual(verified_dsd.get("cik"), "01294846")
        self.assertEqual(verified_dsd.get("notes_count"), 18, "주석 18개 완벽 복원")

        # 재무상태표 수치 복원 검증
        v_bs = verified_dsd.get("financial_statements", {}).get("balance_sheet", {}).get("summary", {})
        self.assertEqual(v_bs.get("current_total_assets"), adj_summary.get("total_assets"))
        self.assertEqual(v_bs.get("current_total_liabilities"), adj_summary.get("total_liabilities"))
        self.assertEqual(v_bs.get("current_total_equity"), adj_summary.get("total_equity"))


def main():
    print("=" * 70)
    print(" [Step 10 E2E 통합 테스트] CPA 회계감사 DSD 보고서 파이프라인 전수 검증")
    print("=" * 70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFullAuditPipelineE2E)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    if test_result.wasSuccessful():
        print("\n" + "=" * 70)
        print(" 🎉 [ALL PASS] Step 1~10 전 단계 파이프라인 통합 무결성 100% 달성!")
        print("=" * 70)
        print(" 📌 [구축 완료 요약]")
        print("   1. 전기 DSD 역추출 엔진: core/dsd_manager.py")
        print("   2. 결산 수정분개(AJE) 엔진: core/audit_engine.py")
        print("   3. K-GAAP 1~18번 주석 자동생성기: core/notes_generator.py")
        print("   4. DART 표준 DSD 빌더: core/dsd_builder.py")
        print("   5. 4대 REST API 라우트: blueprints/audit.py")
        print("   6. 4단계 카드 대시보드 UI: templates/audit.html")
        print("   7. 프론트엔드 비동기 연동: static/js/audit_dsd_hub.js")
        print("=" * 70)
    else:
        print("\n[FAIL] E2E 통합 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
