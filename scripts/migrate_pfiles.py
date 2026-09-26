import os
import re
import logging
import boto3
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("PFileMigrator")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv(os.path.join(_ROOT, "config", ".env"))
load_dotenv(os.path.join(_ROOT, ".env"))

from core.extensions import supabase, s3_client

minio_endpoint = os.environ.get("MINIO_ENDPOINT", "http://100.74.25.71:9000").rstrip("/")
bucket_name = "company-uploads"

def migrate_pfiles(dry_run=False):
    """
    MinIO S3 및 Supabase DB의 기존 P-File들을 신규 누적 경로 구조({회사명}/P-File/{항목명}/...)로 자동 마이그레이션합니다.
    """
    logger.info("=== [P-File Migration Start] DryRun=%s ===", dry_run)
    
    migrated_s3_count = 0
    migrated_db_count = 0
    errors = []

    # 1. MinIO S3 오브젝트 탐색 및 마이그레이션
    if s3_client:
        try:
            logger.info("[S3:SCAN] Scanning bucket '%s' for P-Files...", bucket_name)
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)

            for page in pages:
                contents = page.get('Contents', [])
                for obj in contents:
                    key = obj.get('Key', '')
                    # 패턴: {company}/{year}/P-File/... 또는 {company}/P-File/{timestamp}_{field_name}_{filename}
                    # 변경 대상: {company}/[0-9]{4}/P-File/...
                    match_year_pfile = re.match(r'^([^/]+)/(\d{4})/P-File/(.+)$', key)
                    if match_year_pfile:
                        company = match_year_pfile.group(1)
                        year = match_year_pfile.group(2)
                        rest_filename = match_year_pfile.group(3)

                        # rest_filename 예: 1729384918234_pfile_01_정관.pdf
                        # pfile 항목명(pfile_01 등) 추출
                        field_match = re.search(r'(pfile_\d+)', rest_filename)
                        field_name = field_match.group(1) if field_match else "pfile_common"
                        
                        # 신규 키 생성: {company}/P-File/{field_name}/{clean_filename}
                        # 파일명에서 pfile_01_ 중복 제거 정리
                        clean_fn = re.sub(r'^(\d+)_pfile_\d+_', r'\1_', rest_filename)
                        new_key = f"{company}/P-File/{field_name}/{clean_fn}"

                        logger.info("[S3:MIGRATE_TARGET] OldKey: '%s' -> NewKey: '%s'", key, new_key)

                        if not dry_run:
                            try:
                                # Copy object
                                copy_source = {'Bucket': bucket_name, 'Key': key}
                                s3_client.copy_object(
                                    Bucket=bucket_name,
                                    CopySource=copy_source,
                                    Key=new_key
                                )
                                logger.info("[S3:COPY_SUCCESS] Copied to s3://%s/%s", bucket_name, new_key)
                                migrated_s3_count += 1
                            except Exception as ce:
                                logger.error("[S3:COPY_ERROR] Failed to copy '%s' to '%s': %s", key, new_key, ce, exc_info=True)
                                errors.append(f"S3 Copy Error ({key}): {ce}")
                        else:
                            migrated_s3_count += 1
        except Exception as se:
            logger.error("[S3:SCAN_ERROR] MinIO scan error: %s", se, exc_info=True)
            errors.append(f"S3 Scan Error: {se}")
    else:
        logger.warning("[S3:WARN] s3_client is not initialized")

    # 2. Supabase DB 레코드 조회 및 URL 갱신
    if supabase:
        try:
            logger.info("[DB:SCAN] Querying company_files from Supabase...")
            res = supabase.table('company_files').select('*').execute()
            rows = res.data or []
            logger.info("[DB:FETCHED] Found %d total file records in company_files", len(rows))

            for row in rows:
                row_id = row.get('id')
                file_url = row.get('file_url') or ''
                file_name = row.get('file_name') or ''
                help_text = row.get('help_text') or ''

                # P-File 판별
                is_pfile = ('P-File' in file_url) or ('pfile_' in file_url) or ('[PBC-P-' in file_name) or ('회사기본사항' in help_text) or ('영구문서' in help_text)

                if is_pfile and file_url:
                    # 구 경로 확인: /{year}/P-File/
                    match_url_year = re.search(r'/([^/]+)/(\d{4})/P-File/(.+)$', file_url)
                    if match_url_year:
                        company = match_url_year.group(1)
                        year = match_url_year.group(2)
                        rest_filename = match_url_year.group(3)

                        field_match = re.search(r'(pfile_\d+)', rest_filename)
                        field_name = field_match.group(1) if field_match else "pfile_common"
                        clean_fn = re.sub(r'^(\d+)_pfile_\d+_', r'\1_', rest_filename)

                        new_url = f"{minio_endpoint}/{bucket_name}/{company}/P-File/{field_name}/{clean_fn}"
                        
                        # help_text 보강
                        updated_help = help_text
                        if '[영구문서/P-File]' not in updated_help:
                            updated_help = f"[영구문서/P-File] {updated_help}"
                        # [2025년도] 등 연도 태그 제거
                        updated_help = re.sub(r'\[\d{4}년도\]\s*', '', updated_help)

                        logger.info("[DB:MIGRATE_ROW] ID=%s: OldURL='%s' -> NewURL='%s'", row_id, file_url, new_url)

                        if not dry_run:
                            try:
                                supabase.table('company_files').update({
                                    'file_url': new_url,
                                    'help_text': updated_help
                                }).eq('id', row_id).execute()
                                logger.info("[DB:UPDATE_SUCCESS] Updated row ID=%s", row_id)
                                migrated_db_count += 1
                            except Exception as de:
                                logger.error("[DB:UPDATE_ERROR] Failed to update row ID=%s: %s", row_id, de, exc_info=True)
                                errors.append(f"DB Update Error (ID={row_id}): {de}")
                        else:
                            migrated_db_count += 1
                    else:
                        # 이미 연도가 없는 경로인 경우 help_text 태그만 보강
                        if '[영구문서/P-File]' not in help_text:
                            updated_help = f"[영구문서/P-File] {re.sub(r'\[\d{4}년도\]\s*', '', help_text)}"
                            if not dry_run:
                                try:
                                    supabase.table('company_files').update({
                                        'help_text': updated_help
                                    }).eq('id', row_id).execute()
                                    logger.info("[DB:TAG_UPDATE_SUCCESS] Updated tag for row ID=%s", row_id)
                                    migrated_db_count += 1
                                except Exception as de:
                                    logger.error("[DB:TAG_UPDATE_ERROR] Failed to update tag ID=%s: %s", row_id, de)
        except Exception as dbe:
            logger.error("[DB:SCAN_ERROR] Supabase scan failed: %s", dbe, exc_info=True)
            errors.append(f"DB Scan Error: {dbe}")

    logger.info("=== [P-File Migration Finished] S3 Migrated: %d, DB Migrated: %d, Errors: %d ===",
                migrated_s3_count, migrated_db_count, len(errors))
    return {
        "migrated_s3_count": migrated_s3_count,
        "migrated_db_count": migrated_db_count,
        "errors": errors
    }

if __name__ == "__main__":
    result = migrate_pfiles(dry_run=False)
    print("Migration Result:", result)
