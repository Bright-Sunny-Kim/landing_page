import re
import fitz  # PyMuPDF

class SemanticChunker:
    def __init__(self):
        # 기준서 패턴: 제1조, 제1장, 1.1, 1.2 등
        # 기존 ^((?:제\s*\d+\s*조|\d+\.\d+).*?)$ 에서 날짜, 소수점 오인식 방지를 위해 조건 강화
        # 1~39장 번호, 1~999 문단 번호 (00 등 제외), 후속 문자가 공백이나 줄바꿈일 때만 매칭
        self.article_pattern = re.compile(r"^((?:제\s*\d+\s*조|(?:[1-9]|[1-3]\d)\.(?:[1-9]\d{0,2}|0[1-9]\d?)[A-Za-z]?(?=\s|$)).*?)$", re.MULTILINE)
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PyMuPDF를 사용하여 PDF에서 텍스트를 추출합니다."""
        text = ""
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
            return text
        except Exception as e:
            print(f"[Chunker] PDF 파싱 오류 ({pdf_path}): {e}")
            return ""

    def chunk_text(self, text: str, document_id: str) -> list:
        """
        '조' 단위 등 시맨틱한 기준으로 텍스트를 나눕니다.
        간단한 예시로 정규식을 활용해 '제 N 조' 단위로 자릅니다.
        """
        chunks = []
        
        # '제X조' 기준으로 텍스트 분할
        # re.split에서 캡처 그룹을 쓰면 분할 기준 문자열도 리스트에 포함됨
        parts = self.article_pattern.split(text)
        
        current_chunk = ""
        current_metadata = {"document_id": document_id, "article": "서문/총칙"}
        
        def add_chunk(text, meta):
            text = text.strip()
            if not text:
                return
            # OpenAI 임베딩 제한(8192 토큰)을 방지하기 위해 3000자 단위로 강제 분할
            max_len = 3000
            if len(text) > max_len:
                for i in range(0, len(text), max_len):
                    sub_meta = meta.copy()
                    sub_meta["article"] = f"{meta['article']}_파트{i//max_len + 1}"
                    chunks.append({
                        "text": text[i:i+max_len],
                        "metadata": sub_meta
                    })
            else:
                chunks.append({
                    "text": text,
                    "metadata": meta.copy()
                })

        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if self.article_pattern.match(part):
                # 이전 청크 저장
                add_chunk(current_chunk, current_metadata)
                
                # 새로운 조 시작
                current_chunk = part + "\n"
                current_metadata["article"] = part
            else:
                # 조 제목이 아닌 내용은 현재 청크에 병합
                current_chunk += part + "\n"
                
        # 마지막 청크 저장
        add_chunk(current_chunk, current_metadata)
            
        print(f"[Chunker] '{document_id}' 문서를 {len(chunks)}개의 청크로 분할 완료.")
        return chunks

if __name__ == "__main__":
    import os
    import tempfile
    
    chunker = SemanticChunker()
    
    # 이전 단계(Scraper)에서 다운로드한 파일 경로 동적 생성
    test_pdf_path = os.path.join(tempfile.gettempdir(), "audit_standards", "K-GAAP_KGAAPSampleTest.pdf")
    
    if os.path.exists(test_pdf_path):
        print(f"[테스트] PDF 파싱 시작: {test_pdf_path}")
        test_text = chunker.extract_text_from_pdf(test_pdf_path)
        
        # 텍스트가 정상적으로 추출되었는지 확인
        if test_text:
            chunks = chunker.chunk_text(test_text, "K-GAAP-Test-01")
            print(f"[테스트] 총 청크 수: {len(chunks)}")
            if chunks:
                print("\n[테스트] 첫 번째 청크 내용 미리보기:")
                print(chunks[0]['text'][:200].encode('cp949', 'replace').decode('cp949') + "...\n")
        else:
            print("[에러] PDF에서 텍스트를 추출하지 못했습니다.")
    else:
        print(f"[에러] 다운로드된 PDF 파일을 찾을 수 없습니다: {test_pdf_path}")
        print("먼저 scraper_standards.py를 실행하여 파일을 준비해 주세요.")
