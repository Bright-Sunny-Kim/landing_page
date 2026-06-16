import os
import sys
import argparse
import zipfile
import io
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import OpenDartReader
from supabase import create_client
from openai import OpenAI

# Load env
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
load_dotenv(os.path.join(project_root, '.env'))

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def get_openai_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)

def clean_html(xml_content):
    soup = BeautifulSoup(xml_content, "lxml")
    # Remove tables with purely numerical data if necessary, or just extract text
    text = soup.get_text(separator="\n", strip=True)
    return text

def chunk_text(text, chunk_size=1200, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def process_dart_documents(corp_name, bsns_year):
    supabase = get_supabase_client()
    openai_client = get_openai_client()
    api_key = os.getenv("DART_API_KEY")
    
    if not supabase or not openai_client or not api_key:
        print("Missing Supabase, OpenAI, or DART API configurations.")
        sys.exit(1)
        
    dart = OpenDartReader(api_key)
    corp_code = dart.find_corp_code(corp_name)
    if not corp_code:
        print(f"Corp code not found for {corp_name}.")
        return

    # 공시검색 API 호출 (감사보고서 A001)
    # 사업연도의 다음 연도에 주로 공시되므로 범위를 넓게 잡음
    bgn_de = f"{bsns_year}0101"
    end_de = f"{int(bsns_year)+1}1231"
    
    list_url = 'https://opendart.fss.or.kr/api/list.json'
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bgn_de': bgn_de,
        'end_de': end_de,
        'pblntf_detail_ty': 'A001', # 감사보고서
        'page_count': 10
    }
    
    res = requests.get(list_url, params=params)
    data = res.json()
    
    if data.get('status') != '000':
        print(f"List API Error: {data.get('message')}")
        return
        
    records = data.get('list', [])
    if not records:
        print("No audit reports found.")
        return

    print(f"Found {len(records)} audit report documents. Processing...")
    
    for rec in records:
        rcept_no = rec.get('rcept_no')
        print(f"Processing rcept_no: {rcept_no}")
        
        # Check if already processed
        existing = supabase.table('dart_report_chunks').select('id').eq('rcept_no', rcept_no).limit(1).execute()
        if existing.data:
            print(f"Already processed {rcept_no}. Skipping.")
            continue
            
        doc_url = 'https://opendart.fss.or.kr/api/document.xml'
        doc_res = requests.get(doc_url, params={'crtfc_key': api_key, 'rcept_no': rcept_no})
        
        if doc_res.status_code != 200:
            print(f"Failed to download document for {rcept_no}")
            continue
            
        try:
            with zipfile.ZipFile(io.BytesIO(doc_res.content)) as z:
                xml_files = [name for name in z.namelist() if name.endswith('.xml')]
                for xml_name in xml_files:
                    with z.open(xml_name) as f:
                        xml_content = f.read().decode('utf-8', errors='ignore')
                        clean_txt = clean_html(xml_content)
                        
                        if not clean_txt.strip():
                            continue
                            
                        chunks = chunk_text(clean_txt)
                        print(f"Extracted {len(chunks)} chunks from {xml_name}")
                        
                        for i, chunk in enumerate(chunks):
                            try:
                                emb_res = openai_client.embeddings.create(
                                    input=chunk,
                                    model="text-embedding-3-large",
                                    dimensions=1536
                                )
                                embedding = emb_res.data[0].embedding
                                
                                supabase.table('dart_report_chunks').insert({
                                    'corp_name': corp_name,
                                    'bsns_year': bsns_year,
                                    'rcept_no': rcept_no,
                                    'chunk_text': chunk,
                                    'embedding': embedding
                                }).execute()
                                
                            except Exception as em_err:
                                print(f"Error embedding chunk {i}: {em_err}")
                            
                            time.sleep(0.1) # rate limit 방지
        except zipfile.BadZipFile:
            print(f"Bad zip file for {rcept_no}")

    print("Finished processing.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse and Chunk DART Audit Reports")
    parser.add_argument('--corp', type=str, default='삼성전자')
    parser.add_argument('--year', type=str, default=str(datetime.now().year - 1))
    args = parser.parse_args()
    
    process_dart_documents(args.corp, args.year)
