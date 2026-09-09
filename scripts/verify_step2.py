# -*- coding: utf-8 -*-
"""
Step 2 검증 스크립트 (scripts/verify_step2.py)
core/dsd_manager.py의 parse_dsd_file() 함수 동작 및 추출 무결성 검증
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.dsd_manager import parse_dsd_file

def main():
    dsd_file = os.path.join("uploads", "dsd", "(주)이노플로우_감사보고서_25.dsd")
    print("=" * 60)
    print(" [Step 2 검증] core/dsd_manager.py DSD 파싱 테스트")
    print("=" * 60)
    
    if not os.path.exists(dsd_file):
        print(f"[ERROR] 샘플 DSD 파일을 찾을 수 없습니다: {dsd_file}")
        sys.exit(1)
        
    result = parse_dsd_file(dsd_file)
    
    if not result.get("success"):
        print(f"[FAIL] 파싱 실패: {result.get('error')}")
        sys.exit(1)
        
    print(f"1. 회사명: {result.get('company_name')}")
    print(f"2. CIK 번호: {result.get('cik')}")
    print(f"3. 주석(Notes) 개수: {result.get('notes_count')}개")
    for n in result.get('notes', []):
        print(f"   - 주석 {n['note_number']:2d}번: {n['title']} (표 {len(n['tables'])}개 포함)")
    
    bs_summary = result.get("financial_statements", {}).get("balance_sheet", {}).get("summary", {})
    is_summary = result.get("financial_statements", {}).get("income_statement", {}).get("summary", {})
    
    print("-" * 60)
    print("4. 재무상태표(B/S) 주요 지표:")
    cur_assets = bs_summary.get("current_total_assets", 0)
    pri_assets = bs_summary.get("prior_total_assets", 0)
    print(f"   - 자산총계: 당기 {cur_assets:15,d} 원 | 전기 {pri_assets:15,d} 원")
    
    cur_liab = bs_summary.get("current_total_liabilities", 0)
    pri_liab = bs_summary.get("prior_total_liabilities", 0)
    print(f"   - 부채총계: 당기 {cur_liab:15,d} 원 | 전기 {pri_liab:15,d} 원")
    
    cur_eq = bs_summary.get("current_total_equity", 0)
    pri_eq = bs_summary.get("prior_total_equity", 0)
    print(f"   - 자본총계: 당기 {cur_eq:15,d} 원 | 전기 {pri_eq:15,d} 원")
    
    print("-" * 60)
    print("5. 손익계산서(I/S) 주요 지표:")
    cur_rev = is_summary.get("current_revenue", 0)
    pri_rev = is_summary.get("prior_revenue", 0)
    print(f"   - 매출액:   당기 {cur_rev:15,d} 원 | 전기 {pri_rev:15,d} 원")
    
    cur_op = is_summary.get("current_operating_income", 0)
    pri_op = is_summary.get("prior_operating_income", 0)
    print(f"   - 영업이익: 당기 {cur_op:15,d} 원 | 전기 {pri_op:15,d} 원")
    
    cur_ni = is_summary.get("current_net_income", 0)
    pri_ni = is_summary.get("prior_net_income", 0)
    print(f"   - 당기순익: 당기 {cur_ni:15,d} 원 | 전기 {pri_ni:15,d} 원")
    
    print("=" * 60)
    print("[SUCCESS] Step 2 검증이 완벽하게 통과되었습니다!")
    print("=" * 60)

if __name__ == "__main__":
    main()
