# -*- coding: utf-8 -*-
"""
스마트 하이브리드 RAG 검색 모듈 (core/rag_retriever.py)
- Render.com(클라우드) 및 우분투 홈 서버 환경 모두에서 동작
- 우분투 ChromaDB 원격 HTTP 서버 우선 조회 및 로컬 PersistentClient 자동 폴백
- 회계기준서(standards_chunks) + 감사조서 절차(audit_procedure_chunks) 듀얼 검색
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

# 로깅 설정 (Backend Logging Rule 준수)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RAG_Retriever")

# 환경변수 로드
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CORE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))


class AuditRAGRetriever:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dim = 1536
        
        self.chroma_client = None
        self.col_standards = None
        self.col_procedures = None
        
        self._init_chroma_connection()

    def _init_chroma_connection(self):
        """ChromaDB 연결 초기화: 1순위 원격 HTTP 서버, 2순위 /mnt/storage/chroma_db 직접 탐색, 3순위 로컬 data/chroma_db"""
        host = os.getenv("CHROMA_SERVER_HOST", "100.74.25.71").strip()
        port_str = os.getenv("CHROMA_SERVER_PORT", "8000").strip()
        port = int(port_str) if port_str.isdigit() else 8000
        
        # 1. 원격 우분투 서버 HTTP 연결 시도 (Render.com 및 외부 환경용)
        try:
            logger.info("Attempting connection to ChromaDB HTTP Server at %s:%d...", host, port)
            http_client = chromadb.HttpClient(host=host, port=port)
            http_client.heartbeat()
            self.chroma_client = http_client
            logger.info("Successfully connected to remote ChromaDB HTTP server at %s:%d", host, port)
        except Exception as http_err:
            logger.warning("Remote ChromaDB HTTP at %s:%d not reachable (%s). Checking persistent storage paths.", host, port, http_err)
            
            # 2. 우분투 서버 직접 실행 시: /mnt/storage/chroma_db 또는 지정된 환경변수 경로 우선 확인
            configured_path = os.getenv("CHROMA_PERSISTENT_PATH", "").strip()
            ubuntu_storage_path = "/mnt/storage/chroma_db"
            local_fallback_path = os.path.join(BASE_DIR, "data", "chroma_db")
            
            chosen_path = local_fallback_path
            if configured_path and os.path.exists(configured_path):
                chosen_path = configured_path
            elif os.path.exists(ubuntu_storage_path):
                chosen_path = ubuntu_storage_path
                
            os.makedirs(chosen_path, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=chosen_path)
            logger.info("Using Persistent ChromaDB storage at '%s'", chosen_path)

        # 컬렉션 핸들러 획득
        try:
            self.col_standards = self.chroma_client.get_collection(name="standards_chunks")
            logger.info("Loaded collection 'standards_chunks' (count: %d)", self.col_standards.count())
        except Exception as e:
            logger.warning("Could not load 'standards_chunks': %s", e)
            self.col_standards = None

        try:
            self.col_procedures = self.chroma_client.get_collection(name="audit_procedure_chunks")
            logger.info("Loaded collection 'audit_procedure_chunks' (count: %d)", self.col_procedures.count())
        except Exception as e:
            logger.warning("Could not load 'audit_procedure_chunks': %s", e)
            self.col_procedures = None

    def get_query_embedding(self, query: str) -> List[float]:
        """사용자 질문 텍스트를 1536차원 벡터로 변환"""
        if not self.openai_client:
            logger.error("OpenAI client not initialized (OPENAI_API_KEY missing)")
            return []
        try:
            t0 = time.time()
            resp = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model,
                dimensions=self.embedding_dim
            )
            elapsed = time.time() - t0
            logger.debug("Generated query embedding in %.3f sec", elapsed)
            return resp.data[0].embedding
        except Exception as e:
            logger.error("Error generating query embedding: %s", e, exc_info=True)
            return []

    def retrieve(self, query: str, top_k_std: int = 3, top_k_proc: int = 3) -> Dict[str, Any]:
        """
        회계기준서 및 감사절차 듀얼 검색 수행
        반환값: {
            "standards": [...],
            "procedures": [...],
            "combined_context": "프롬프트 주입용 텍스트",
            "sources_summary": ["기준서 제1115호 문단 31", "C-0_매출채권 조서"]
        }
        """
        logger.info("[RAG_SEARCH] Searching for query: '%s' (std_k=%d, proc_k=%d)", query, top_k_std, top_k_proc)
        t_start = time.time()
        
        q_emb = self.get_query_embedding(query)
        if not q_emb:
            logger.warning("[RAG_SEARCH] Query embedding failed. Returning empty results.")
            return {"standards": [], "procedures": [], "combined_context": "", "sources_summary": []}

        standards_results = []
        procedures_results = []
        sources_summary = []

        # 1. 회계기준서 컬렉션 검색
        if self.col_standards:
            try:
                res_std = self.col_standards.query(query_embeddings=[q_emb], n_results=top_k_std)
                if res_std and res_std.get('ids') and len(res_std['ids'][0]) > 0:
                    for i in range(len(res_std['ids'][0])):
                        meta = res_std['metadatas'][0][i]
                        doc = res_std['documents'][0][i]
                        dist = res_std['distances'][0][i] if res_std.get('distances') else 0.5
                        sim = max(0.0, 1.0 - dist)
                        
                        doc_id = meta.get("document_id", "기준서")
                        cat = meta.get("category", "")
                        art = meta.get("article_title", "")
                        
                        src_label = f"[{cat}] {doc_id} - {art}"
                        sources_summary.append(src_label)
                        
                        standards_results.append({
                            "source_label": src_label,
                            "category": cat,
                            "document_id": doc_id,
                            "article_title": art,
                            "content": doc,
                            "similarity": round(sim, 4)
                        })
                logger.info("[RAG_SEARCH] Found %d standards chunks.", len(standards_results))
            except Exception as e:
                logger.error("[RAG_SEARCH] standards_chunks query failed: %s", e, exc_info=True)

        # 2. 감사조서/절차 컬렉션 검색
        if self.col_procedures:
            try:
                res_proc = self.col_procedures.query(query_embeddings=[q_emb], n_results=top_k_proc)
                if res_proc and res_proc.get('ids') and len(res_proc['ids'][0]) > 0:
                    for i in range(len(res_proc['ids'][0])):
                        meta = res_proc['metadatas'][0][i]
                        doc = res_proc['documents'][0][i]
                        dist = res_proc['distances'][0][i] if res_proc.get('distances') else 0.5
                        sim = max(0.0, 1.0 - dist)
                        
                        tmpl_id = meta.get("template_id", "감사조서")
                        sec = meta.get("section_name", "")
                        sub = meta.get("sub_category", "")
                        step = meta.get("step_no", "")
                        
                        src_label = f"[감사조서 {tmpl_id}] {sec} ({sub}) - 절차 {step}".strip(" - ")
                        sources_summary.append(src_label)
                        
                        procedures_results.append({
                            "source_label": src_label,
                            "template_id": tmpl_id,
                            "section_name": sec,
                            "sub_category": sub,
                            "step_no": step,
                            "content": doc,
                            "similarity": round(sim, 4)
                        })
                logger.info("[RAG_SEARCH] Found %d audit procedure chunks.", len(procedures_results))
            except Exception as e:
                logger.error("[RAG_SEARCH] audit_procedure_chunks query failed: %s", e, exc_info=True)

        # 3. LLM 프롬프트 주입용 복합 컨텍스트 조립
        context_blocks = []
        if standards_results:
            context_blocks.append("### 📚 [관련 회계/감사 기준서 조항]")
            for item in standards_results:
                context_blocks.append(f"**{item['source_label']}** (유사도: {item['similarity']})\n{item['content']}")

        if procedures_results:
            context_blocks.append("### 📋 [실제 감사조서 템플릿 및 수행 절차]")
            for item in procedures_results:
                context_blocks.append(f"**{item['source_label']}** (유사도: {item['similarity']})\n{item['content']}")

        combined_context = "\n\n".join(context_blocks)
        total_time = time.time() - t_start
        logger.info("[RAG_SEARCH] Retrieval completed in %.3f sec (Total chunks: %d)", total_time, len(standards_results) + len(procedures_results))

        return {
            "standards": standards_results,
            "procedures": procedures_results,
            "combined_context": combined_context,
            "sources_summary": sources_summary,
            "elapsed_seconds": round(total_time, 3)
        }


# 싱글톤 인스턴스
_retriever_instance = None

def get_rag_retriever() -> AuditRAGRetriever:
    """싱글톤 RAG 검색기 인스턴스를 반환합니다."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = AuditRAGRetriever()
    return _retriever_instance


def query_dual_rag(query: str, top_k_std: int = 3, top_k_proc: int = 3) -> Dict[str, Any]:
    """간편 호출용 듀얼 RAG 검색 함수"""
    retriever = get_rag_retriever()
    return retriever.retrieve(query, top_k_std=top_k_std, top_k_proc=top_k_proc)


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # 테스트 질의 수행
    test_q = "매출채권 대손충당금 설정 기준과 실증감사절차"
    print(f"테스트 질의: '{test_q}'")
    result = query_dual_rag(test_q)
    print(f"소요 시간: {result['elapsed_seconds']}초")
    print("\n[출처 요약]:")
    for s in result["sources_summary"]:
        print(" -", s)
    print("\n[프롬프트 주입용 컨텍스트 미리보기]:")
    print(result["combined_context"][:500], "...")
