import datetime
import io
import json
import logging
import os
import re
import zipfile
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# 루트 및 config/.env 로드
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, "config", ".env"))
load_dotenv(os.path.join(_ROOT, ".env"))

logger = logging.getLogger(__name__)


class HybridStorageManager:
    """
    로컬 파일 보관함 및 사내 Ubuntu 서버(MinIO S3 / PostgreSQL / Network Mount)
    이중화 영속화를 관리하는 스토리지 관리자
    """

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.local_base_dir = os.path.join(
            self.project_root, "uploads", "작업완료_보관함"
        )
        try:
            os.makedirs(self.local_base_dir, exist_ok=True)
        except Exception as e:
            logger.warning("[STORAGE:INIT_WARNING] 기본 보관함 디렉토리 생성 실패: %s", e)

        # 사내 Ubuntu 서버 관련 환경설정 로드
        self.storage_mode = os.environ.get(
            "STORAGE_MODE", "hybrid"
        ).lower()  # 'local', 'ubuntu_server', 'hybrid'
        self.ubuntu_mount_path = os.environ.get("UBUNTU_ARCHIVE_PATH", "").strip()
        self.ubuntu_pg_host = os.environ.get("UBUNTU_PG_HOST", "").strip()
        self.ubuntu_pg_port = os.environ.get("UBUNTU_PG_PORT", "5432").strip()
        self.ubuntu_pg_db = os.environ.get("UBUNTU_PG_DB", "audit_lakehouse").strip()
        self.ubuntu_pg_user = os.environ.get("UBUNTU_PG_USER", "postgres").strip()
        self.ubuntu_pg_password = os.environ.get("UBUNTU_PG_PASSWORD", "").strip()

        # MinIO S3 환경설정 로드
        self.minio_endpoint = os.environ.get("MINIO_ENDPOINT", "https://s3.hyean-dskim.com").strip()
        self.minio_access_key = os.environ.get("MINIO_ACCESS_KEY", "").strip()
        self.minio_secret_key = os.environ.get("MINIO_SECRET_KEY", "").strip()
        self.minio_bucket = os.environ.get("MINIO_BUCKET_NAME", "audit-lakehouse").strip()

        self.s3_client = None
        self._init_s3_client()
        
        # 전역 extensions s3_client 폴백
        if not self.s3_client:
            try:
                from core.extensions import s3_client as ext_s3
                if ext_s3:
                    self.s3_client = ext_s3
                    logger.info("[STORAGE:EXT_S3_FALLBACK] Connected using core.extensions.s3_client")
            except Exception:
                pass

    def _init_s3_client(self):
        """MinIO S3 클라이언트를 초기화하고 필요시 기본 버킷을 생성합니다."""
        if self.minio_access_key and self.minio_secret_key:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=self.minio_endpoint,
                    aws_access_key_id=self.minio_access_key,
                    aws_secret_access_key=self.minio_secret_key,
                    region_name="us-east-1"
                )
                # 버킷 존재 여부 확인 및 자동 생성
                try:
                    self.s3_client.head_bucket(Bucket=self.minio_bucket)
                    logger.info("[STORAGE:MINIO_INIT] MinIO S3 버킷 연결 확인: %s (%s)", self.minio_bucket, self.minio_endpoint)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code")
                    if error_code in ["404", "NoSuchBucket"]:
                        self.s3_client.create_bucket(Bucket=self.minio_bucket)
                        logger.info("[STORAGE:MINIO_BUCKET_CREATED] MinIO S3 버킷 신규 생성: %s", self.minio_bucket)
                    else:
                        logger.warning("[STORAGE:MINIO_HEAD_WARNING] 버킷 상태 확인 중 경고: %s", e)
            except Exception as se:
                logger.error("[STORAGE:MINIO_INIT_ERROR] MinIO S3 클라이언트 초기화 실패: %s", se, exc_info=True)
                self.s3_client = None
        else:
            logger.info("[STORAGE:MINIO_NOTICE] MINIO credentials 미설정 (로컬 스토리지 모드 활성)")

    def get_storage_status(self):
        """현재 스토리지 모드 및 사내 Ubuntu 서버 / MinIO S3 연결 상태를 점검하여 반환합니다."""
        status = {
            "mode": self.storage_mode,
            "local_storage": {
                "active": True,
                "path": self.local_base_dir,
                "exists": os.path.exists(self.local_base_dir),
            },
            "ubuntu_server": {
                "configured": bool(self.ubuntu_mount_path or self.ubuntu_pg_host),
                "mount_path": self.ubuntu_mount_path or None,
                "pg_host": self.ubuntu_pg_host or None,
                "connected": False,
                "message": "로컬 보관함 활성 (Ubuntu 서버 환경설정 대기 중)",
            },
            "minio_s3": {
                "configured": bool(self.minio_access_key and self.minio_secret_key),
                "endpoint": self.minio_endpoint,
                "bucket": self.minio_bucket,
                "connected": False,
                "message": "MinIO S3 인증 정보 대기 중"
            }
        }

        # 1. Ubuntu 마운트 경로 연결 점검
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            status["ubuntu_server"]["connected"] = True
            status["ubuntu_server"][
                "message"
            ] = f"사내 Ubuntu 서버 마운트 경로 정상 연결 ({self.ubuntu_mount_path})"
        elif self.ubuntu_pg_host:
            status["ubuntu_server"]["connected"] = True
            status["ubuntu_server"][
                "message"
            ] = f"사내 Ubuntu PostgreSQL 서버 연동 모드 ({self.ubuntu_pg_host})"

        # 2. MinIO S3 버킷 통신 점검
        if self.s3_client:
            try:
                self.s3_client.head_bucket(Bucket=self.minio_bucket)
                status["minio_s3"]["connected"] = True
                status["minio_s3"]["message"] = f"MinIO S3 정상 연결 ({self.minio_endpoint} / {self.minio_bucket})"
            except Exception as me:
                status["minio_s3"]["message"] = f"MinIO S3 연결 실패: {me}"

        return status

    def save_analysis(self, company_name, fiscal_year, payload, raw_files=None):
        """
        분석 완료된 정규화 JSON, 감사조서(.md), 원본 엑셀/CSV(raw_files) 및 메타데이터를
        1) 사내 로컬 시점별(Timestamp) 타임시리즈 보관함
        2) 사내 Ubuntu 마운트 서버 (설정된 경우)
        3) 사내 Ubuntu MinIO S3 오브젝트 스토리지 (설정된 경우)
        에 안전하게 자동 영구 보관합니다.
        """
        fy = (
            int(fiscal_year)
            if fiscal_year and str(fiscal_year).isdigit()
            else 2025
        )
        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip() or "직접_분석_기업"
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        session_id = f"{fy}_{timestamp_str}"
        data_fn = f"{session_id}_data.json"
        report_fn = f"{session_id}_report.md"
        meta_fn = "metadata.json"

        # 6대 장부 수집 플래그 구성
        norm_bundle = payload.get("normalized_bundle") or {}
        raw_ds = norm_bundle.get("raw_datasets") or {}
        health_info = payload.get("ingestion_health") or {}

        metadata = {
            "company_name": company_name,
            "fiscal_year": fy,
            "session_id": session_id,
            "timestamp": timestamp_str,
            "saved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "integrity_score": payload.get("integrity_score", health_info.get("integrity_score", 100)),
            "raw_file_count": len(raw_files) if raw_files else 0,
            "raw_filenames": [f.get("filename", "") for f in raw_files] if raw_files else payload.get("analyzed_files", []),
            "ledgers_collected": {
                "balance_sheet": bool(raw_ds.get("balance_sheet")),
                "income_statement": bool(raw_ds.get("income_statement")),
                "trial_balance": bool(raw_ds.get("trial_balance")),
                "journal_entries": bool(raw_ds.get("journal_entries_sample")),
                "subledger": bool(raw_ds.get("subledger_sample")),
                "account_ledger": bool(raw_ds.get("account_ledger_sample") or raw_ds.get("account_ledger")),
            }
        }

        results = {
            "success": True,
            "filename": data_fn,
            "session_id": session_id,
            "saved_at": metadata["saved_at"],
            "locations": [],
            "metadata": metadata
        }

        payload_json_bytes = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        meta_json_bytes = json.dumps(metadata, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        report_md = payload.get("report_md", "")
        report_md_bytes = report_md.encode("utf-8") if report_md else b""

        # [1] 로컬 및 Ubuntu 마운트 디렉토리 저장
        target_base_dirs = [("local", self.local_base_dir)]
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            target_base_dirs.append(("ubuntu_server", self.ubuntu_mount_path))

        for target_type, base_path in target_base_dirs:
            try:
                company_root_dir = os.path.join(base_path, safe_company)
                session_dir = os.path.join(company_root_dir, str(fy), session_id)
                raw_files_dir = os.path.join(session_dir, "raw_files")
                os.makedirs(raw_files_dir, exist_ok=True)

                # data.json 및 metadata.json
                with open(os.path.join(session_dir, "data.json"), "wb") as jf:
                    jf.write(payload_json_bytes)

                with open(os.path.join(session_dir, meta_fn), "wb") as mf:
                    mf.write(meta_json_bytes)

                # report.md
                if report_md_bytes:
                    with open(os.path.join(session_dir, "report.md"), "wb") as rf:
                        rf.write(report_md_bytes)

                # 원본 파일
                if raw_files:
                    for rf_item in raw_files:
                        rf_name = rf_item.get("filename", "")
                        rf_content = rf_item.get("content", b"")
                        if rf_name and rf_content:
                            safe_rf_name = re.sub(r'[\\/:*?"<>|]', "_", os.path.basename(rf_name))
                            with open(os.path.join(raw_files_dir, safe_rf_name), "wb") as rbf:
                                rbf.write(rf_content)

                # 루트 백업 포인터
                with open(os.path.join(company_root_dir, data_fn), "wb") as cjf:
                    cjf.write(payload_json_bytes)

                if report_md_bytes:
                    with open(os.path.join(company_root_dir, report_fn), "wb") as crf:
                        crf.write(report_md_bytes)

                with open(os.path.join(company_root_dir, f"latest_{fy}_data.json"), "wb") as lf:
                    lf.write(payload_json_bytes)

                results["locations"].append({
                    "type": target_type,
                    "session_path": session_dir,
                    "status": "saved"
                })
                logger.info("[STORAGE:%s_SAVE] 시점별 영구 누적 저장 완료: %s/%s", target_type.upper(), safe_company, session_id)

            except Exception as le:
                logger.error("[STORAGE:%s_ERROR] 영구 보관함 저장 실패: %s", target_type.upper(), le, exc_info=True)
                results["locations"].append({"type": target_type, "status": "failed", "error": str(le)})

        # [2] MinIO S3 오브젝트 스토리지 업로드 (Lakehouse Bronze Layer)
        if self.s3_client:
            try:
                s3_prefix = f"bronze/{safe_company}/{fy}/{session_id}"
                
                # 1) data.json
                self.s3_client.put_object(
                    Bucket=self.minio_bucket,
                    Key=f"{s3_prefix}/data.json",
                    Body=payload_json_bytes,
                    ContentType="application/json; charset=utf-8"
                )

                # 2) metadata.json
                self.s3_client.put_object(
                    Bucket=self.minio_bucket,
                    Key=f"{s3_prefix}/metadata.json",
                    Body=meta_json_bytes,
                    ContentType="application/json; charset=utf-8"
                )

                # 3) report.md
                if report_md_bytes:
                    self.s3_client.put_object(
                        Bucket=self.minio_bucket,
                        Key=f"{s3_prefix}/report.md",
                        Body=report_md_bytes,
                        ContentType="text/markdown; charset=utf-8"
                    )

                # 4) raw_files (원본 파일들)
                if raw_files:
                    for rf_item in raw_files:
                        rf_name = rf_item.get("filename", "")
                        rf_content = rf_item.get("content", b"")
                        if rf_name and rf_content:
                            safe_rf_name = re.sub(r'[\\/:*?"<>|]', "_", os.path.basename(rf_name))
                            self.s3_client.put_object(
                                Bucket=self.minio_bucket,
                                Key=f"{s3_prefix}/raw_files/{safe_rf_name}",
                                Body=rf_content,
                                ContentType="application/octet-stream"
                            )

                # 5) 최신 포인터 (latest_{fy}_data.json)
                self.s3_client.put_object(
                    Bucket=self.minio_bucket,
                    Key=f"bronze/{safe_company}/latest_{fy}_data.json",
                    Body=payload_json_bytes,
                    ContentType="application/json; charset=utf-8"
                )

                results["locations"].append({
                    "type": "minio_s3",
                    "bucket": self.minio_bucket,
                    "s3_prefix": s3_prefix,
                    "status": "saved"
                })
                logger.info("[STORAGE:MINIO_SAVE] MinIO S3 자동 적재 성공: s3://%s/%s", self.minio_bucket, s3_prefix)

            except Exception as me:
                logger.error("[STORAGE:MINIO_ERROR] MinIO S3 적재 실패: %s", me, exc_info=True)
                results["locations"].append({"type": "minio_s3", "status": "failed", "error": str(me)})

        return results

        return results

    def list_upload_history(self, company_name=None):
        """
        전체 기업 또는 특정 기업의 시점별(Timestamp) 업로드 및 분석 이력 목록을 반환합니다.
        실시간 모니터링 관리 센터에서 표출됩니다.
        """
        history_list = []
        seen_sessions = set()

        candidate_base_dirs = [self.local_base_dir]
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            candidate_base_dirs.insert(0, self.ubuntu_mount_path)

        for base_dir in candidate_base_dirs:
            if not os.path.exists(base_dir):
                continue

            # 특정 회사 지정 또는 전체 회사 순회
            if company_name:
                safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
                company_dirs = [os.path.join(base_dir, safe_company)] if os.path.exists(os.path.join(base_dir, safe_company)) else []
            else:
                company_dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

            for c_dir in company_dirs:
                c_name = os.path.basename(c_dir)
                if not os.path.isdir(c_dir):
                    continue

                # 1. 연도별 하위 디렉토리 탐색 (예: 2025/2025_20260830_...)
                for sub_item in os.listdir(c_dir):
                    sub_path = os.path.join(c_dir, sub_item)
                    if os.path.isdir(sub_path) and sub_item.isdigit():
                        # sub_item은 연도(예: 2025)
                        fy_year = sub_item
                        for session_name in os.listdir(sub_path):
                            sess_dir = os.path.join(sub_path, session_name)
                            if os.path.isdir(sess_dir) and session_name not in seen_sessions:
                                seen_sessions.add(session_name)
                                meta_file = os.path.join(sess_dir, "metadata.json")
                                raw_dir = os.path.join(sess_dir, "raw_files")

                                if os.path.exists(meta_file):
                                    try:
                                        with open(meta_file, "r", encoding="utf-8") as mf:
                                            m_data = json.load(mf)
                                            m_data["has_raw_files"] = os.path.exists(raw_dir) and len(os.listdir(raw_dir)) > 0
                                            history_list.append(m_data)
                                            continue
                                    except Exception as me:
                                        logger.warning("[STORAGE:META_READ_WARNING] 메타데이터 로드 실패 (%s): %s", meta_file, me)

                                # metadata.json이 없는 경우 data.json 또는 디렉토리 타임스탬프로 폴백
                                ctime = datetime.datetime.fromtimestamp(os.path.getmtime(sess_dir)).strftime("%Y-%m-%d %H:%M:%S")
                                history_list.append({
                                    "company_name": c_name,
                                    "fiscal_year": int(fy_year) if fy_year.isdigit() else 2025,
                                    "session_id": session_name,
                                    "saved_at": ctime,
                                    "integrity_score": 100,
                                    "raw_file_count": len(os.listdir(raw_dir)) if os.path.exists(raw_dir) else 0,
                                    "raw_filenames": os.listdir(raw_dir) if os.path.exists(raw_dir) else [],
                                    "has_raw_files": os.path.exists(raw_dir) and len(os.listdir(raw_dir)) > 0,
                                    "ledgers_collected": {
                                        "balance_sheet": True,
                                        "income_statement": True,
                                        "trial_balance": True,
                                        "journal_entries": True,
                                        "subledger": True,
                                        "account_ledger": True
                                    }
                                })

                # 2. 회사 루트 바로 아래의 단일 파일형 보관본 탐색 (이전 버전 호환용)
                for fn in os.listdir(c_dir):
                    if fn.endswith("_data.json") and not fn.startswith("latest_"):
                        sess_key = fn.replace("_data.json", "")
                        if sess_key not in seen_sessions:
                            seen_sessions.add(sess_key)
                            fp = os.path.join(c_dir, fn)
                            ctime = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
                            parts = sess_key.split("_")
                            fy_val = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 2025
                            history_list.append({
                                "company_name": c_name,
                                "fiscal_year": fy_val,
                                "session_id": sess_key,
                                "saved_at": ctime,
                                "integrity_score": 100,
                                "raw_file_count": 0,
                                "raw_filenames": [],
                                "has_raw_files": False,
                                "ledgers_collected": {
                                    "balance_sheet": True,
                                    "income_statement": True,
                                    "trial_balance": True,
                                    "journal_entries": True,
                                    "subledger": True,
                                    "account_ledger": False
                                }
                            })

        # 3. MinIO S3의 Normalized Lakehouse 메타데이터 조회
        if self.s3_client:
            try:
                bucket_name = "company-uploads"
                prefix = f"{re.sub(r'[\\/:*?\"<>|]', '_', company_name).strip()}/" if company_name else ""
                s3_objs = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix).get("Contents", [])
                
                for obj in s3_objs:
                    key = obj["Key"]
                    if key.endswith("Normalized/metadata.json"):
                        try:
                            resp = self.s3_client.get_object(Bucket=bucket_name, Key=key)
                            meta_data = json.loads(resp["Body"].read().decode("utf-8"))
                            
                            c_name = meta_data.get("company_name") or key.split("/")[0]
                            fy_val = meta_data.get("fiscal_year") or 2025
                            sess_key = f"lakehouse_{fy_val}"
                            
                            if sess_key not in seen_sessions:
                                seen_sessions.add(sess_key)
                                af = meta_data.get("active_files") or meta_data.get("active_source_files", {})
                                raw_fns = [v.get("filename") for v in af.values() if isinstance(v, dict) and v.get("filename")]
                                col_ledgers = meta_data.get("collected_ledgers", {})
                                
                                history_list.append({
                                    "company_name": c_name,
                                    "fiscal_year": int(fy_val) if str(fy_val).isdigit() else 2025,
                                    "session_id": sess_key,
                                    "saved_at": meta_data.get("synced_at") or obj.get("LastModified", "").strftime("%Y-%m-%d %H:%M:%S") if hasattr(obj.get("LastModified", ""), "strftime") else str(obj.get("LastModified", "")),
                                    "integrity_score": 100 if meta_data.get("is_balanced") else 85,
                                    "raw_file_count": len(raw_fns),
                                    "raw_filenames": raw_fns,
                                    "has_raw_files": True,
                                    "ledgers_collected": {
                                        "balance_sheet": col_ledgers.get("balance_sheet", "bs" in af),
                                        "income_statement": col_ledgers.get("income_statement", "is" in af),
                                        "trial_balance": col_ledgers.get("trial_balance", "tb" in af),
                                        "journal_entries": col_ledgers.get("journal_entries", "je" in af),
                                        "subledger": col_ledgers.get("subledger", "sl" in af),
                                        "account_ledger": col_ledgers.get("account_ledger", "gl" in af)
                                    }
                                })
                        except Exception as s3_err:
                            logger.warning("[STORAGE:LIST_HISTORY_S3_ERR] %s: %s", key, s3_err)
            except Exception as e:
                logger.warning("[STORAGE:LIST_HISTORY_S3_WARN] Failed to list S3 lakehouse metadata: %s", e)

        # 최신 저장순으로 정렬
        return sorted(history_list, key=lambda x: x.get("saved_at", ""), reverse=True)

    def get_archive_raw_files_zip(self, company_name, session_id):
        """
        특정 기업의 특정 시점(session_id)에 업로드되었던 원본 엑셀/CSV 파일들을
        인메모리 ZIP 바이트 스트림으로 압축하여 반환합니다.
        """
        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
        safe_session = re.sub(r'[\\/:*?"<>|]', "_", session_id).strip()
        parts = safe_session.split("_")
        fy = parts[0] if len(parts) > 0 else "2025"

        candidate_raw_dirs = [
            os.path.join(self.local_base_dir, safe_company, str(fy), safe_session, "raw_files")
        ]
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            candidate_raw_dirs.insert(
                0, os.path.join(self.ubuntu_mount_path, safe_company, str(fy), safe_session, "raw_files")
            )

        target_dir = None
        for r_dir in candidate_raw_dirs:
            if os.path.exists(r_dir) and len(os.listdir(r_dir)) > 0:
                target_dir = r_dir
                break

        # MinIO S3에서 원본 파일 가져오기 시도 (로컬에 없는 경우)
        if not target_dir and self.s3_client:
            try:
                s3_raw_prefix = f"bronze/{safe_company}/{fy}/{safe_session}/raw_files/"
                resp = self.s3_client.list_objects_v2(Bucket=self.minio_bucket, Prefix=s3_raw_prefix)
                contents = resp.get("Contents", [])
                if contents:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for obj in contents:
                            obj_key = obj.get("Key", "")
                            fname = os.path.basename(obj_key)
                            if fname:
                                obj_resp = self.s3_client.get_object(Bucket=self.minio_bucket, Key=obj_key)
                                zf.writestr(fname, obj_resp["Body"].read())
                    zip_buffer.seek(0)
                    logger.info("[STORAGE:MINIO_ZIP_SUCCESS] MinIO S3에서 원본 파일 압축 다운로드 완료: %s / %s (파일 수: %d)", safe_company, safe_session, len(contents))
                    return zip_buffer
            except Exception as me:
                logger.warning("[STORAGE:MINIO_ZIP_WARNING] MinIO S3 원본 파일 압축 시도 중 경고: %s", me)

        if not target_dir:
            raise FileNotFoundError(f"'{company_name}' ({session_id})의 원본 업로드 파일을 찾을 수 없습니다.")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(target_dir):
                fpath = os.path.join(target_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, arcname=fname)

        zip_buffer.seek(0)
        logger.info("[STORAGE:ZIP_SUCCESS] 원본 파일 압축 완료: %s / %s (파일 수: %d)", safe_company, safe_session, len(os.listdir(target_dir)))
        return zip_buffer

    def list_datasets(self, company_name):
        """해당 기업의 과거 저장된 데이터셋 목록을 로컬 및 Ubuntu 서버에서 통합 조회합니다."""
        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
        datasets = []
        seen_filenames = set()

        candidate_dirs = [os.path.join(self.local_base_dir, safe_company)]
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            candidate_dirs.append(
                os.path.join(self.ubuntu_mount_path, safe_company)
            )

        for cdir in candidate_dirs:
            if not os.path.exists(cdir):
                continue
            for fn in sorted(os.listdir(cdir), reverse=True):
                if (
                    fn.endswith("_data.json")
                    and not fn.startswith("latest_")
                    and fn not in seen_filenames
                ):
                    seen_filenames.add(fn)
                    fp = os.path.join(cdir, fn)
                    ctime = datetime.datetime.fromtimestamp(
                        os.path.getmtime(fp)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    parts = fn.replace("_data.json", "").split("_")
                    fy = parts[0] if len(parts) > 0 else "2025"
                    datasets.append(
                        {
                            "filename": fn,
                            "fiscal_year": fy,
                            "saved_at": ctime,
                            "size_bytes": os.path.getsize(fp),
                            "source": "ubuntu_server"
                            if cdir.startswith(self.ubuntu_mount_path or "___")
                            else "local",
                        }
                    )

        return sorted(datasets, key=lambda x: x["saved_at"], reverse=True)

    def load_dataset(self, company_name, filename=None, session_id=None):
        """선택된 과거 데이터셋 JSON을 로컬, Ubuntu 서버 또는 MinIO S3에서 0.01초 만에 로드합니다."""
        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
        target_id = session_id or filename or "latest"

        candidate_paths = []

        # 1. 특정 session_id 또는 filename이 지정된 경우
        if target_id and target_id != "latest":
            safe_fn = os.path.basename(target_id)
            sess_str = safe_fn.replace("_data.json", "")
            parts = sess_str.split("_")
            fy = parts[0] if len(parts) > 0 else "2025"

            candidate_paths.extend([
                # 세션 폴더 하위 data.json
                os.path.join(self.local_base_dir, safe_company, str(fy), sess_str, "data.json"),
                # 회사 루트 하위 _data.json
                os.path.join(self.local_base_dir, safe_company, f"{sess_str}_data.json"),
                os.path.join(self.local_base_dir, safe_company, safe_fn),
            ])
            if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
                candidate_paths.insert(
                    0, os.path.join(self.ubuntu_mount_path, safe_company, str(fy), sess_str, "data.json")
                )
                candidate_paths.insert(
                    1, os.path.join(self.ubuntu_mount_path, safe_company, f"{sess_str}_data.json")
                )
        else:
            # 2. 최신 포인터 또는 가장 최근 연도 데이터 로드
            for default_fy in ["2025", "2024", "2026", "2023"]:
                candidate_paths.append(
                    os.path.join(self.local_base_dir, safe_company, f"latest_{default_fy}_data.json")
                )
                candidate_paths.append(
                    os.path.join(self.local_base_dir, safe_company, f"{default_fy}_data.json")
                )

        for fp in candidate_paths:
            if os.path.exists(fp) and os.path.isfile(fp):
                with open(fp, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                logger.info(
                    "[STORAGE:LOAD_SUCCESS] 로컬/마운트 데이터셋 로드 성공: %s (경로: %s)",
                    target_id,
                    fp,
                )
                return data

        # 3. MinIO S3 폴백 로딩 시도
        if self.s3_client:
            try:
                s3_keys_to_try = []
                if target_id and target_id != "latest":
                    safe_fn = os.path.basename(target_id)
                    sess_str = safe_fn.replace("_data.json", "")
                    parts = sess_str.split("_")
                    fy = parts[0] if len(parts) > 0 else "2025"
                    s3_keys_to_try.append(f"bronze/{safe_company}/{fy}/{sess_str}/data.json")
                else:
                    for default_fy in ["2025", "2024", "2026"]:
                        s3_keys_to_try.append(f"bronze/{safe_company}/latest_{default_fy}_data.json")

                for s3_key in s3_keys_to_try:
                    try:
                        resp = self.s3_client.get_object(Bucket=self.minio_bucket, Key=s3_key)
                        data = json.loads(resp["Body"].read().decode("utf-8"))
                        logger.info("[STORAGE:MINIO_LOAD_SUCCESS] MinIO S3 데이터셋 로드 성공: s3://%s/%s", self.minio_bucket, s3_key)
                        return data
                    except ClientError:
                        continue

                # 4. company-uploads 버킷의 Normalized/data.json 조회
                for fy_check in ["2025", "2024", "2026", "2023"]:
                    lake_key = f"{safe_company}/{fy_check}/Normalized/data.json"
                    try:
                        resp = self.s3_client.get_object(Bucket="company-uploads", Key=lake_key)
                        lake_d = json.loads(resp["Body"].read().decode("utf-8"))
                        logger.info("[STORAGE:LAKEHOUSE_LOAD_SUCCESS] MinIO company-uploads 데이터셋 로드 성공: %s", lake_key)
                        return {
                            "company_name": safe_company,
                            "fiscal_year": int(fy_check),
                            "session_id": f"lakehouse_{fy_check}",
                            "normalized_bundle": lake_d.get("statements", {}),
                            "summary": {"total_accounts": len(lake_d.get("statements", {}).get("balance_sheet", []))},
                            "raw_datasets": lake_d.get("statements", {}),
                            "data": lake_d
                        }
                    except ClientError:
                        continue
            except Exception as se:
                logger.warning("[STORAGE:MINIO_LOAD_WARNING] MinIO S3 로드 시도 중 에러: %s", se)

        raise FileNotFoundError(
            f"'{safe_company}' 기업의 '{target_id}' 데이터를 찾을 수 없습니다."
        )

    def load_normalized_lakehouse_data(self, company_name: str, fiscal_year: int = 2025):
        """
        사내 우분투 MinIO 서버의 {company_name}/{fiscal_year}/Normalized/data.json 을
        0.01초 만에 인메모리로 고속 로드하여 반환합니다.
        """
        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
        fy = int(fiscal_year) if fiscal_year and str(fiscal_year).isdigit() else 2025
        bucket_name = "company-uploads"
        target_key = f"{safe_company}/{fy}/Normalized/data.json"
        meta_key = f"{safe_company}/{fy}/Normalized/metadata.json"

        if not self.s3_client:
            logger.error("[STORAGE:LAKEHOUSE_ERROR] MinIO S3 client is not available")
            raise RuntimeError("MinIO S3 클라이언트가 초기화되지 않았습니다.")

        try:
            start_t = datetime.datetime.now()
            resp = self.s3_client.get_object(Bucket=bucket_name, Key=target_key)
            data_bytes = resp["Body"].read()
            data_json = json.loads(data_bytes.decode("utf-8"))
            elapsed_ms = (datetime.datetime.now() - start_t).total_seconds() * 1000

            logger.info("[STORAGE:LAKEHOUSE_SUCCESS] Normalized data loaded from s3://%s/%s in %.2f ms",
                        bucket_name, target_key, elapsed_ms)
            return {
                "success": True,
                "company_name": safe_company,
                "fiscal_year": fy,
                "elapsed_ms": round(elapsed_ms, 2),
                "data": data_json
            }
        except ClientError as ce:
            logger.warning("[STORAGE:LAKEHOUSE_NOT_FOUND] Normalized dataset not found: s3://%s/%s (%s)",
                           bucket_name, target_key, ce)
            return {
                "success": False,
                "company_name": safe_company,
                "fiscal_year": fy,
                "error": f"정규화된 재무 데이터셋(s3://{bucket_name}/{target_key})을 찾을 수 없습니다."
            }
        except Exception as e:
            logger.error("[STORAGE:LAKEHOUSE_ERROR] Failed to read normalized data: %s", e, exc_info=True)
            return {
                "success": False,
                "company_name": safe_company,
                "fiscal_year": fy,
                "error": f"데이터 로드 중 오류가 발생했습니다: {str(e)}"
            }

    def sync_normalized_lakehouse(self, company_name: str, fiscal_year: int = 2025):
        """
        사내 MinIO 서버의 {company_name}/{fiscal_year}/Temp/ 경로를 스캔하여
        중복 파일 중 가장 최신본을 자동 선별(Latest-Wins)하고,
        표준 data.json 및 metadata.json을 생성하여 Normalized/ 계층에 자동 동기화합니다.
        (부분 수집 Graceful Partial Ingestion 지원)
        """
        import numpy as np
        import math
        import pandas as pd
        from core.audit_engine import (
            parse_trial_balance_structured,
            parse_financial_statement,
            parse_tb_file,
            check_balance,
            reconcile_tb_to_statement
        )

        safe_company = re.sub(r'[\\/:*?"<>|]', "_", company_name).strip()
        fy = int(fiscal_year) if fiscal_year and str(fiscal_year).isdigit() else 2025
        bucket_name = "company-uploads"
        temp_prefix = f"{safe_company}/{fy}/Temp/"
        norm_prefix = f"{safe_company}/{fy}/Normalized"

        if not self.s3_client:
            logger.error("[STORAGE:SYNC_ERROR] MinIO S3 client is not available")
            return {"success": False, "error": "MinIO S3 클라이언트가 초기화되지 않았습니다."}

        try:
            logger.info("[STORAGE:SYNC_START] Syncing lakehouse for %s (FY %s)...", safe_company, fy)
            res = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=temp_prefix)
            contents = res.get("Contents", [])

            if not contents:
                logger.info("[STORAGE:SYNC_EMPTY] No source files found in s3://%s/%s", bucket_name, temp_prefix)
                return {
                    "success": True,
                    "company_name": safe_company,
                    "fiscal_year": fy,
                    "file_count": 0,
                    "message": "수집된 원본 파일이 없습니다."
                }

            # 1. 파일 유형별 분류 및 최신본 선별 (Latest-Wins Deduplication)
            categorized_files = {
                "tb": [],
                "bs": [],
                "is": [],
                "je": [],
                "gl": [],
                "sl": [],
                "other": []
            }

            for obj in contents:
                key = obj["Key"]
                filename = key.split("/")[-1]
                size = obj["Size"]
                last_modified = obj["LastModified"]
                
                # 파일명 앞자리 타임스탬프 추출 (없으면 LastModified 사용)
                ts_match = re.match(r"^(\d+)_", filename)
                ts_val = int(ts_match.group(1)) if ts_match else int(last_modified.timestamp() * 1000)

                item = {
                    "key": key,
                    "filename": filename,
                    "size_bytes": size,
                    "timestamp": ts_val,
                    "last_modified": last_modified.strftime("%Y-%m-%d %H:%M:%S")
                }

                if "_tb_" in filename or "시산표" in filename or "합잔" in filename:
                    categorized_files["tb"].append(item)
                elif "_bs_" in filename or "재무상태표" in filename or "재무" in filename:
                    categorized_files["bs"].append(item)
                elif "_is_" in filename or "손익계산서" in filename or "손익" in filename:
                    categorized_files["is"].append(item)
                elif "_je_" in filename or "분개장" in filename or "분개" in filename:
                    categorized_files["je"].append(item)
                elif "_gl_" in filename or "계정별원장" in filename or "총계정" in filename:
                    categorized_files["gl"].append(item)
                elif "_sl_" in filename or "거래처원장" in filename or "거래처" in filename:
                    categorized_files["sl"].append(item)
                else:
                    categorized_files["other"].append(item)

            # 각 유형별 최신 파일 1개만 선별
            selected_files = {}
            for cat, file_list in categorized_files.items():
                if file_list:
                    # 타임스탬프 기준 내림차순 정렬하여 가장 최신본 선택
                    file_list.sort(key=lambda x: x["timestamp"], reverse=True)
                    selected_files[cat] = file_list[0]

            logger.info("[STORAGE:SYNC_SELECTED] Selected %d latest files for normalization (Latest-Wins)", len(selected_files))

            # 2. 선별된 최신 엑셀 파일들 파싱 (부분 수집 지원)
            parsed_store = {}
            parsed_errors = {}

            # 2-1. 합계잔액시산표 (T/B)
            if "tb" in selected_files:
                tb_info = selected_files["tb"]
                try:
                    s3_obj = self.s3_client.get_object(Bucket=bucket_name, Key=tb_info["key"])
                    file_b = s3_obj["Body"].read()
                    try:
                        tb_df = parse_trial_balance_structured(file_b, tb_info["filename"])
                    except Exception:
                        # 3열 간이 시산표 또는 비정형 서식 폴백
                        raw_tb = parse_tb_file(file_b, tb_info["filename"])
                        tb_df = raw_tb.rename(columns={"Current": "NetBalance"})
                        if "IsSubtotal" not in tb_df.columns:
                            tb_df["IsSubtotal"] = False
                    parsed_store["tb"] = tb_df
                    logger.info("[STORAGE:SYNC_PARSED] T/B parsed successfully: %d accounts", len(tb_df))
                except Exception as tbe:
                    logger.warning("[STORAGE:SYNC_TB_ERR] Failed to parse T/B (%s): %s", tb_info["filename"], tbe)
                    parsed_errors["tb"] = str(tbe)

            # 2-2. 재무상태표 (B/S)
            if "bs" in selected_files:
                bs_info = selected_files["bs"]
                try:
                    s3_obj = self.s3_client.get_object(Bucket=bucket_name, Key=bs_info["key"])
                    bs_df = parse_financial_statement(s3_obj["Body"].read(), bs_info["filename"])
                    parsed_store["bs"] = bs_df
                    logger.info("[STORAGE:SYNC_PARSED] B/S parsed successfully: %d items", len(bs_df))
                except Exception as bse:
                    logger.warning("[STORAGE:SYNC_BS_ERR] Failed to parse B/S (%s): %s", bs_info["filename"], bse)
                    parsed_errors["bs"] = str(bse)

            # 2-3. 손익계산서 (I/S)
            if "is" in selected_files:
                is_info = selected_files["is"]
                try:
                    s3_obj = self.s3_client.get_object(Bucket=bucket_name, Key=is_info["key"])
                    is_df = parse_financial_statement(s3_obj["Body"].read(), is_info["filename"])
                    parsed_store["is"] = is_df
                    logger.info("[STORAGE:SYNC_PARSED] I/S parsed successfully: %d items", len(is_df))
                except Exception as ise:
                    logger.warning("[STORAGE:SYNC_IS_ERR] Failed to parse I/S (%s): %s", is_info["filename"], ise)
                    parsed_errors["is"] = str(ise)

            # 3. 대차평형 및 수치 대사 무결성 검증
            balance_check_res = check_balance(parsed_store.get("bs")) if "bs" in parsed_store else {}
            reconciliation_list = []
            if "tb" in parsed_store and "bs" in parsed_store:
                try:
                    reconciliation_list = reconcile_tb_to_statement(parsed_store["tb"], parsed_store["bs"])
                except Exception as rce:
                    logger.warning("[STORAGE:SYNC_RECON_ERR] Reconciliation failed: %s", rce)

            matched_recons = [r for r in reconciliation_list if r.get("Matched")]
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            def _clean_for_json(val):
                if isinstance(val, list):
                    return [_clean_for_json(x) for x in val]
                if isinstance(val, dict):
                    return {k: _clean_for_json(v) for k, v in val.items()}
                if isinstance(val, float):
                    if math.isnan(val) or math.isinf(val):
                        return None
                return val

            def _df_to_records(df):
                if df is None or not hasattr(df, "to_dict"):
                    return []
                records = df.replace({np.nan: None}).to_dict(orient="records")
                return _clean_for_json(records)

            # 4. 표준 data.json 생성
            standard_data_json = {
                "schema_version": "1.0-lakehouse",
                "company_name": safe_company,
                "fiscal_year": fy,
                "synced_at": now_str,
                "integrity": {
                    "is_balanced": balance_check_res.get("Balanced", False),
                    "balance_diff": balance_check_res.get("Diff", 0.0),
                    "reconciliation_total": len(reconciliation_list),
                    "reconciliation_matched": len(matched_recons),
                    "match_rate_pct": round(len(matched_recons) / len(reconciliation_list) * 100, 1) if reconciliation_list else 0.0
                },
                "statements": {
                    "trial_balance": _df_to_records(parsed_store.get("tb")),
                    "balance_sheet": _df_to_records(parsed_store.get("bs")),
                    "income_statement": _df_to_records(parsed_store.get("is"))
                },
                "reconciliation": _clean_for_json(reconciliation_list),
                "active_source_files": selected_files
            }

            # 5. metadata.json 생성
            metadata_json = {
                "company_name": safe_company,
                "fiscal_year": fy,
                "synced_at": now_str,
                "total_source_files": len(contents),
                "active_files": selected_files,
                "collected_ledgers": {
                    "trial_balance": "tb" in parsed_store,
                    "balance_sheet": "bs" in parsed_store,
                    "income_statement": "is" in parsed_store,
                    "journal_entries": "je" in selected_files,
                    "account_ledger": "gl" in selected_files,
                    "subledger": "sl" in selected_files
                },
                "account_counts": {
                    "trial_balance": len(parsed_store.get("tb", [])),
                    "balance_sheet": len(parsed_store.get("bs", [])),
                    "income_statement": len(parsed_store.get("is", []))
                },
                "is_balanced": balance_check_res.get("Balanced", False),
                "is_complete": bool("tb" in parsed_store and "bs" in parsed_store and "is" in parsed_store),
                "parse_errors": parsed_errors
            }

            # 6. MinIO Normalized/ 계층에 영구 적재
            data_bytes = json.dumps(standard_data_json, ensure_ascii=False, indent=2).encode("utf-8")
            meta_bytes = json.dumps(metadata_json, ensure_ascii=False, indent=2).encode("utf-8")

            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=f"{norm_prefix}/data.json",
                Body=data_bytes,
                ContentType="application/json; charset=utf-8"
            )
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=f"{norm_prefix}/metadata.json",
                Body=meta_bytes,
                ContentType="application/json; charset=utf-8"
            )

            logger.info("[STORAGE:SYNC_COMPLETE] Successfully synced Lakehouse Normalized layer for %s/%s", safe_company, fy)
            return {
                "success": True,
                "company_name": safe_company,
                "fiscal_year": fy,
                "data_size_bytes": len(data_bytes),
                "is_balanced": balance_check_res.get("Balanced", False),
                "is_complete": metadata_json["is_complete"],
                "active_files_count": len(selected_files),
                "synced_at": now_str
            }

        except Exception as e:
            logger.error("[STORAGE:SYNC_UNHANDLED_ERROR] Failed to sync lakehouse: %s", e, exc_info=True)
            return {
                "success": False,
                "company_name": safe_company,
                "fiscal_year": fy,
                "error": f"레이크하우스 동기화 실패: {str(e)}"
            }


# 전역 싱글톤 인스턴스
storage_manager = HybridStorageManager()
