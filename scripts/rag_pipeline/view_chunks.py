import os
import chromadb
from dotenv import load_dotenv

def view_recent_chunks(limit=5):
    # .env 파일에서 환경변수 로드
    load_dotenv()
    host = os.environ.get("CHROMA_SERVER_HOST", "192.168.0.224")
    port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))

    try:
        # 우분투 서버 ChromaDB 연결
        client = chromadb.HttpClient(host=host, port=port)
        collection = client.get_collection("document_chunks")
        
        # 데이터 가져오기 (최근 limit 개수만큼)
        results = collection.peek(limit=limit)
        
        if not results['ids']:
            print("데이터베이스에 저장된 청크가 없습니다.")
            return

        print(f"=== 최근 저장된 {len(results['ids'])}개의 청크 미리보기 ===\n")
        
        for i in range(len(results['ids'])):
            print(f"[{i+1}] 문서 ID: {results['ids'][i]}")
            print(f"▶ 메타데이터: {results['metadatas'][i]}")
            
            # 본문 내용 (길이가 길 수 있으므로 500자까지만 출력)
            content = results['documents'][i]
            print("▶ 본문 내용:")
            print("-" * 50)
            print(content[:500] + ("..." if len(content) > 500 else ""))
            print("-" * 50)
            print("\n")
            
    except Exception as e:
        print(f"ChromaDB 연결 또는 조회 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    view_recent_chunks(limit=3)
