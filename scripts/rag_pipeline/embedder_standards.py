import os
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

class VectorEmbedder:
    def __init__(self):
        load_dotenv()
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Supabase 클라이언트 초기화
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if url and key:
            self.supabase: Client = create_client(url, key)
        else:
            self.supabase = None
            
        self.model_name = "text-embedding-3-large"

    def get_embedding(self, text: str) -> list:
        """텍스트를 벡터로 변환합니다."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.model_name,
                dimensions=1536
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[Embedder] 임베딩 오류: {e}")
            return []

    def embed_and_store_chunks(self, chunks: list):
        """청크 리스트를 받아 각각 임베딩하고 DB에 삽입합니다."""
        if not self.supabase:
            print("[Embedder] Supabase가 연결되지 않았습니다.")
            return

        for chunk in chunks:
            text = chunk.get("text")
            metadata = chunk.get("metadata", {})
            document_id = metadata.get("document_id", "unknown")
            article_name = metadata.get("article", "unknown")
            category = metadata.get("category", "분류없음") # 새로 추가된 카테고리 필드
            
            # 임베딩 생성
            embedding_vector = self.get_embedding(text)
            
            if not embedding_vector:
                continue
                
            data = {
                "document_id": document_id,
                "category": category, # DB에 카테고리 추가 삽입
                "article_name": article_name,
                "chunk_text": text,
                "embedding": embedding_vector
            }
            
            try:
                self.supabase.table("document_chunks").insert(data).execute()
                print(f"[Embedder] '{article_name}' 청크 적재 완료.")
            except Exception as e:
                print(f"[Embedder] DB 적재 오류: {e}")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # 환경변수 점검
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("SUPABASE_URL"):
        print("[에러] .env 파일에 OPENAI_API_KEY 또는 SUPABASE_URL이 설정되지 않아 테스트를 종료합니다.")
    else:
        print("[테스트] 임베딩 및 Supabase 적재 테스트를 시작합니다...")
        embedder = VectorEmbedder()
        
        # 앞 단계에서 쪼개진 텍스트라고 가정하고 샘플 청크 주입
        sample_chunks = [
            {
                "text": "재고자산은 취득원가로 평가한다. 다만, 순실현가능가치가 취득원가보다 하락한 경우에는 순실현가능가치로 평가한다.", 
                "metadata": {"document_id": "K-GAAP-Test-01", "article": "제10조"}
            }
        ]
        
        embedder.embed_and_store_chunks(sample_chunks)
        print("[테스트] 임베딩 테스트 스크립트 실행 완료.")
