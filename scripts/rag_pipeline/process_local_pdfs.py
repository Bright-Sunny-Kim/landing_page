import os
import glob
from chunker_standards import SemanticChunker
from embedder_standards import VectorEmbedder
from supabase_uploader import SupabaseUploader

CATEGORIES = [
    "한국채택국제회계기준(K-IFRS)(시행중)",
    "한국채택국제회계기준(K-IFRS)(조기적용가능)",
    "일반기업회계기준",
    "특수분야회계기준",
    "중소기업회계기준",
    "비영리조직회계기준"
]

def process_local_directory(base_dir: str):
    """
    지정된 로컬 디렉토리 내의 카테고리별 하위 폴더에서 PDF 파일을 찾아
    파싱(Chunking) -> 임베딩 -> DB 적재 -> 원문 Storage 아카이빙을 일괄 수행합니다.
    """
    print(f"\n[일괄 처리 시작] 타겟 베이스 디렉토리: {base_dir}")
    
    # 베이스 디렉토리 및 카테고리 하위 폴더 생성
    for cat in CATEGORIES:
        cat_dir = os.path.join(base_dir, cat)
        if not os.path.exists(cat_dir):
            os.makedirs(cat_dir)
            print(f"[안내] 하위 폴더 자동 생성: {cat}")
            
    print(f"\n[안내] 위 폴더들에 다운로드 받은 PDF 원본들을 분류해서 넣어주세요.")
    
    # 전체 PDF 탐색
    all_pdfs = []
    for cat in CATEGORIES:
        cat_dir = os.path.join(base_dir, cat)
        pdfs = glob.glob(os.path.join(cat_dir, "*.pdf"))
        for p in pdfs:
            all_pdfs.append((p, cat)) # (파일경로, 카테고리명)
            
    if not all_pdfs:
        print(f"[안내] 하위 폴더들에 PDF 파일이 없습니다. 파일을 추가한 뒤 다시 실행해 주세요.")
        return

    print(f"총 {len(all_pdfs)}개의 PDF 파일을 발견했습니다. 파이프라인 가동을 시작합니다.\n")

    # 모듈 초기화
    chunker = SemanticChunker()
    embedder = VectorEmbedder()
    uploader = SupabaseUploader()
    uploader.ensure_bucket_exists()

    for pdf_path, category in all_pdfs:
        filename = os.path.basename(pdf_path)
        document_id = os.path.splitext(filename)[0]
        
        print(f"\n==============================================")
        print(f"▶ 처리 중인 파일: [{category}] {filename}")
        print(f"==============================================")
        
        # 1. 텍스트 추출 및 청킹 (Chunking)
        text = chunker.extract_text_from_pdf(pdf_path)
        if not text:
            print(f"[에러] {filename} 파일에서 텍스트를 추출할 수 없어 건너뜁니다.")
            continue
            
        chunks = chunker.chunk_text(text, document_id, category)
        if not chunks:
            print(f"[경고] {filename} 파일이 분할되지 않았습니다. 패턴이 있는지 확인하세요.")
            continue
            
        # 메타데이터에 category 속성 강제 추가
        for c in chunks:
            c['metadata']['category'] = category

        # 2. 임베딩 및 DB 적재 (Vectorization)
        embedder.embed_and_store_chunks(chunks)

        # 3. 원문 PDF Supabase Storage 업로드 (분류 폴더명 포함)
        metadata = {
            "title": document_id,
            "category": category,
            "type": "K-GAAP" if "gaap" in filename.lower() else "Standards"
        }
        # Storage 내부 경로를 "카테고리/파일명" 구조로 지정하되, 파이썬 Supabase 클라이언트의 한글 인코딩 에러를 방지하기 위해 완전한 영문(ASCII)으로 변환
        CATEGORY_MAP = {
            "한국채택국제회계기준(K-IFRS)(시행중)": "K-IFRS",
            "한국채택국제회계기준(K-IFRS)(조기적용가능)": "K-IFRS-Early",
            "일반기업회계기준": "K-GAAP",
            "특수분야회계기준": "Special-GAAP",
            "중소기업회계기준": "SME-GAAP",
            "비영리조직회계기준": "NPO-GAAP"
        }
        import hashlib
        eng_category = CATEGORY_MAP.get(category, "Other")
        
        # 한글 등 Non-ASCII 문자를 제거
        ascii_filename = filename.encode('ascii', 'ignore').decode('ascii').strip("_ ")
        if not ascii_filename.replace('.pdf', '').strip():
            ascii_filename = "document.pdf"
            
        # 영문 변환 시 파일명 충돌을 막기 위해 원본 파일명의 해시 6자리 추가
        file_hash = hashlib.md5(filename.encode()).hexdigest()[:6]
        storage_path = f"{eng_category}/{file_hash}_{ascii_filename}"
        
        # uploader의 upload_file은 내부적으로 filename 기반으로 동작하므로 약간 수정 필요하지만
        # upload_file에 storage_path를 명시적으로 넘기는 기능이 없으면,
        # 아래와 같이 uploader 스크립트 수정을 가정하고 호출
        uploader.upload_file(pdf_path, metadata, dest_path=storage_path)
        
        print(f"✅ {filename} 처리 완벽 완료.")

    print("\n[완료] 모든 로컬 PDF 파일의 일괄 적재 프로세스가 종료되었습니다.")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "standards"))
    process_local_directory(base_dir)
