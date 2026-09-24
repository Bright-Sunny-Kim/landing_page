# -*- coding: utf-8 -*-
"""
회계기준서(Standards PDF) 전용 파서 및 표준 JSON 생성기
- 대상 경로: uploads/standards (K-IFRS, K-GAAP, SME-GAAP, SPC-GAAP, NPO-GAAP, K-GAAS)
- 출력 경로: data/json_rag/standards
"""

import os
import sys
import glob
import json
import logging
import re
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF

# 로깅 설정 (Backend Logging Rule 준수)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("StandardsParser")


# 문단/조 분할 정규식 패턴
GAAP_PATTERN = re.compile(
    r"^((?:제\s*\d+\s*조|(?:[1-9]|[1-3]\d)\.(?:[1-9]\d{0,2}|0[1-9]\d?)[A-Za-z]?(?=\s|$)).*?)$",
    re.MULTILINE
)
IFRS_PATTERN = re.compile(
    r"^((?:(?:한|IE|[A-Z])?\d{1,3}[A-Za-z]?\.?(?=\s|$)).*?)$",
    re.MULTILINE
)


def extract_pdf_pages_and_text(pdf_path: str) -> List[Dict[str, Any]]:
    """PDF 파일에서 페이지별 텍스트를 추출합니다."""
    pages = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_idx, page in enumerate(doc):
                text = page.get_text() or ""
                pages.append({
                    "page_number": page_idx + 1,
                    "text": text
                })
        return pages
    except Exception as e:
        logger.error("Error reading PDF with PyMuPDF: %s, Error: %s", pdf_path, e, exc_info=True)
        return []


def chunk_standards_text(pages: List[Dict[str, Any]], category: str, doc_title: str) -> List[Dict[str, Any]]:
    """페이지별 텍스트를 조합하여 조/문단 단위의 구조화된 청크 리스트로 분할합니다."""
    full_text_with_pages = []
    for p in pages:
        full_text_with_pages.append(f"\n[PAGE_{p['page_number']}]\n{p['text']}")
    
    full_text = "\n".join(full_text_with_pages)
    
    pattern = IFRS_PATTERN if "IFRS" in category.upper() else GAAP_PATTERN
    parts = pattern.split(full_text)
    
    chunks = []
    current_article = "서문/총칙"
    current_page = 1
    
    for part in parts:
        part_clean = part.strip()
        if not part_clean:
            continue
            
        # 페이지 번호 추적
        page_matches = re.findall(r"\[PAGE_(\d+)\]", part_clean)
        if page_matches:
            current_page = int(page_matches[-1])
            part_clean = re.sub(r"\[PAGE_\d+\]", "", part_clean).strip()

        if not part_clean:
            continue

        if pattern.match(part_clean):
            current_article = part_clean
        else:
            # 텍스트 청크 추가 (8000자 초과 시 서브 파트로 분할)
            max_chunk_size = 4000
            if len(part_clean) > max_chunk_size:
                for i in range(0, len(part_clean), max_chunk_size):
                    chunks.append({
                        "chunk_id": f"{len(chunks) + 1}",
                        "article_title": current_article,
                        "page_number": current_page,
                        "content": part_clean[i:i + max_chunk_size]
                    })
            else:
                chunks.append({
                    "chunk_id": f"{len(chunks) + 1}",
                    "article_title": current_article,
                    "page_number": current_page,
                    "content": part_clean
                })
                
    return chunks


def parse_standard_pdf(pdf_path: str, base_dir: str) -> Optional[Dict[str, Any]]:
    """단일 회계기준서 PDF를 파싱하여 표준 JSON 객체로 변환합니다."""
    filename = os.path.basename(pdf_path)
    rel_path = os.path.relpath(pdf_path, base_dir)
    category = rel_path.replace("\\", "/").split("/")[0]
    
    doc_title = os.path.splitext(filename)[0]
    logger.info("Parsing Standards PDF: [%s] %s", category, filename)
    
    pages = extract_pdf_pages_and_text(pdf_path)
    if not pages:
        logger.warning("Empty or unreadable PDF: %s", pdf_path)
        return None
        
    chunks = chunk_standards_text(pages, category, doc_title)
    
    result_data = {
        "metadata": {
            "document_id": doc_title,
            "filename": filename,
            "category": category,
            "file_type": "pdf",
            "total_pages": len(pages),
            "total_chunks": len(chunks)
        },
        "chunks": chunks
    }
    logger.info("Successfully parsed Standards PDF: %s (%d pages, %d chunks)",
                filename, len(pages), len(chunks))
    return result_data


def process_all_standards(src_dir: str, out_dir: str) -> Dict[str, int]:
    """전체 회계기준서 디렉토리를 순회하여 JSON 파일로 변환합니다."""
    logger.info("Starting standards PDF batch processing...")
    logger.info("Source Directory: %s", src_dir)
    logger.info("Output Directory: %s", out_dir)

    os.makedirs(out_dir, exist_ok=True)
    
    files = glob.glob(os.path.join(src_dir, "**", "*.pdf"), recursive=True)
    stats = {"total": 0, "success": 0, "failed": 0, "categories": {}}

    for fpath in files:
        stats["total"] += 1
        rel_fpath = os.path.relpath(fpath, src_dir)
        category = rel_fpath.replace("\\", "/").split("/")[0]
        stats["categories"][category] = stats["categories"].get(category, 0) + 1
        
        target_sub_dir = os.path.join(out_dir, category)
        os.makedirs(target_sub_dir, exist_ok=True)
        
        json_filename = os.path.splitext(os.path.basename(fpath))[0] + ".json"
        target_json_path = os.path.join(target_sub_dir, json_filename)

        parsed_data = parse_standard_pdf(fpath, src_dir)
        if parsed_data:
            try:
                with open(target_json_path, "w", encoding="utf-8") as jf:
                    json.dump(parsed_data, jf, ensure_ascii=False, indent=2)
                stats["success"] += 1
            except Exception as se:
                logger.error("Failed to write JSON file: %s, Error: %s", target_json_path, se, exc_info=True)
                stats["failed"] += 1
        else:
            stats["failed"] += 1

    logger.info("==================================================")
    logger.info("Standards Parsing Finished!")
    logger.info("Total Files Evaluated: %d", stats["total"])
    for cat, cnt in stats["categories"].items():
        logger.info("  - Category [%s]: %d files", cat, cnt)
    logger.info("Success: %d, Failed: %d", stats["success"], stats["failed"])
    logger.info("==================================================")
    return stats


if __name__ == "__main__":
    base_proj = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    source_standards_dir = os.path.join(base_proj, "uploads", "standards")
    output_rag_dir = os.path.join(base_proj, "data", "json_rag", "standards")
    
    process_all_standards(source_standards_dir, output_rag_dir)
