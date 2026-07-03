import os
import chromadb
from dotenv import load_dotenv

# .env 로드
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(env_path)

host = os.environ.get("CHROMA_SERVER_HOST", "100.74.25.71")
port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "document_chunks")

print(f"[{host}:{port}] ChromaDB 서버에 연결 중...")
try:
    client = chromadb.HttpClient(host=host, port=port)
    collection = client.get_collection(name=collection_name)
    
    # 전체 청크(데이터) 개수 확인
    count = collection.count()
    print(f"\n[OK] 컬렉션 '{collection_name}' 접속 성공!")
    print(f"[Info] 현재 적재된 총 청크(글 덩어리) 개수: {count}개\n")
    
    if count > 0:
        print("[데이터 샘플 2개 미리보기]")
        # 데이터 2개만 꺼내서 보기
        results = collection.peek(limit=2)
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        
        for i in range(len(documents)):
            print("=" * 60)
            print(f"문서명: {metadatas[i].get('document_name', 'N/A')}")
            print(f"카테고리: {metadatas[i].get('category', 'N/A')} | 조항: {metadatas[i].get('article', 'N/A')}")
            print(f"내용 (미리보기):\n{documents[i][:200]} ... (생략)")
    print("=" * 60)
except Exception as e:
    print(f"\n[Error] 에러 발생: {e}")
