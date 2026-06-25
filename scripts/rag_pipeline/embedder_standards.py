import os
import uuid
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

class VectorEmbedder:
    def __init__(self):
        load_dotenv()
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model_name = "text-embedding-3-large"
        
        # ChromaDB 클라이언트 연결 (Ubuntu 서버)
        host = os.environ.get("CHROMA_SERVER_HOST", "localhost")
        port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
        
        try:
            self.chroma_client = chromadb.HttpClient(host=host, port=port)
            # 컬렉션(테이블) 생성 또는 가져오기
            self.collection = self.chroma_client.get_or_create_collection(
                name="document_chunks",
                metadata={"hnsw:space": "cosine"} # 코사인 유사도 사용
            )
        except Exception as e:
            print(f"[오류] ChromaDB 서버({host}:{port})에 접속할 수 없습니다: {e}")
            self.collection = None

    def is_document_processed(self, document_id: str) -> bool:
        """주어진 document_id가 이미 DB에 존재하는지 확인하여 중복을 방지합니다."""
        if not self.collection: return False
        try:
            # document_id를 where 조건으로 검색
            results = self.collection.get(
                where={"document_id": document_id},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            print(f"[Embedder] 중복 확인 중 오류: {e}")
            return False

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
        if not self.collection:
            print("[Embedder] ChromaDB 컬렉션이 초기화되지 않아 적재를 중단합니다.")
            return

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for chunk in chunks:
            text = chunk.get("text")
            metadata = chunk.get("metadata", {})
            document_id = metadata.get("document_id", "unknown")
            article_name = metadata.get("article", "unknown")
            category = metadata.get("category", "분류없음")
            
            # 임베딩 생성
            embedding_vector = self.get_embedding(text)
            
            if not embedding_vector:
                continue
                
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)
            embeddings.append(embedding_vector)
            documents.append(text)
            metadatas.append({
                "document_id": document_id,
                "category": category,
                "article_name": article_name
            })
            
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
                print(f"[Embedder] {len(ids)}개의 청크를 ChromaDB에 적재 완료.")
            except Exception as e:
                print(f"[Embedder] DB 적재 오류: {e}")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # 환경변수 점검
    if not os.environ.get("OPENAI_API_KEY"):
        print("[에러] .env 파일에 OPENAI_API_KEY가 설정되지 않아 테스트를 종료합니다.")
    else:
        print("[테스트] 임베딩 및 ChromaDB 적재 테스트를 시작합니다...")
        embedder = VectorEmbedder()
        
        # 앞 단계에서 쪼개진 텍스트라고 가정하고 샘플 청크 주입
        sample_chunks = [
            {
                "text": "재고자산은 취득원가로 평가한다. 다만, 순실현가능가치가 취득원가보다 하락한 경우에는 순실현가능가치로 평가한다.", 
                "metadata": {"document_id": "K-GAAP-Test-01", "article": "제10조"}
            }
        ]
        
        # 중복 방지 로직 테스트
        if not embedder.is_document_processed("K-GAAP-Test-01"):
            embedder.embed_and_store_chunks(sample_chunks)
            print("[테스트] 임베딩 테스트 스크립트 실행 완료.")
        else:
            print("[테스트] 이미 처리된 문서입니다 (중복 처리 방지 정상 작동).")
