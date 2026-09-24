# -*- coding: utf-8 -*-
"""
RAG 데이터셋 일괄 빌더 오케스트레이터
- 1) 감사조서 템플릿 (data/audit_templates/0_KGAAP_2023 -> data/json_rag/audit_procedure)
- 2) 회계기준서 (uploads/standards -> data/json_rag/standards)
"""

import os
import sys
import logging
from parse_audit_templates import process_all_audit_templates
from parse_standards_json import process_all_standards

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RAG_Builder")


def build_all():
    base_proj = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    audit_src = os.path.join(base_proj, "data", "audit_templates", "0_KGAAP_2023")
    audit_out = os.path.join(base_proj, "data", "json_rag", "audit_procedure")
    
    standards_src = os.path.join(base_proj, "uploads", "standards")
    standards_out = os.path.join(base_proj, "data", "json_rag", "standards")
    
    logger.info("====================================================================")
    logger.info(">>> [1/2] 감사조서 템플릿 (Audit Procedures) JSON 변환 시작...")
    logger.info("====================================================================")
    audit_stats = process_all_audit_templates(audit_src, audit_out)
    
    logger.info("====================================================================")
    logger.info(">>> [2/2] 회계기준서 (Accounting Standards) JSON 변환 시작...")
    logger.info("====================================================================")
    standards_stats = process_all_standards(standards_src, standards_out)
    
    logger.info("====================================================================")
    logger.info(">>> [전체 완료 보고] 로컬 RAG JSON 데이터셋 생성 요약")
    logger.info("  1. 감사조서(Audit Procedure): 총 %d개 처리 (성공: %d, 실패: %d)",
                audit_stats["total"], audit_stats["success"], audit_stats["failed"])
    logger.info("  2. 회계기준서(Standards): 총 %d개 처리 (성공: %d, 실패: %d)",
                standards_stats["total"], standards_stats["success"], standards_stats["failed"])
    logger.info("  저장 위치: %s", os.path.join(base_proj, "data", "json_rag"))
    logger.info("====================================================================")


if __name__ == "__main__":
    build_all()
