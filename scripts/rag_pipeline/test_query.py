import os
from openai import OpenAI
import chromadb
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")))

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

host = os.environ.get("CHROMA_SERVER_HOST", "100.74.25.71")
port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "document_chunks")

question = "중대한 오류 과거의 재무제표 수정"

print(f"질문: {question}")
embed_response = openai_client.embeddings.create(
    input=question,
    model="text-embedding-3-large",
    dimensions=1536
)
query_embedding = embed_response.data[0].embedding

chroma_client = chromadb.HttpClient(host=host, port=port)
collection = chroma_client.get_collection(name=collection_name)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=10
)

if results and results['ids'] and len(results['ids'][0]) > 0:
    for i in range(len(results['ids'][0])):
        dist = results['distances'][0][i]
        sim = 1.0 - dist
        doc_name = results['metadatas'][0][i].get("document_name", "N/A")
        print(f"순위 {i+1} | Distance: {dist:.4f} | Sim: {sim:.4f} | 문서: {doc_name}")
else:
    print("결과 없음")
