# -*- coding: utf-8 -*-
"""
우분투 홈 서버 MinIO 스토리지 일괄 업로더 스크립트
- 대상: data/json_rag/ 내 227개 JSON 파일
- 타겟 MinIO 버킷: audit-lakehouse (경로: standards/ 및 audit_procedure/)
"""

import os
import sys
import glob
import json
import logging
from typing import Dict, Any, List
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정 (Backend Logging Rule 준수)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MinIO_Uploader")


def get_minio_client():
    """MinIO S3 클라이언트를 초기화하여 반환합니다."""
    endpoint = os.getenv("MINIO_ENDPOINT", "http://100.74.25.71:9000").strip()
    access_key = os.getenv("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.getenv("MINIO_SECRET_KEY", "").strip()

    if not access_key or not secret_key:
        logger.error("MINIO_ACCESS_KEY or MINIO_SECRET_KEY is missing in .env")
        raise ValueError("MinIO credentials missing")

    logger.info("Connecting to MinIO S3 endpoint: %s", endpoint)
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1',
        config=Config(connect_timeout=5, read_timeout=15, retries={'max_attempts': 3})
    )
    return s3


def ensure_bucket(s3, bucket_name: str):
    """지정된 버킷이 존재하는지 확인하고, 없으면 생성합니다."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info("Bucket '%s' exists and accessible.", bucket_name)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ('404', 'NoSuchBucket'):
            logger.info("Bucket '%s' not found. Creating bucket...", bucket_name)
            s3.create_bucket(Bucket=bucket_name)
            logger.info("Bucket '%s' created successfully.", bucket_name)
        else:
            logger.error("Error checking bucket '%s': %s", bucket_name, e, exc_info=True)
            raise


def upload_directory_to_minio(s3, bucket_name: str, local_dir: str, s3_prefix: str) -> Dict[str, int]:
    """로컬 디렉토리의 모든 JSON 파일을 MinIO의 해당 prefix 경로에 업로드합니다."""
    logger.info("Uploading directory '%s' to MinIO 's3://%s/%s'...", local_dir, bucket_name, s3_prefix)
    
    files = glob.glob(os.path.join(local_dir, "**", "*.json"), recursive=True)
    stats = {"total": len(files), "uploaded": 0, "failed": 0, "total_bytes": 0}
    
    for idx, fpath in enumerate(files, 1):
        rel_path = os.path.relpath(fpath, local_dir).replace("\\", "/")
        s3_key = f"{s3_prefix}/{rel_path}".replace("//", "/")
        file_size = os.path.getsize(fpath)
        stats["total_bytes"] += file_size
        
        try:
            with open(fpath, "rb") as f:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=f,
                    ContentType="application/json; charset=utf-8"
                )
            stats["uploaded"] += 1
            if idx % 20 == 0 or idx == len(files):
                logger.info("Progress [%d/%d] Uploaded: %s (%d bytes)", idx, len(files), s3_key, file_size)
        except Exception as ue:
            logger.error("Failed to upload '%s' to 's3://%s/%s': %s", fpath, bucket_name, s3_key, ue, exc_info=True)
            stats["failed"] += 1

    return stats


def verify_uploaded_objects(s3, bucket_name: str, prefix: str) -> int:
    """MinIO에 실제로 적재된 오브젝트 개수를 조회하여 검증합니다."""
    count = 0
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.json'):
                count += 1
    return count


def run_upload_pipeline():
    """전체 MinIO 업로드 파이프라인 실행"""
    base_proj = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    json_rag_base = os.path.join(base_proj, "data", "json_rag")
    
    audit_local_dir = os.path.join(json_rag_base, "audit_procedure")
    standards_local_dir = os.path.join(json_rag_base, "standards")
    
    target_bucket = "audit-lakehouse"
    
    logger.info("====================================================================")
    logger.info(">>> [MinIO Upload Step 2] 우분투 서버 MinIO 데이터 적재 시작")
    logger.info("====================================================================")
    
    s3 = get_minio_client()
    ensure_bucket(s3, target_bucket)
    
    # 1. audit_procedure 업로드
    logger.info("--- [1/2] 감사조서(audit_procedure) JSON 업로드 시작 ---")
    audit_stats = upload_directory_to_minio(s3, target_bucket, audit_local_dir, "audit_procedure")
    
    # 2. standards 업로드
    logger.info("--- [2/2] 회계기준서(standards) JSON 업로드 시작 ---")
    standards_stats = upload_directory_to_minio(s3, target_bucket, standards_local_dir, "standards")
    
    # 3. MinIO 서버 상의 실제 오브젝트 개수 대조 검증
    logger.info("--- [3/3] MinIO 서버 상의 적재 결과 대조 검증 ---")
    minio_audit_count = verify_uploaded_objects(s3, target_bucket, "audit_procedure/")
    minio_standards_count = verify_uploaded_objects(s3, target_bucket, "standards/")
    
    logger.info("====================================================================")
    logger.info(">>> [MinIO 업로드 완료 요약 보고]")
    logger.info("  1. audit_procedure: 로컬 %d개 -> MinIO 업로드 %d개 (서버 총 개수: %d개, 용량: %.2f MB)",
                audit_stats["total"], audit_stats["uploaded"], minio_audit_count, audit_stats["total_bytes"] / (1024*1024))
    logger.info("  2. standards: 로컬 %d개 -> MinIO 업로드 %d개 (서버 총 개수: %d개, 용량: %.2f MB)",
                standards_stats["total"], standards_stats["uploaded"], minio_standards_count, standards_stats["total_bytes"] / (1024*1024))
    logger.info("  * 총 업로드 성공: %d / %d 파일 (실패: %d)",
                audit_stats["uploaded"] + standards_stats["uploaded"],
                audit_stats["total"] + standards_stats["total"],
                audit_stats["failed"] + standards_stats["failed"])
    logger.info("  * MinIO 버킷: %s", target_bucket)
    logger.info("====================================================================")
    
    return {
        "audit": audit_stats,
        "standards": standards_stats,
        "minio_audit_count": minio_audit_count,
        "minio_standards_count": minio_standards_count
    }


if __name__ == "__main__":
    run_upload_pipeline()
