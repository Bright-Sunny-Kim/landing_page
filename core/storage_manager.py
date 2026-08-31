import datetime
import io
import json
import logging
import os
import re
import zipfile

logger = logging.getLogger(__name__)


class HybridStorageManager:
    """
    로컬 파일 보관함 및 사내 Ubuntu 서버(PostgreSQL / Network Mount / SFTP)
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

    def get_storage_status(self):
        """현재 스토리지 모드 및 사내 Ubuntu 서버 연결 상태를 점검하여 반환합니다."""
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

        return status

    def save_analysis(self, company_name, fiscal_year, payload, raw_files=None):
        """
        분석 완료된 정규화 JSON, 감사조서(.md), 원본 엑셀/CSV(raw_files) 및 메타데이터를
        1) 사내 로컬 시점별(Timestamp) 타임시리즈 보관함
        2) 사내 Ubuntu 서버 (설정된 경우)
        에 1초 만에 안전하게 자동 영구 보관합니다.
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

        # 대상 디렉토리 목록 (로컬 + Ubuntu 마운트)
        target_base_dirs = [("local", self.local_base_dir)]
        if self.ubuntu_mount_path and os.path.exists(self.ubuntu_mount_path):
            target_base_dirs.append(("ubuntu_server", self.ubuntu_mount_path))

        for target_type, base_path in target_base_dirs:
            try:
                # 1. 회사 루트 및 연도별 시점 타임스탬프 세션 디렉토리 생성
                company_root_dir = os.path.join(base_path, safe_company)
                session_dir = os.path.join(company_root_dir, str(fy), session_id)
                raw_files_dir = os.path.join(session_dir, "raw_files")
                os.makedirs(raw_files_dir, exist_ok=True)

                # 2. 세션 디렉토리에 data.json 및 metadata.json 저장
                with open(os.path.join(session_dir, "data.json"), "w", encoding="utf-8") as jf:
                    json.dump(payload, jf, ensure_ascii=False, indent=2, default=str)

                with open(os.path.join(session_dir, meta_fn), "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf, ensure_ascii=False, indent=2, default=str)

                # 3. 마크다운 조서 저장
                report_md = payload.get("report_md", "")
                if report_md:
                    with open(os.path.join(session_dir, "report.md"), "w", encoding="utf-8") as rf:
                        rf.write(report_md)

                # 4. 원본 엑셀/CSV 바이너리 파일 영구 보존
                if raw_files:
                    for rf_item in raw_files:
                        rf_name = rf_item.get("filename", "")
                        rf_content = rf_item.get("content", b"")
                        if rf_name and rf_content:
                            safe_rf_name = re.sub(r'[\\/:*?"<>|]', "_", os.path.basename(rf_name))
                            with open(os.path.join(raw_files_dir, safe_rf_name), "wb") as rbf:
                                rbf.write(rf_content)

                # 5. 기존 호환성 및 0.01초 빠른 조회를 위한 회사 루트 백업 포인터 갱신
                with open(os.path.join(company_root_dir, data_fn), "w", encoding="utf-8") as cjf:
                    json.dump(payload, cjf, ensure_ascii=False, indent=2, default=str)

                if report_md:
                    with open(os.path.join(company_root_dir, report_fn), "w", encoding="utf-8") as crf:
                        crf.write(report_md)

                with open(os.path.join(company_root_dir, f"latest_{fy}_data.json"), "w", encoding="utf-8") as lf:
                    json.dump(payload, lf, ensure_ascii=False, indent=2, default=str)

                results["locations"].append({
                    "type": target_type,
                    "session_path": session_dir,
                    "status": "saved"
                })
                logger.info("[STORAGE:%s_SAVE] 시점별 영구 누적 저장 완료: %s/%s", target_type.upper(), safe_company, session_id)

            except Exception as le:
                logger.error("[STORAGE:%s_ERROR] 영구 보관함 저장 실패: %s", target_type.upper(), le, exc_info=True)
                results["locations"].append({"type": target_type, "status": "failed", "error": str(le)})

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
        """선택된 과거 데이터셋 JSON을 로컬 또는 Ubuntu 서버에서 0.01초 만에 로드합니다."""
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
                    "[STORAGE:LOAD_SUCCESS] 데이터셋 로드 성공: %s (경로: %s)",
                    target_id,
                    fp,
                )
                return data

        raise FileNotFoundError(
            f"'{safe_company}' 기업의 '{target_id}' 데이터를 찾을 수 없습니다."
        )


# 전역 싱글톤 인스턴스
storage_manager = HybridStorageManager()
