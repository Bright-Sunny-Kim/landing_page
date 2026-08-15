import os
import glob
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# LlamaParse & LangChain
from llama_parse import LlamaParse
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 기존 모듈 재사용
from embedder_standards import VectorEmbedder
from supabase_uploader import SupabaseUploader

load_dotenv()

CATEGORIES = [
    "K-IFRS",
    "K-GAAP",
    "SPC-GAAP",
    "SME-GAAP",
    "NPO-GAAP",
    "K-GAAS"
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKER_FILE = os.path.join(BASE_DIR, "data", "parse_tracker.json")
if not os.path.exists(TRACKER_FILE):
    TRACKER_FILE = os.path.join(BASE_DIR, "parse_tracker.json")
MAX_FILES_PER_RUN = 2 # 하루/1회 실행 시 파싱할 최대 파일 개수 (무료 티어 보호)

def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tracker(tracker_data):
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracker_data, f, ensure_ascii=False, indent=4)

def process_llama_parse(base_dir: str):
    print(f"\n[LlamaParse] 시작: {base_dir}")
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        print("[오류] .env 파일에 LLAMA_CLOUD_API_KEY가 없습니다!")
        return

    tracker = load_tracker()
    
    # 파싱할 PDF 목록 수집
    unparsed_pdfs = []
    for cat in CATEGORIES:
        cat_dir = os.path.join(base_dir, cat)
        if not os.path.exists(cat_dir):
            os.makedirs(cat_dir)
        
        pdfs = glob.glob(os.path.join(cat_dir, "*.pdf"))
        for p in pdfs:
            filename = os.path.basename(p)
            file_hash = hashlib.md5(filename.encode()).hexdigest()[:6]
            doc_id = f"{cat}_{file_hash}"
            
            # 이미 성공한 파일은 스킵
            if tracker.get(doc_id, {}).get("status") == "success":
                continue
            
            unparsed_pdfs.append((p, cat, filename, doc_id))

    if not unparsed_pdfs:
        print("[완료] 모든 파일의 파싱이 이미 완료되었습니다!")
        return
        
    print(f"[안내] 총 {len(unparsed_pdfs)}개의 파싱 대기 파일이 있습니다.")
    print(f"[안내] 이번 실행에서는 최대 {MAX_FILES_PER_RUN}개의 파일만 파싱합니다.")

    embedder = VectorEmbedder()
    uploader = SupabaseUploader()
    uploader.ensure_bucket_exists()
    
    # LlamaParse 초기화 (Markdown 결과물)
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True
    )
    
    # Markdown 헤더 기준 분할기 설정
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    processed_count = 0
    for pdf_path, category, filename, doc_id in unparsed_pdfs:
        if processed_count >= MAX_FILES_PER_RUN:
            break
            
        print(f"\n[{processed_count+1}/{MAX_FILES_PER_RUN}] 파싱 중: [{category}] {filename}")
        try:
            # 1. LlamaParse로 PDF 파싱 (API 호출)
            parsed_docs = parser.load_data(pdf_path)
            
            if not parsed_docs:
                raise Exception("LlamaParse에서 반환된 데이터가 없습니다. (API 한도 초과 또는 파싱 오류)")
                
            full_markdown = "\n\n".join([doc.text for doc in parsed_docs])
            
            # 2. Markdown 헤더 기준으로 청킹
            md_header_splits = markdown_splitter.split_text(full_markdown)
            
            print(f" -> LlamaParse 완료! 총 {len(md_header_splits)}개의 의미 단위 청크(Chunk) 생성됨.")
            
            # 3. ChromaDB에 적재하기 위한 데이터 조립
            chunks_to_embed = []
            for i, split in enumerate(md_header_splits):
                text_content = split.page_content
                if not text_content.strip(): continue
                
                # Markdown 헤더 정보들을 메타데이터로 합침
                headers = split.metadata
                article_info = " > ".join([v for k, v in headers.items()]) if headers else f"Chunk_{i}"
                
                meta = {
                    "document_id": doc_id,
                    "article": article_info,
                    "category": category,
                    "type": "K-GAAP" if "gaap" in filename.lower() else "Standards"
                }
                chunks_to_embed.append({
                    "text": text_content,
                    "metadata": meta
                })
            
            # 4. ChromaDB 삽입
            if chunks_to_embed:
                embedder.embed_and_store_chunks(chunks_to_embed)
                
            # 5. 원본 파일 Supabase Storage 백업
            ascii_filename = filename.encode('ascii', 'ignore').decode('ascii').strip("_ ")
            if not ascii_filename.replace('.pdf', '').strip():
                ascii_filename = "document.pdf"
            file_hash_short = hashlib.md5(filename.encode()).hexdigest()[:6]
            storage_path = f"{category}/{file_hash_short}_{ascii_filename}"
            
            supa_meta = {
                "title": doc_id,
                "category": category,
                "type": "K-GAAP" if "gaap" in filename.lower() else "Standards"
            }
            uploader.upload_file(pdf_path, supa_meta, dest_path=storage_path)
            
            # 6. Tracker 업데이트
            tracker[doc_id] = {
                "filename": filename,
                "category": category,
                "status": "success",
                "chunks_count": len(md_header_splits),
                "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_tracker(tracker)
            processed_count += 1
            print(f" -> 성공적으로 적재되었습니다!")
            
        except Exception as e:
            print(f"[오류] {filename} 처리 실패: {e}")
            tracker[doc_id] = {
                "filename": filename,
                "category": category,
                "status": "failed",
                "error": str(e),
                "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_tracker(tracker)
            processed_count += 1

    print(f"\n[완료] 이번 실행에서 {processed_count}개의 파일을 파싱했습니다.")
    print("나머지 파일을 파싱하시려면 내일 다시 실행하시거나 MAX_FILES_PER_RUN을 조정하세요.")

if __name__ == "__main__":
    target_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "standards"))
    process_llama_parse(target_directory)
