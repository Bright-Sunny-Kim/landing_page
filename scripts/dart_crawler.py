import os
import sys
import argparse
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

import OpenDartReader
from supabase import create_client, Client

# 스크립트가 위치한 디렉토리의 상위(프로젝트 루트)에서 .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
load_dotenv(os.path.join(project_root, '.env'))

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or url == "YOUR_SUPABASE_PROJECT_URL_HERE":
        print("ERROR: SUPABASE_URL or SUPABASE_KEY is missing or invalid.")
        return None
    return create_client(url, key)

def get_dart_client():
    api_key = os.getenv("DART_API_KEY")
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        print("ERROR: DART_API_KEY is missing in .env.")
        print("Please add DART_API_KEY=your_key_here to the .env file.")
        return None
    return OpenDartReader(api_key)

import requests

def crawl_audit_reports(dart, supabase, corp_name, bsns_year):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Crawling audit reports for {corp_name} in {bsns_year}...")
    try:
        # OpenDartReader를 이용해 corp_code (8자리 고유번호) 조회
        corp_code = dart.find_corp_code(corp_name)
        if not corp_code:
            print(f"Cannot find corp code for '{corp_name}'.")
            return

        print(f"Corp code for '{corp_name}' is {corp_code}. Fetching data from DART API...")
        
        # 회계감사인의 명칭 및 감사의견 API 호출
        url = 'https://opendart.fss.or.kr/api/accnutAdtorNmNdAdtOpinion.json'
        params = {
            'crtfc_key': dart.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': '11011' # 사업보고서 기준
        }
        
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if data.get('status') != '000':
            print(f"DART API Error: {data.get('message', 'Unknown error')} (status: {data.get('status')})")
            return
            
        records = data.get('list', [])
        if not records:
            print(f"No audit reports found for '{corp_name}' in {bsns_year}.")
            return

        print(f"Found {len(records)} records. Inserting into Supabase...")
        
        for row in records:
            record = {
                "rcept_no": row.get("rcept_no"),
                "corp_code": row.get("corp_code"),
                "corp_name": row.get("corp_name"),
                "bsns_year": bsns_year,
                "adtor_nm": row.get("adtor"),
                "adt_opinion": row.get("adt_opinion"),
                "adt_reprt_rcept_dt": row.get("rcept_no")[:8] if row.get("rcept_no") else None
            }
            
            try:
                # 중복 등록을 방지하기 위해 먼저 조회
                existing = supabase.table('dart_audit_reports') \
                    .select('id') \
                    .eq('rcept_no', record['rcept_no']) \
                    .eq('corp_code', record['corp_code']) \
                    .execute()
                
                if not existing.data:
                    supabase.table('dart_audit_reports').insert(record).execute()
                    print(f"Inserted: {record['corp_name']} ({record['bsns_year']}) - {record['adtor_nm']}")
                else:
                    print(f"Already exists (Skipped): {record['corp_name']} - {record['rcept_no']}")
                    
            except Exception as e:
                print(f"Failed to insert record for {record['corp_name']}: {e}")
                
    except Exception as e:
        print(f"Error crawling data for {corp_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl Open DART Audit Reports and store in Supabase.")
    parser.add_argument('--corp', type=str, default='삼성전자', help='Target company name or corp code (e.g., 삼성전자)')
    parser.add_argument('--year', type=str, default=str(datetime.now().year - 1), help='Business year (e.g., 2023)')
    parser.add_argument('--test', action='store_true', help='Run a test crawl')
    args = parser.parse_args()

    supabase = get_supabase_client()
    dart = get_dart_client()

    if not supabase or not dart:
        sys.exit(1)

    crawl_audit_reports(dart, supabase, args.corp, args.year)
    print("Process completed.")
