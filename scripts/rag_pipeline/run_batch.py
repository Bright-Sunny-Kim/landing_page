import os
import glob
import json
import hashlib
from datetime import datetime
from n8n_pdf_processor import N8nPDFProcessor

CATEGORIES = [
    "K-IFRS",
    "K-GAAP",
    "SPC-GAAP",
    "SME-GAAP",
    "NPO-GAAP",
    "K-GAAS"
]

TRACKER_FILE = os.path.join(os.path.dirname(__file__), "parse_tracker.json")
MAX_FILES_PER_RUN = 50  # 한 번 실행할 때 최대 처리할 파일 수 (필요시 조절 가능)

def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tracker(tracker_data):
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracker_data, f, ensure_ascii=False, indent=4)

def run_batch(base_dir: str):
    print(f"\n[RAG 배치 프로세서 시작] 탐색 폴더: {base_dir}")
    
    tracker = load_tracker()
    processor = N8nPDFProcessor()
    
    # 처리할 PDF 목록 수집
    unparsed_pdfs = []
    for cat in CATEGORIES:
        cat_dir = os.path.join(base_dir, cat)
        if not os.path.exists(cat_dir):
            continue
        
        pdfs = glob.glob(os.path.join(cat_dir, "*.pdf"))
        for p in pdfs:
            filename = os.path.basename(p)
            file_hash = hashlib.md5(filename.encode()).hexdigest()[:6]
            doc_id = f"{cat}_{file_hash}"
            
            # 이미 성공한 기록이 있다면 스킵 (skipped_limit은 다시 시도하도록 허용)
            status = tracker.get(doc_id, {}).get("status")
            if status == "success":
                continue
                
            unparsed_pdfs.append((p, cat, filename, doc_id))
            
    if not unparsed_pdfs:
        print("[완료] 모든 파일이 이미 성공적으로 RAG화 되어 있습니다.")
        return
        
    print(f"[대기 상태] 총 {len(unparsed_pdfs)}개의 문서가 파싱 대기 중입니다.")
    print(f" -> 이번 실행에서는 최대 {MAX_FILES_PER_RUN}개까지만 순차 처리합니다.\n")
    
    processed_count = 0
    for pdf_path, category, filename, doc_id in unparsed_pdfs:
        if processed_count >= MAX_FILES_PER_RUN:
            print(f"\n[안내] 설정된 1회 최대 처리 개수({MAX_FILES_PER_RUN}개)에 도달하여 배치를 일시 중단합니다.")
            break
            
        print(f"==================================================")
        print(f"[{processed_count+1}/{len(unparsed_pdfs)}] 파일 처리 중: [{category}] {filename}")
        
        try:
            # 통합 스크립트의 process_file 호출 (텍스트 여부 판별 -> 파싱 -> 청킹 -> 임베딩)
            processor.process_file(pdf_path, category)
            
            # 성공 시 Tracker 업데이트
            tracker[doc_id] = {
                "filename": filename,
                "category": category,
                "status": "success",
                "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_tracker(tracker)
            print(f" -> 성공적으로 적재 완료 (Tracker 기록됨)\n")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[오류] 파일 처리 실패: {error_msg}")
            
            # LlamaParse 한도 초과 에러를 감지하면 중단하지 않고 건너뛰기 처리
            if "LlamaParse" in error_msg:
                print("\n[⚠️ 한도 초과] LlamaParse API 한도가 초과되었습니다.")
                print(f"이 스캔본 문서({filename})는 스킵하고, 텍스트 문서(Marker 무료 파싱 대상) 처리를 위해 다음 파일로 넘어갑니다.")
                tracker[doc_id] = {
                    "filename": filename,
                    "category": category,
                    "status": "skipped_limit",
                    "error": error_msg,
                    "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_tracker(tracker)
                processed_count += 1
                continue
                
            # 일반 오류인 경우 실패 기록을 남기고 다음 파일로 넘어감
            tracker[doc_id] = {
                "filename": filename,
                "category": category,
                "status": "failed",
                "error": error_msg,
                "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_tracker(tracker)
            
        processed_count += 1

    print("\n[배치 실행 종료] 이번 턴의 RAG 변환 작업이 마무리되었습니다.")

if __name__ == "__main__":
    target_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "standards"))
    run_batch(target_directory)
