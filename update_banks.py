import sys
import os
from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

if not url or not key:
    print("Supabase credentials not found.")
    sys.exit(1)

supabase = create_client(url, key)

online_banks = [
    "HSBC", "KEB하나은행", "하나은행", "SC제일은행", "경남은행", "광주은행", "국민은행", "기업은행", 
    "농협은행", "미즈호은행", "부산은행", "산업은행", "수협은행", "신한은행", "씨티은행", 
    "아이엠뱅크", "대구은행", "우리은행", "전북은행", "제이피모간체이스은행", 
    "제주은행", "중소벤처기업진흥공단", "카카오뱅크", "케이뱅크", "토스뱅크", "한국수출입은행",
    "KB증권", "NH투자증권", "SK증권", "교보증권", "대신증권", "메리츠증권", "미래에셋증권", 
    "삼성증권", "신한투자증권", "아이엠증권", "키움증권", "하나증권", "한국증권금융", 
    "한국투자증권", "한화투자증권", "현대차증권",
    "DB손해보험", "KB손해보험", "NH농협생명보험", "NH농협손해보험", "교보생명보험", 
    "롯데손해보험", "메리츠화재해상보험", "미래에셋생명", "삼성생명보험", "삼성화재해상보험", 
    "신한라이프생명보험", "에이아이지 손해보험", "한화생명보험", "한화손해보험", "현대해상화재보험", "흥국생명보험",
    "기술보증기금", "서울보증보험", "신용보증기금"
]

res = supabase.table('financial_institutions').select('*').execute()
banks = res.data

updated_online = 0
updated_paper = 0

for b in banks:
    name = b['institution_name']
    
    is_online = False
    for ob in online_banks:
        if ob in name or name in ob:
            is_online = True
            break
            
    new_type = 'online' if is_online else 'paper'
    
    if b['inquiry_type'] != new_type:
        supabase.table('financial_institutions').update({'inquiry_type': new_type}).eq('id', b['id']).execute()
        if new_type == 'online':
            updated_online += 1
        else:
            updated_paper += 1
        print(f"Updated {name} to {new_type}")

print(f"Done! Changed {updated_online} to online, {updated_paper} to paper.")
