import os
import json
import hashlib
import requests
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from llama_parse import LlamaParse
from embedder_standards import VectorEmbedder

load_dotenv()

class N8nPDFProcessor:
    def __init__(self):
        self.unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL", "http://localhost:8000/general/v0/general")
        self.marker_api_url = os.getenv("MARKER_API_URL", "http://localhost:8080/api/parse")
        self.llama_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self.embedder = VectorEmbedder()

    def check_pdf_routing(self, pdf_path: str) -> bool:
        """
        Unstructured API를 호출하여 텍스트 포함 여부 판별
        표(Table) 보존을 위해 고해상도(hi_res) 전략 사용
        반환값: True (텍스트 있음, Marker 라우팅), False (스캔본, LlamaParse 라우팅)
        PDF 파일의 텍스트 추출 가능 여부를 확인합니다.
        로컬 pdfplumber 라이브러리를 사용하여 빠르고 안정적으로 판별합니다.
        (True: 텍스트 추출 가능 -> Marker, False: 스캔본/이미지 -> LlamaParse)
        """
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                # 첫 3페이지까지만 확인하여 텍스트가 있는지 빠르게 검사
                num_pages_to_check = min(3, len(pdf.pages))
                text_content = ""
                for i in range(num_pages_to_check):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text:
                        text_content += text
                        
                # 추출된 텍스트가 50자 이상이면 일반 텍스트 문서로 간주
                if len(text_content.strip()) > 50:
                    return True
                else:
                    return False
        except Exception as e:
            print(f"[라우팅 오류] pdfplumber 검사 중 예외 발생: {e}")
            return False

    def parse_with_marker(self, pdf_path: str) -> str:
        """Marker 서버 API 호출 (텍스트 PDF용)"""
        print(f"[파싱] Marker 서버 API 호출 중... (무료)")
        try:
            with open(pdf_path, 'rb') as f:
                files = {"file": f}
                response = requests.post(self.marker_api_url, files=files)
                if response.status_code == 200:
                    return response.json().get("markdown", "")
                return ""
        except Exception as e:
            print(f"[오류] Marker API 예외 발생: {e}")
            return ""

    def parse_with_unstructured(self, pdf_path: str) -> str:
        """Unstructured API를 호출하여 파싱 (Marker 실패 시 백업용)"""
        print(f"[파싱] Unstructured API 호출 중... : {pdf_path}")
        with open(pdf_path, 'rb') as f:
            files = {"files": (os.path.basename(pdf_path), f, "application/pdf")}
            data = {
                "strategy": "hi_res",
                "pdf_infer_table_structure": "true"
            }
            try:
                response = requests.post(self.unstructured_api_url, files=files, data=data)
                if response.status_code == 200:
                    elements = response.json()
                    # 간단히 텍스트와 표를 마크다운 텍스트로 결합
                    markdown_text = ""
                    for el in elements:
                        if el.get("type") == "Table":
                            markdown_text += "\n\n" + el.get("metadata", {}).get("text_as_html", "") + "\n\n"
                        elif el.get("type") == "Title":
                            markdown_text += f"\n## {el.get('text', '')}\n"
                        else:
                            markdown_text += f"{el.get('text', '')}\n"
                    return markdown_text
                else:
                    print(f"[오류] Unstructured API 파싱 실패: {response.status_code}")
                    return ""
            except Exception as e:
                print(f"[오류] Unstructured API 파싱 예외 발생: {e}")
                return ""

    def parse_with_llama(self, pdf_path: str) -> str:
        """LlamaParse API 호출 (스캔본/이미지 PDF용)"""
        print(f"[파싱] LlamaParse API 호출 중...")
        parser = LlamaParse(
            api_key=self.llama_api_key,
            result_type="markdown",
            verbose=True
        )
        parsed_docs = parser.load_data(pdf_path)
        if not parsed_docs:
            raise Exception("LlamaParse에서 반환된 데이터가 없습니다.")
        return "\n\n".join([doc.text for doc in parsed_docs])

    def chunk_and_embed(self, markdown_text: str, filename: str, category: str):
        """마크다운 헤더 기반 청킹 및 오버랩, 컨텍스트 레이어링 적용 후 임베딩"""
        print(f"[청킹] Markdown Header 기반 분할 시작")
        
        # 1. 마크다운 헤더 분할
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        splits = md_splitter.split_text(markdown_text)

        # 2. 재분할 (오버랩)을 위한 Character Splitter
        # 짧은 것은 위로 병합하고, 긴 것은 10~20% 오버랩으로 자름
        char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200 # 약 10~15% 오버랩
        )

        chunks_to_embed = []
        file_hash = hashlib.md5(filename.encode()).hexdigest()[:6]
        doc_id = f"{category}_{file_hash}"
        doc_type = "K-GAAP" if "gaap" in filename.lower() else "Standards"

        temp_short_chunk = ""
        temp_metadata = {}

        for i, split in enumerate(splits):
            text = split.page_content.strip()
            if not text:
                continue

            headers = split.metadata
            # Context Layering: 하위 청크 상단에 상위 헤더 구조 텍스트 프리픽스 삽입
            hierarchy = " > ".join([v for k, v in headers.items()]) if headers else f"Section_{i}"
            prefix = f"[{hierarchy}]\n"

            # 짧은 구간 병합 예외 처리 (300자 미만)
            if len(text) < 300:
                temp_short_chunk += prefix + text + "\n\n"
                temp_metadata = headers
                continue
            else:
                if temp_short_chunk:
                    text = temp_short_chunk + prefix + text
                    temp_short_chunk = ""

            layered_text = prefix + text

            # 너무 긴 구간 오버랩 분할 (RecursiveCharacterTextSplitter)
            sub_chunks = char_splitter.split_text(layered_text)

            for idx, sub_txt in enumerate(sub_chunks):
                # 메타데이터 적재
                meta = {
                    "document_id": doc_id,
                    "document_name": filename,
                    "category": category,
                    "standard_type": doc_type, # 회계/감사 기준구분
                    "article": hierarchy,
                    "page_number": idx + 1 # 페이지 번호 대체 개념
                }
                chunks_to_embed.append({
                    "text": sub_txt,
                    "metadata": meta
                })

        if temp_short_chunk:
            meta = {
                "document_id": doc_id,
                "document_name": filename,
                "category": category,
                "standard_type": doc_type,
                "article": "Merged_Short_Sections",
                "page_number": 1
            }
            chunks_to_embed.append({
                "text": temp_short_chunk,
                "metadata": meta
            })

        print(f"[저장] 총 {len(chunks_to_embed)}개의 Chunk ChromaDB 적재 시작")
        if chunks_to_embed:
            self.embedder.embed_and_store_chunks(chunks_to_embed)
        print("[완료] Vector DB 저장 완료")

    def process_file(self, pdf_path: str, category: str):
        filename = os.path.basename(pdf_path)
        print(f"[문서 처리 시작] {filename}")
        
        # 1. 텍스트 포함 여부 라우팅
        has_text = self.check_pdf_routing(pdf_path)
        
        # 2. 파싱 (마크다운 추출)
        parsed_text = ""
        if has_text:
            parsed_text = self.parse_with_marker(pdf_path)
            # 만약 Marker 서버가 꺼져있거나 에러가 났다면, Ubuntu에 띄워둔 Unstructured API로 대체!
            if not parsed_text:
                print("[경고] Marker 파싱 실패/미설정. Unstructured API로 대체 파싱을 시도합니다.")
                parsed_text = self.parse_with_unstructured(pdf_path)
        else:
            parsed_text = self.parse_with_llama(pdf_path)

        if not parsed_text.strip():
            raise Exception("파싱 결과가 비어있습니다 (파싱 서버 에러 또는 텍스트 없음).")

        self.chunk_and_embed(parsed_text, filename, category)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        pdf_file = sys.argv[1]
        cat = sys.argv[2]
        processor = N8nPDFProcessor()
        processor.process_file(pdf_file, cat)
    else:
        print("사용법: python n8n_pdf_processor.py <pdf_path> <category>")
