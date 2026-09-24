# -*- coding: utf-8 -*-
"""
우분투 ChromaDB 고속 벡터 인덱서 스크립트
- 컬렉션 ①: standards_chunks (회계기준서 조/문단 지식)
- 컬렉션 ②: audit_procedure_chunks (감사절차 및 조서 서식 지식)
- 임베딩 모델: OpenAI text-embedding-3-large (1536 차원)
"""

import os
import sys
import glob
import json
import logging
import uuid
import time
from typing import Dict, Any, List, Optional
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정 (Backend Logging Rule 준수)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Chroma_Indexer")


class ChromaRAGIndexer:
    def __init__(self, chroma_path: str = "data/chroma_db"):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment.")
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dim = 1536
        
        # ChromaDB 클라이언트 초기화 (HTTP 서버 연결 시도 후 실패 시 PersistentClient로 폴백)
        host = os.getenv("CHROMA_SERVER_HOST", "100.74.25.71")
        port = int(os.getenv("CHROMA_SERVER_PORT", "8000"))
        
        self.client = None
        try:
            logger.info("Attempting connection to ChromaDB HTTP Server (%s:%d)...", host, port)
            http_client = chromadb.HttpClient(host=host, port=port)
            # 연결 테스트를 위해 임의 호출
            http_client.heartbeat()
            self.client = http_client
            logger.info("Connected to remote ChromaDB HTTP Server at %s:%d", host, port)
        except Exception as e:
            logger.warning("Could not connect to ChromaDB HTTP Server (%s). Using local PersistentClient at '%s'.", e, chroma_path)
            os.makedirs(chroma_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=chroma_path)

        # 2개 독립 컬렉션 생성/가져오기 (Cosine 거리 공간 사용)
        self.col_standards = self.client.get_or_create_collection(
            name="standards_chunks",
            metadata={"hnsw:space": "cosine", "description": "Accounting Standards Chunks"}
        )
        self.col_procedures = self.client.get_or_create_collection(
            name="audit_procedure_chunks",
            metadata={"hnsw:space": "cosine", "description": "Audit Procedures and Working Paper Templates"}
        )
        logger.info("ChromaDB collections ready: 'standards_chunks' (count: %d), 'audit_procedure_chunks' (count: %d)",
                    self.col_standards.count(), self.col_procedures.count())

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """OpenAI text-embedding-3-large 모델을 사용하여 배치 텍스트 임베딩을 생성합니다."""
        if not texts:
            return []
        try:
            response = self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_model,
                dimensions=self.embedding_dim
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error("OpenAI Embedding API error: %s", e, exc_info=True)
            return []

    def index_standards(self, json_dir: str, batch_size: int = 50):
        """회계기준서 JSON 파일들을 읽어 ChromaDB standards_chunks 컬렉션에 색인합니다."""
        logger.info("--- Starting Standards Indexing from '%s' ---", json_dir)
        files = glob.glob(os.path.join(json_dir, "**", "*.json"), recursive=True)
        logger.info("Found %d standards JSON files.", len(files))

        total_chunks = 0
        batch_ids = []
        batch_texts = []
        batch_metadatas = []

        for f_idx, fpath in enumerate(files, 1):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as re:
                logger.error("Error reading JSON file %s: %s", fpath, re, exc_info=True)
                continue

            meta = data.get("metadata", {})
            doc_id = meta.get("document_id", "unknown")
            category = meta.get("category", "일반")
            chunks = data.get("chunks", [])

            for c in chunks:
                article = c.get("article_title", "서문/본문")
                page = c.get("page_number", 1)
                content = c.get("content", "").strip()
                if not content or len(content) < 5:
                    continue

                embed_text = f"[{category}] {doc_id} ({article})\n{content}"
                chunk_id = f"std_{doc_id}_{c.get('chunk_id', uuid.uuid4().hex[:8])}"

                batch_ids.append(chunk_id)
                batch_texts.append(embed_text)
                batch_metadatas.append({
                    "document_id": str(doc_id),
                    "category": str(category),
                    "article_title": str(article),
                    "page_number": int(page),
                    "source_type": "standards"
                })

                if len(batch_texts) >= batch_size:
                    embeddings = self.get_embeddings_batch(batch_texts)
                    if embeddings:
                        self.col_standards.upsert(
                            ids=batch_ids,
                            documents=batch_texts,
                            embeddings=embeddings,
                            metadatas=batch_metadatas
                        )
                        total_chunks += len(batch_ids)
                        logger.info("Indexed %d standards chunks (Files: %d/%d)...", total_chunks, f_idx, len(files))
                    batch_ids, batch_texts, batch_metadatas = [], [], []
                    time.sleep(0.1)

        # 잔여 배치 처리
        if batch_texts:
            embeddings = self.get_embeddings_batch(batch_texts)
            if embeddings:
                self.col_standards.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    embeddings=embeddings,
                    metadatas=batch_metadatas
                )
                total_chunks += len(batch_ids)

        logger.info("Standards Indexing Completed! Total indexed chunks in 'standards_chunks': %d", self.col_standards.count())

    def index_audit_procedures(self, json_dir: str, batch_size: int = 50):
        """감사조서 JSON 파일들을 읽어 ChromaDB audit_procedure_chunks 컬렉션에 색인합니다."""
        logger.info("--- Starting Audit Procedures Indexing from '%s' ---", json_dir)
        files = glob.glob(os.path.join(json_dir, "**", "*.json"), recursive=True)
        logger.info("Found %d audit procedure JSON files.", len(files))

        total_chunks = 0
        batch_ids = []
        batch_texts = []
        batch_metadatas = []

        for f_idx, fpath in enumerate(files, 1):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as re:
                logger.error("Error reading JSON file %s: %s", fpath, re, exc_info=True)
                continue

            meta = data.get("metadata", {})
            template_id = meta.get("template_id", "unknown")
            section_name = meta.get("section_name", "감사절차")
            sub_category = meta.get("sub_category", "")
            doc_code = meta.get("doc_code", "")
            general_instr = data.get("general_instructions", "")

            # 1. 엑셀 시트별 절차 및 마크다운 표 색인
            for sheet in data.get("sheets", []):
                sheet_name = sheet.get("sheet_name", "")
                procedures = sheet.get("procedures", [])
                table_md = sheet.get("table_markdown", "")
                sheet_instr = sheet.get("instructions", "")

                # 개별 절차 색인
                for p in procedures:
                    step_no = p.get("step_no", "")
                    cat = p.get("category", "")
                    p_text = p.get("procedure_text", "")
                    assertions = ", ".join(p.get("assertions", []))

                    embed_text = (
                        f"[{section_name}/{sub_category}] {template_id} ({sheet_name})\n"
                        f"절차: {step_no} {p_text}\n"
                        f"분류: {cat}\n"
                        f"경영진주장: {assertions or '해당없음'}\n"
                        f"업무지침: {sheet_instr or general_instr[:200]}"
                    )
                    chunk_id = f"proc_{template_id}_{sheet_name}_{uuid.uuid4().hex[:8]}"

                    batch_ids.append(chunk_id)
                    batch_texts.append(embed_text)
                    batch_metadatas.append({
                        "template_id": str(template_id),
                        "section_name": str(section_name),
                        "sub_category": str(sub_category),
                        "doc_code": str(doc_code),
                        "sheet_name": str(sheet_name),
                        "step_no": str(step_no),
                        "assertions": str(assertions),
                        "source_type": "audit_procedure"
                    })

                # 시트의 전체 마크다운 표도 독립 컨텍스트 청크로 추가 (서식 통검색용)
                if table_md and len(table_md) > 30:
                    table_embed_text = (
                        f"[{section_name}/{sub_category}] {template_id} - {sheet_name} 감사서식/표\n"
                        f"{table_md[:3000]}"
                    )
                    t_chunk_id = f"table_{template_id}_{sheet_name}_{uuid.uuid4().hex[:8]}"
                    batch_ids.append(t_chunk_id)
                    batch_texts.append(table_embed_text)
                    batch_metadatas.append({
                        "template_id": str(template_id),
                        "section_name": str(section_name),
                        "sub_category": str(sub_category),
                        "doc_code": str(doc_code),
                        "sheet_name": str(sheet_name),
                        "step_no": "TABLE",
                        "assertions": "",
                        "source_type": "audit_table"
                    })

                if len(batch_texts) >= batch_size:
                    embeddings = self.get_embeddings_batch(batch_texts)
                    if embeddings:
                        self.col_procedures.upsert(
                            ids=batch_ids,
                            documents=batch_texts,
                            embeddings=embeddings,
                            metadatas=batch_metadatas
                        )
                        total_chunks += len(batch_ids)
                        logger.info("Indexed %d audit procedure chunks (Files: %d/%d)...", total_chunks, f_idx, len(files))
                    batch_ids, batch_texts, batch_metadatas = [], [], []
                    time.sleep(0.1)

            # 2. 워드 문서 단락/표 색인
            for para in data.get("paragraphs", []):
                p_text = para.get("text", "").strip()
                if len(p_text) < 10:
                    continue
                heading = para.get("heading", "본문")
                embed_text = f"[{section_name}/{sub_category}] {template_id} ({heading})\n{p_text}"
                chunk_id = f"word_{template_id}_{uuid.uuid4().hex[:8]}"

                batch_ids.append(chunk_id)
                batch_texts.append(embed_text)
                batch_metadatas.append({
                    "template_id": str(template_id),
                    "section_name": str(section_name),
                    "sub_category": str(sub_category),
                    "doc_code": str(doc_code),
                    "sheet_name": "Word_Document",
                    "step_no": "",
                    "assertions": "",
                    "source_type": "audit_procedure_word"
                })

                if len(batch_texts) >= batch_size:
                    embeddings = self.get_embeddings_batch(batch_texts)
                    if embeddings:
                        self.col_procedures.upsert(
                            ids=batch_ids,
                            documents=batch_texts,
                            embeddings=embeddings,
                            metadatas=batch_metadatas
                        )
                        total_chunks += len(batch_ids)
                    batch_ids, batch_texts, batch_metadatas = [], [], []
                    time.sleep(0.1)

        if batch_texts:
            embeddings = self.get_embeddings_batch(batch_texts)
            if embeddings:
                self.col_procedures.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    embeddings=embeddings,
                    metadatas=batch_metadatas
                )
                total_chunks += len(batch_ids)

        logger.info("Audit Procedures Indexing Completed! Total indexed chunks in 'audit_procedure_chunks': %d", self.col_procedures.count())


def run_indexing():
    base_proj = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    json_base = os.path.join(base_proj, "data", "json_rag")
    
    indexer = ChromaRAGIndexer(chroma_path=os.path.join(base_proj, "data", "chroma_db"))
    
    # 1. standards 색인
    indexer.index_standards(os.path.join(json_base, "standards"), batch_size=80)
    
    # 2. audit_procedure 색인
    indexer.index_audit_procedures(os.path.join(json_base, "audit_procedure"), batch_size=80)
    
    logger.info("====================================================================")
    logger.info(">>> [ChromaDB Indexing Complete Summary]")
    logger.info("  1. standards_chunks 컬렉션 총 벡터 수: %d", indexer.col_standards.count())
    logger.info("  2. audit_procedure_chunks 컬렉션 총 벡터 수: %d", indexer.col_procedures.count())
    logger.info("====================================================================")


if __name__ == "__main__":
    run_indexing()
