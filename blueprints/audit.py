# -*- coding: utf-8 -*-
"""
Hyean AI 회계감사 전용 포털 블루프린트 (blueprints/audit.py)
참여 회계사(CPA / Auditor) 및 마스터 관리자 전용 독립 포털 라우트 및 REST API
"""
import os
import json
import logging
import time
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, send_file
from core.extensions import supabase, MASTER_EMAIL, logger
from core.storage_manager import storage_manager
from core.audit_engine import (
    load_template_index_data, 
    generate_kgaap_account_working_paper,
    export_working_paper_excel
)

audit_bp = Blueprint('audit', __name__)

_auditor_pool_cache = None
_auditor_pool_cache_time = 0
AUDITOR_POOL_CACHE_TTL = 300  # 5분 서버 메모리 TTL

def invalidate_auditor_pool_cache():
    global _auditor_pool_cache, _auditor_pool_cache_time
    _auditor_pool_cache = None
    _auditor_pool_cache_time = 0
    logger.info('[AUDITOR_POOL:CACHE_INVALIDATED]')

# ==============================================================================
# 1. 뷰 라우트
# ==============================================================================

@audit_bp.route('/audit')
def audit_page():
    """참여 회계사 전용 포털 메인 뷰"""
    if 'email' not in session:
        logger.info("[AUTH_ROUTING] Unauthorized access to /audit, redirecting to login")
        return redirect(url_for('auth.login_page'))
    
    user_email = session.get('email', '')
    user_role = session.get('role', 'client')
    user_task = session.get('task_type', '')
    
    # 최고 관리자 또는 회계사/감사인 전용 허용
    is_authorized = (
        user_email == MASTER_EMAIL or 
        user_role in ['master', 'cpa', 'auditor']
    )
    
    if not is_authorized:
        logger.warning("[AUTH_ROUTING] Access denied for %s (role=%s, task=%s) to /audit", user_email, user_role, user_task)
        return redirect(url_for('pages.company_page', company_name=session.get('company', '')))
        
    logger.info("[AUDIT_PAGE] GET /audit - Loaded for user=%s, role=%s", user_email, user_role)
    return render_template('audit.html', 
                           username=session.get('username', '회계사'),
                           user_role=user_role,
                           user_email=user_email,
                           company_name=session.get('company', '회계법인 혜안'))


# ==============================================================================
# 2. 메타데이터 및 K-GAAP 2023 조서 색인 API
# ==============================================================================

@audit_bp.route('/api/audit/companies', methods=['GET'])
def get_audit_companies():
    """감사 대상 고객사 목록 반환 (회계사 포털 전용 전체 감사 고객사 및 배정 정보 연동)"""
    user_email = session.get('email', '')
    user_role = session.get('role', 'client')
    session_company = session.get('company', '').strip()
    logger.info("[API_REQ] GET /api/audit/companies for user=%s, role=%s, session_company=%s", 
                user_email, user_role, session_company)
    try:
        assignments = load_assignments_data() or []
        known_companies = {}
        
        # 1. assignments에서 로드
        for idx, a in enumerate(assignments):
            cname = a.get('company_name')
            if cname:
                known_companies[cname] = {
                    "id": a.get('id', idx + 1),
                    "company_name": cname,
                    "corporate_number": a.get('corporate_number', '법인'),
                    "in_charge_name": a.get('in_charge_name', '김동선'),
                    "in_charge_email": a.get('in_charge_email', 'cpaeastsun@gmail.com'),
                    "status_label": a.get('status_label', '실증감사 진행중')
                }
                
        # 2. MinIO S3 company-uploads 버킷에서 실제 업로드된 기업 추출
        try:
            if storage_manager and storage_manager.s3_client:
                resp = storage_manager.s3_client.list_objects_v2(Bucket='company-uploads', Delimiter='/')
                for p in resp.get('CommonPrefixes', []):
                    prefix_name = p.get('Prefix', '').rstrip('/')
                    if prefix_name and prefix_name not in known_companies:
                        known_companies[prefix_name] = {
                            "id": len(known_companies) + 1,
                            "company_name": prefix_name,
                            "corporate_number": "법인",
                            "in_charge_name": "김동선",
                            "in_charge_email": "cpaeastsun@gmail.com",
                            "status_label": "실증감사 진행중"
                        }
        except Exception as s3_err:
            logger.warning("[API_WARN] S3 company listing warning: %s", s3_err)

        # 3. 로컬 보관함 폴더 확인
        try:
            if os.path.exists(storage_manager.local_base_dir):
                for d in os.listdir(storage_manager.local_base_dir):
                    full_d = os.path.join(storage_manager.local_base_dir, d)
                    if os.path.isdir(full_d) and d not in known_companies and not d.startswith('.'):
                        known_companies[d] = {
                            "id": len(known_companies) + 1,
                            "company_name": d,
                            "corporate_number": "법인",
                            "in_charge_name": "김동선",
                            "in_charge_email": "cpaeastsun@gmail.com",
                            "status_label": "실증감사 진행중"
                        }
        except Exception as loc_err:
            logger.warning("[API_WARN] Local archive listing warning: %s", loc_err)

        # 4. 세션 회사 추가
        if session_company and session_company not in known_companies:
            known_companies[session_company] = {
                "id": len(known_companies) + 1,
                "company_name": session_company,
                "corporate_number": "법인",
                "in_charge_name": "김동선",
                "in_charge_email": "cpaeastsun@gmail.com",
                "status_label": "실증감사 진행중"
            }

        companies = list(known_companies.values())
        
        # 기본 기업이 없을 때의 안전 Fallback
        if not companies:
            companies = [
                {"id": 1, "company_name": "혜안_임시", "corporate_number": "법인", "in_charge_name": "김동선", "in_charge_email": "cpaeastsun@gmail.com", "status_label": "실증감사 진행중"},
                {"id": 2, "company_name": "(주)프레오", "corporate_number": "110111-1234567", "in_charge_name": "김동선", "in_charge_email": "cpaeastsun@gmail.com", "status_label": "실증감사 진행중"},
                {"id": 3, "company_name": "(주)더존비즈온", "corporate_number": "법인", "in_charge_name": "이진우", "in_charge_email": "jw.lee@hyean.com", "status_label": "기획/계획 단계"}
            ]

        # 세션 회사 또는 혜안_임시가 최상단에 오도록 우선 정렬
        companies.sort(key=lambda c: 0 if c['company_name'] in [session_company, '혜안_임시'] else 1)
        
        logger.info("[API_RES] /api/audit/companies count=%d for %s", len(companies), user_email)
        return jsonify({"success": True, "companies": companies})
    except Exception as e:
        logger.error("[API_ERROR] get_audit_companies failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/templates/tree', methods=['GET'])
def get_template_tree():
    """K-GAAP 2023 조서 6대 섹션 및 계정별 트리 데이터 반환"""
    logger.info("[API_REQ] GET /api/audit/templates/tree")
    try:
        templates = load_template_index_data()
        
        # 6대 섹션별로 그룹화
        sections = {
            "1000": {"code": "1000", "title": "Section 1000 - 감사계약", "items": []},
            "2000": {"code": "2000", "title": "Section 2000 - 위험평가", "items": []},
            "3000": {"code": "3000", "title": "Section 3000 - 위험에 대한 대응", "items": []},
            "4000": {"code": "4000", "title": "Section 4000 - 계정별 입증감사절차", "items": []},
            "7000": {"code": "7000", "title": "Section 7000 - 그룹감사", "items": []},
            "8000": {"code": "8000", "title": "Section 8000 - 감사완결", "items": []},
        }
        
        for t in templates:
            sec_code = t.get('section_code', '4000')
            if sec_code in sections:
                sections[sec_code]['items'].append({
                    "account_code": t.get('account_code'),
                    "account_name": t.get('account_name'),
                    "procedure_count": t.get('procedure_count', 0),
                    "filename": t.get('filename')
                })
                
        tree_list = list(sections.values())
        logger.info("[API_RES] /api/audit/templates/tree - Returned %d sections", len(tree_list))
        return jsonify({"success": True, "tree": tree_list})
    except Exception as e:
        logger.error("[API_ERROR] get_template_tree failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# 3. AI 감사조서 자동생성 및 엑셀 다운로드 API
# ==============================================================================

@audit_bp.route('/api/audit/working-papers/reconcile', methods=['POST'])
def reconcile_working_paper_api():
    """계정 선택 시 6대 장부 JSON 기반 실시간 대사(Reconciliation) 수치 즉시 반환"""
    data = request.get_json() or {}
    company_name = data.get('company_name', '').strip()
    fiscal_year = int(data.get('fiscal_year', 2025))
    account_code = data.get('account_code', 'A-0').strip()
    
    logger.info("[WP_RECON:REQ] Reconcile account: company=%s, year=%s, account=%s", 
                company_name, fiscal_year, account_code)
    
    if not company_name:
        return jsonify({"success": False, "error": "회사명을 선택해주세요."}), 400
        
    try:
        archive_payload = storage_manager.load_dataset(company_name)
        normalized_bundle = archive_payload.get('normalized_bundle') if archive_payload else None
        
        # 가벼운 대사 계산 수행
        result = generate_kgaap_account_working_paper(
            company_name=company_name,
            fiscal_year=fiscal_year,
            account_code=account_code,
            normalized_bundle=normalized_bundle,
            author=session.get('username', '공인회계사')
        )
        
        return jsonify({
            "success": True, 
            "reconciliation": result.get('reconciliation', {}),
            "related_pnl": result.get('related_pnl', []),
            "account_info": result.get('account_info', {})
        })
    except Exception as e:
        logger.error("[WP_RECON:ERR] Reconcile failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/working-papers/generate', methods=['POST'])
def generate_working_paper_api():
    """6대 장부 JSON + K-GAAP 2023 RAG 기반 계정별 조서 자동 생성"""
    data = request.get_json() or {}
    company_name = data.get('company_name', '').strip()
    fiscal_year = int(data.get('fiscal_year', 2025))
    account_code = data.get('account_code', 'A-0').strip()
    
    logger.info("[WP_GEN:REQ] Generate working paper: company=%s, year=%s, account=%s", 
                company_name, fiscal_year, account_code)
    
    if not company_name:
        return jsonify({"success": False, "error": "감사 대상 기업을 선택해주세요."}), 400
        
    try:
        # 1. 우분투 서버/로컬 스토리지에서 6대 장부 JSON 로드
        archive_payload = storage_manager.load_dataset(company_name)
        normalized_bundle = archive_payload.get('normalized_bundle') if archive_payload else None
        
        # 2. K-GAAP 조서 생성 엔진 실행
        author_name = session.get('username', '공인회계사')
        result = generate_kgaap_account_working_paper(
            company_name=company_name,
            fiscal_year=fiscal_year,
            account_code=account_code,
            normalized_bundle=normalized_bundle,
            author=author_name
        )
        
        logger.info("[WP_GEN:RES] Generated %s successfully", account_code)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error("[WP_GEN:ERR] Failed to generate working paper: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/working-papers/export-excel', methods=['POST'])
def export_working_paper_excel_api():
    """K-GAAP 2023 원본 서식 엑셀 파일(.xlsx) 바이너리 다운로드"""
    data = request.get_json() or {}
    company_name = data.get('company_name', '').strip() or "회사"
    fiscal_year = int(data.get('fiscal_year', 2025))
    account_code = data.get('account_code', 'A-0').strip()
    working_paper_md = data.get('working_paper_md', '')
    reconciliation = data.get('reconciliation', {})
    
    logger.info("[WP_EXCEL:REQ] Export Excel: company=%s, year=%s, account=%s", 
                company_name, fiscal_year, account_code)
    
    try:
        stream = export_working_paper_excel(
            company_name=company_name,
            fiscal_year=fiscal_year,
            account_code=account_code,
            working_paper_md=working_paper_md,
            reconciliation_data=reconciliation
        )
        
        safe_company = company_name.replace(' ', '_')
        download_filename = f"{fiscal_year}_{safe_company}_감사조서_{account_code}.xlsx"
        
        return send_file(
            stream,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=download_filename
        )
    except Exception as e:
        logger.error("[WP_EXCEL:ERR] Export Excel failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# 4. 감사일정 캘린더 CRUD API
# ==============================================================================

# 기본 모의 일정 데이터 (DB 연결 전/로컬 Fallback용)
DEFAULT_SCHEDULES = [
    {"id": 1, "title": "내부통제 및 위험평가 (사전감사)", "schedule_type": "사전감사", "start_date": "2025-11-15", "end_date": "2025-11-20", "color": "#3b82f6", "memo": "핵심 통제 테스트"},
    {"id": 2, "title": "기말 재고실사 입회", "schedule_type": "재고실사", "start_date": "2025-12-31", "end_date": "2025-12-31", "color": "#10b981", "memo": "인천 물류센터 실사 입회"},
    {"id": 3, "title": "금융기관조회서 발송", "schedule_type": "금융조회발송", "start_date": "2026-01-05", "end_date": "2026-01-08", "color": "#a855f7", "memo": "주요 거래은행 6곳 발송"},
    {"id": 4, "title": "현장 실증감사 (기말감사)", "schedule_type": "기말감사", "start_date": "2026-01-20", "end_date": "2026-02-05", "color": "#f97316", "memo": "피감사회사 본사 현장감사"},
    {"id": 5, "title": "감사보고서 최종 발행", "schedule_type": "보고서제출", "start_date": "2026-03-20", "end_date": "2026-03-20", "color": "#ef4444", "memo": "주총 1주일 전 감사의견 전달"}
]

@audit_bp.route('/api/audit/schedules', methods=['GET', 'POST'])
def handle_audit_schedules():
    """감사 일정 조회 및 신규 등록"""
    if request.method == 'GET':
        logger.info("[CAL_REQ] GET /api/audit/schedules")
        try:
            if supabase:
                res = supabase.table('audit_schedules').select('*').order('start_date').execute()
                events = res.data or DEFAULT_SCHEDULES
            else:
                events = DEFAULT_SCHEDULES
                
            # FullCalendar 이벤트 포맷으로 변환
            fc_events = []
            for ev in events:
                fc_events.append({
                    "id": str(ev.get('id')),
                    "title": ev.get('title'),
                    "start": ev.get('start_date'),
                    "end": ev.get('end_date'),
                    "backgroundColor": ev.get('color', '#2563eb'),
                    "borderColor": ev.get('color', '#2563eb'),
                    "extendedProps": {
                        "schedule_type": ev.get('schedule_type'),
                        "memo": ev.get('memo', '')
                    }
                })
            return jsonify({"success": True, "events": fc_events})
        except Exception as e:
            logger.error("[CAL_ERROR] Failed to fetch schedules: %s", e)
            return jsonify({"success": True, "events": DEFAULT_SCHEDULES})
            
    elif request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        schedule_type = data.get('schedule_type', '기타')
        start_date = data.get('start_date')
        end_date = data.get('end_date') or start_date
        memo = data.get('memo', '')
        
        type_colors = {
            "사전감사": "#3b82f6",
            "기말감사": "#f97316",
            "재고실사": "#10b981",
            "금융조회발송": "#a855f7",
            "보고서제출": "#ef4444",
            "기타": "#64748b"
        }
        color = type_colors.get(schedule_type, "#2563eb")
        
        logger.info("[CAL_REQ] Create schedule: %s (%s ~ %s)", title, start_date, end_date)
        
        new_event = {
            "title": title,
            "schedule_type": schedule_type,
            "start_date": start_date,
            "end_date": end_date,
            "color": color,
            "memo": memo
        }
        
        try:
            if supabase:
                res = supabase.table('audit_schedules').insert(new_event).execute()
                saved_item = res.data[0] if res.data else new_event
            else:
                new_event["id"] = len(DEFAULT_SCHEDULES) + 1
                DEFAULT_SCHEDULES.append(new_event)
                saved_item = new_event
                
            return jsonify({"success": True, "event": saved_item})
        except Exception as e:
            logger.error("[CAL_ERROR] Create schedule failed: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# 5. 감사 프로젝트 & 회사별 Job Assign 관리 API
# ==============================================================================

ASSIGNMENTS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'audit_assignments.json')
ASSIGNMENT_LOGS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'audit_assignment_logs.json')

def load_assignments_data():
    """배정 데이터 로컬 JSON 로드 (Fallback 및 영속화)"""
    if os.path.exists(ASSIGNMENTS_FILE_PATH):
        try:
            with open(ASSIGNMENTS_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("[ASSIGN_LOAD:ERR] Failed to read assignments json: %s", e, exc_info=True)
    
    # 기본 초기 배정 데이터
    default_data = [
        {
            "id": 1,
            "company_name": "(주)프레오",
            "fiscal_year": 2025,
            "in_charge_name": "김동선",
            "in_charge_email": "cpaeastsun@gmail.com",
            "partner_name": "이진우 파트너",
            "members": [
                {"name": "김동선", "email": "cpaeastsun@gmail.com", "role": "In-charge"},
                {"name": "박지민", "email": "jm.park@hyean.com", "role": "Staff CPA"},
                {"name": "최영수", "email": "ys.choi@hyean.com", "role": "Staff CPA"}
            ],
            "account_assignments": {
                "A-0": "cpaeastsun@gmail.com",
                "C-0": "jm.park@hyean.com",
                "E-0": "cpaeastsun@gmail.com",
                "G-0": "ys.choi@hyean.com"
            },
            "status": "in_progress",
            "status_label": "실증감사 진행중",
            "target_report_date": "2026-03-20"
        },
        {
            "id": 2,
            "company_name": "(주)더존비즈온",
            "fiscal_year": 2025,
            "in_charge_name": "이진우",
            "in_charge_email": "jw.lee@hyean.com",
            "partner_name": "이진우 파트너",
            "members": [
                {"name": "이진우", "email": "jw.lee@hyean.com", "role": "In-charge"},
                {"name": "정다은", "email": "de.jung@hyean.com", "role": "Staff CPA"}
            ],
            "account_assignments": {
                "A-0": "jw.lee@hyean.com",
                "C-0": "de.jung@hyean.com"
            },
            "status": "planned",
            "status_label": "기획/계획 단계",
            "target_report_date": "2026-03-15"
        },
        {
            "id": 3,
            "company_name": "혜안_임시",
            "fiscal_year": 2025,
            "in_charge_name": "김동선",
            "in_charge_email": "cpaeastsun@gmail.com",
            "partner_name": "이진우 파트너",
            "members": [
                {"name": "김동선 (Master)", "email": "cpaeastsun@gmail.com", "role": "In-charge"},
                {"name": "김동선 (CPA)", "email": "cpaeastsun@naver.com", "role": "Lead CPA"}
            ],
            "account_assignments": {
                "A-0": "cpaeastsun@naver.com",
                "C-0": "cpaeastsun@naver.com",
                "E-0": "cpaeastsun@naver.com",
                "G-0": "cpaeastsun@naver.com"
            },
            "status": "in_progress",
            "status_label": "실증감사 진행중",
            "target_report_date": "2026-03-20"
        }
    ]
    save_assignments_data(default_data)
    return default_data

def save_assignments_data(data):
    """배정 데이터 로컬 JSON 저장"""
    try:
        os.makedirs(os.path.dirname(ASSIGNMENTS_FILE_PATH), exist_ok=True)
        with open(ASSIGNMENTS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("[ASSIGN_SAVE:OK] Saved %d assignments to %s", len(data), ASSIGNMENTS_FILE_PATH)
        return True
    except Exception as e:
        logger.error("[ASSIGN_SAVE:ERR] Failed to save assignments: %s", e, exc_info=True)
        return False

def load_assignment_logs_data():
    """감사팀 배정 변경 이력 로컬 JSON 로드"""
    if os.path.exists(ASSIGNMENT_LOGS_FILE_PATH):
        try:
            with open(ASSIGNMENT_LOGS_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("[ASSIGN_LOGS_LOAD:ERR] Failed to read assignment logs: %s", e, exc_info=True)
    return []

def record_assignment_log(company_name, fiscal_year, action_type, changed_by, before_data, after_data, diff_summary=None):
    """감사팀 배정 변경 이력 영구 기록"""
    try:
        logs = load_assignment_logs_data()
        log_entry = {
            "id": len(logs) + 1,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "company_name": company_name,
            "fiscal_year": fiscal_year,
            "action_type": action_type,  # 'CREATE', 'UPDATE_TEAM', 'UPDATE_STATUS', 'UPDATE_ACCOUNTS'
            "changed_by": changed_by,
            "diff_summary": diff_summary or "",
            "before_data": before_data,
            "after_data": after_data
        }
        logs.insert(0, log_entry)  # 최신 로그가 맨 위로
        os.makedirs(os.path.dirname(ASSIGNMENT_LOGS_FILE_PATH), exist_ok=True)
        with open(ASSIGNMENT_LOGS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        logger.info("[ASSIGN_LOG:OK] Recorded %s log for %s (FY %d) by %s", action_type, company_name, fiscal_year, changed_by)
        return True
    except Exception as e:
        logger.error("[ASSIGN_LOG:ERR] Failed to record assignment log: %s", e, exc_info=True)
        return False


@audit_bp.route('/api/audit/projects', methods=['GET'])
def get_audit_projects():
    """사업연도별 감사 프로젝트 및 참여 배정 목록 조회"""
    logger.info("[ASSIGN_REQ] GET /api/audit/projects")
    try:
        assignments = load_assignments_data()
        projects = []
        for a in assignments:
            projects.append({
                "id": a.get("id"),
                "company_name": a.get("company_name"),
                "fiscal_year": a.get("fiscal_year", 2025),
                "in_charge": f"{a.get('in_charge_name', '')} ({a.get('in_charge_email', '')})",
                "engagement_partner": a.get("partner_name", ""),
                "members": [m.get("name") for m in a.get("members", [])],
                "target_report_date": a.get("target_report_date", "2026-03-20"),
                "status": a.get("status", "in_progress"),
                "status_label": a.get("status_label", "진행중")
            })
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        logger.error("[ASSIGN_ERROR] Failed to fetch projects: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/assignments', methods=['GET', 'POST'])
def handle_audit_assignments():
    """회사별 Job Assign 목록 조회 및 저장/수정 API"""
    if request.method == 'GET':
        company_name = request.args.get('company_name', '').strip()
        user_email = request.args.get('user_email', '').strip()
        logger.info("[ASSIGN:REQ] GET assignments: company=%s, user_email=%s", company_name, user_email)
        
        try:
            assignments = load_assignments_data()
            
            # 특정 회사 필터링
            if company_name:
                assignments = [a for a in assignments if a.get('company_name') == company_name]
                
            # 특정 사용자 필터링 (본인이 In-charge이거나 멤버에 포함된 건)
            if user_email:
                assignments = [
                    a for a in assignments 
                    if a.get('in_charge_email') == user_email or 
                    any(m.get('email') == user_email for m in a.get('members', []))
                ]
                
            logger.info("[ASSIGN:RES] Returned %d assignments", len(assignments))
            return jsonify({"success": True, "assignments": assignments})
        except Exception as e:
            logger.error("[ASSIGN:ERR] Failed to get assignments: %s", e, exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500
            
    elif request.method == 'POST':
        payload = request.get_json() or {}
        company_name = payload.get('company_name', '').strip()
        fiscal_year = int(payload.get('fiscal_year', 2025))
        changed_by = session.get('username') or session.get('email', '마스터 관리자')
        
        logger.info("[ASSIGN:POST] Update assignment for company=%s, year=%d by %s", company_name, fiscal_year, changed_by)
        
        if not company_name:
            return jsonify({"success": False, "error": "회사명을 입력해주세요."}), 400
            
        try:
            assignments = load_assignments_data()
            found = False
            before_snapshot = None
            action_type = 'UPDATE_TEAM'
            
            for idx, item in enumerate(assignments):
                if item.get('company_name') == company_name and int(item.get('fiscal_year', 0)) == fiscal_year:
                    before_snapshot = dict(item)
                    assignments[idx].update(payload)
                    found = True
                    break
            
            if not found:
                action_type = 'CREATE'
                new_id = max([a.get('id', 0) for a in assignments] or [0]) + 1
                payload['id'] = new_id
                assignments.append(payload)
                
            save_assignments_data(assignments)
            
            # 변경점 요약 생성 및 로그 영구 보존
            diff_parts = []
            if before_snapshot:
                if before_snapshot.get('in_charge_email') != payload.get('in_charge_email'):
                    diff_parts.append(f"주임 변경: {before_snapshot.get('in_charge_name', '')} ➔ {payload.get('in_charge_name', '')}")
                if before_snapshot.get('status') != payload.get('status'):
                    diff_parts.append(f"단계 변경: {before_snapshot.get('status_label', '')} ➔ {payload.get('status_label', '')}")
                if before_snapshot.get('partner_name') != payload.get('partner_name'):
                    diff_parts.append(f"파트너 변경: {before_snapshot.get('partner_name', '')} ➔ {payload.get('partner_name', '')}")
            else:
                diff_parts.append(f"신규 감사팀 배정 생성 (주임: {payload.get('in_charge_name', '')})")
                
            diff_str = ", ".join(diff_parts) if diff_parts else "감사팀 배정 정보 갱신"
            record_assignment_log(
                company_name=company_name,
                fiscal_year=fiscal_year,
                action_type=action_type,
                changed_by=changed_by,
                before_data=before_snapshot,
                after_data=payload,
                diff_summary=diff_str
            )
            
            logger.info("[ASSIGN:POST_SUCCESS] Saved assignment and log for %s", company_name)
            invalidate_auditor_pool_cache()
            return jsonify({"success": True, "assignment": payload})
        except Exception as e:
            logger.error("[ASSIGN:POST_ERR] Failed to save assignment: %s", e, exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# K-GAAP 2023 전 영역(1000~8000) 105대 감사조서 및 절차 표준 메타데이터
# ==============================================================================
K_GAAP_STANDARD_PROCEDURES = [
    # Section 1000: 감사계약 및 계획
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1100A", "account_name": "신규 수임 및 재계약 위험 평가 (기준서 210/220)", "filename": "1100A_감사수임.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1100", "account_name": "감사계약서 체결 및 감사수임 승인", "filename": "1100_감사계약서.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1101A", "account_name": "감수인 독립성 및 윤리기준 준수 평가", "filename": "1101A_독립성평가.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1200", "account_name": "감사전략 및 전반 감사계획 수립", "filename": "1200_전반감사계획.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1300A", "account_name": "감사팀 편성 및 업무분장 (Job Assign)", "filename": "1300A_감사팀편성.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1300B", "account_name": "감사일정 및 투입예산 계획", "filename": "1300B_감사일정예산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "1000", "section_name": "감사계약 및 계획", "account_code": "1300", "account_name": "감사팀 킥오프 회의 및 내부 커뮤니케이션", "filename": "1300_감사팀회의.xlsx", "default_assignee": "cpaeastsun@gmail.com"},

    # Section 2000: 중요성 및 위험평가
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2100A", "account_name": "기업 및 환경 이해와 중요왜곡표시위험 식별 (기준서 315)", "filename": "2100A_위험식별.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2100", "account_name": "위험평가 종합 요약표", "filename": "2100_위험평가요약.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2110-02", "account_name": "중요성 기준 설정 세부 계산표", "filename": "2110-02_중요성계산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2110A", "account_name": "전반적 중요성(OM) 및 수행중요성(PM) 결정 (기준서 320)", "filename": "2110A_중요성결정.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2110B", "account_name": "명백하게 사소하지 않은 금액(AMPT) 기준표", "filename": "2110B_AMPT.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2110", "account_name": "중요성 및 한계위험 평가표", "filename": "2110_중요성평가.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2120A", "account_name": "기획단계 예비 분석적 절차 (기준서 520)", "filename": "2120A_분석적절차.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2120", "account_name": "예비 분석적 검토 조서", "filename": "2120_분석적검토.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2131", "account_name": "전문가 활용 계획 및 적격성 평가 (기준서 620)", "filename": "2131_전문가활용.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2132", "account_name": "내부감사인 활동 활용 평가 (기준서 610)", "filename": "2132_내부감사활용.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2133", "account_name": "서비스조직(SOC) 이용에 대한 감사 고려사항 (기준서 402)", "filename": "2133_서비스조직.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2301", "account_name": "부정위험 식별 및 평가 (기준서 240)", "filename": "2301_부정위험.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2302", "account_name": "법규위반 가능성 검토 (기준서 250)", "filename": "2302_법규위반.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2511", "account_name": "내부통제 환경 및 통제구조 평가", "filename": "2511_통제환경.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2512", "account_name": "기업의 위험평가 프로세스 검토", "filename": "2512_위험평가프로세스.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2513", "account_name": "통제활동 및 정보시스템 이해", "filename": "2513_통제활동.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2520", "account_name": "업무프로세스(RCM) 흐름 및 통제기술서", "filename": "2520_RCM통제기술.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2530", "account_name": "IT 일반통제(ITGC) 평가 계획", "filename": "2530_ITGC계획.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2531A", "account_name": "정보기술(IT) 응용통제(ITAC) 검토", "filename": "2531A_ITAC검토.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2531", "account_name": "IT 일반통제 세부 테스트 조서", "filename": "2531_ITGC테스트.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2532", "account_name": "IT 시스템 접근 및 변경통제 검토", "filename": "2532_IT접근변경.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2600", "account_name": "식별된 유의적 위험(Significant Risk) 목록", "filename": "2600_유의적위험.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2700A", "account_name": "감사위원회/지배기구와의 커뮤니케이션 계획 (기준서 260)", "filename": "2700A_지배기구계획.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "2000", "section_name": "중요성 및 위험평가", "account_code": "2700", "account_name": "지배기구 커뮤니케이션 요약", "filename": "2700_지배기구요약.xlsx", "default_assignee": "cpaeastsun@gmail.com"},

    # Section 3000: 평가된 위험에 대한 대응
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3100", "account_name": "전반적 위험 대응전략 및 실증절차 계획 (기준서 330)", "filename": "3100_위험대응전략.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3150", "account_name": "내부회계관리제도 통제테스트(TOC) 설계", "filename": "3150_TOC설계.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3200", "account_name": "핵심 감사절차 및 표본추출(Sampling) 계획 (기준서 530)", "filename": "3200_표본추출.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3300A", "account_name": "외부조회(Confirmation) 통제 및 발송계획 (기준서 505)", "filename": "3300A_외부조회통제.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3300", "account_name": "외부조회 관리 대장", "filename": "3300_외부조회대장.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3400", "account_name": "기초잔액 감사절차 (신규 감사 대상, 기준서 510)", "filename": "3400_기초잔액.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3500", "account_name": "회계추정치 및 공정가치 평가 위험대응 (기준서 540)", "filename": "3500_회계추정치.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3600", "account_name": "특수관계자 거래 검토 계획 (기준서 550)", "filename": "3600_특수관계자.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3650", "account_name": "소송 및 우발상황 확인 절차 (기준서 501)", "filename": "3650_소송우발.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3700", "account_name": "실질적 분석적 절차(Substantive Analytical Procedures) 계획", "filename": "3700_실질분석.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3800", "account_name": "세부테스트(Test of Details) 접근전략", "filename": "3800_세부테스트.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "3000", "section_name": "평가된 위험에 대한 대응", "account_code": "3910", "account_name": "중간감사 결과 요약 및 기말 추가감사 절차 수립", "filename": "3910_중간감사결과.xlsx", "default_assignee": "cpaeastsun@gmail.com"},

    # Section 4000: 계정별 입증감사절차
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "A-0", "account_name": "현금및현금성자산 및 단기금융상품", "filename": "A-0_현금및금융상품.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "B-0", "account_name": "단기투자자산 및 유가증권", "filename": "B-0_단기투자증권.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "C-0", "account_name": "매출채권 및 대손충당금 평가", "filename": "C-0_매출채권.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "D-0", "account_name": "기타수취채권 및 미수금", "filename": "D-0_기타수취채권.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "DER-0", "account_name": "파생상품 평가 및 회계처리", "filename": "DER-0_파생상품.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "DL-0", "account_name": "대여금 및 장기수취채권", "filename": "DL-0_대여금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "E-0", "account_name": "재고자산 실사 및 평가(저가법)", "filename": "E-0_재고자산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "E10", "account_name": "재고자산 입출고 컷오프(Cut-off) 테스트", "filename": "E10_재고컷오프.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "F-0", "account_name": "선급금 및 선급비용", "filename": "F-0_선급금비용.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "G-0", "account_name": "유형자산 취득·처분 및 감가상각 검토", "filename": "G-0_유형자산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "H-0", "account_name": "무형자산 및 영업권 손상검사", "filename": "H-0_무형자산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "I-0", "account_name": "투자부동산", "filename": "I-0_투자부동산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "J-0", "account_name": "종속기업 및 관계기업 지분법투자주식", "filename": "J-0_지분법주식.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "JV-0", "account_name": "분개장 테스트 (JET: Journal Entry Testing)", "filename": "JV-0_분개장JET.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "SAJ-0", "account_name": "총계정원장(GL) 수치 대사 및 시산표 검증", "filename": "SAJ-0_총원장대사.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "AA-0", "account_name": "매입채무 및 미지급금", "filename": "AA-0_매입채무.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "BBDD-0", "account_name": "단기차입금 및 유동성장기부채", "filename": "BBDD-0_단기차입금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "CC-0", "account_name": "미지급비용 및 예수금", "filename": "CC-0_미지급비용.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "EE-0", "account_name": "장기차입금 및 사채", "filename": "EE-0_장기차입금사채.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "FF-0", "account_name": "퇴직급여충당부채 및 퇴직연금자산", "filename": "FF-0_퇴직부채연금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "FFF-0", "account_name": "기타 비유동부채 및 충당부채", "filename": "FFF-0_기타부채충당금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "TUL-0", "account_name": "리스(Lease)부채 및 사용권자산", "filename": "TUL-0_리스사용권자산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "GG-0", "account_name": "자본금, 자본잉여금 및 기타자본항목", "filename": "GG-0_자본금잉여금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "CL-0", "account_name": "이익잉여금 및 배당금 검토", "filename": "CL-0_이익잉여금.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "P-0", "account_name": "매출액 및 영업수익 실증분석", "filename": "P-0_매출수익.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "Q-0", "account_name": "매출원가(COGS) 실증테스트", "filename": "Q-0_매출원가.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "R-0", "account_name": "판매비와관리비 세부 분석", "filename": "R-0_판관비.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "S-0", "account_name": "금융수익 및 금융원가", "filename": "S-0_금융손익.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "T-0", "account_name": "기타영업외수익 및 기타비용", "filename": "T-0_영업외손익.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "U-0", "account_name": "법인세비용 및 이연법인세자산·부채", "filename": "U-0_법인세이연세.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "IOC-0", "account_name": "포괄손익 및 중단영업손익", "filename": "IOC-0_기타포괄손익.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "EST-0", "account_name": "회계추정치 불확실성 종합 평가", "filename": "EST-0_추정불확실성.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "4000", "section_name": "계정별 입증감사절차", "account_code": "CF-0", "account_name": "현금흐름표(Cash Flows) 검증", "filename": "CF-0_현금흐름표.xlsx", "default_assignee": "cpaeastsun@gmail.com"},

    # Section 7000: 그룹감사 및 연결재무제표
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7000", "account_name": "그룹감사 전반 전략 및 범위 결정 (기준서 600)", "filename": "7000_그룹감사전략.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7100A", "account_name": "유의적 부문(Component) 식별 및 위험평가", "filename": "7100A_부문식별.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7100", "account_name": "부문감사인 업무 지시 및 협업 계획", "filename": "7100_부문감사지시.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7200A", "account_name": "부문감사인 독립성 및 역량 평가", "filename": "7200A_부문역량평가.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7200", "account_name": "부문 감사보고서 및 감사결과 검토", "filename": "7200_부문결과검토.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7300", "account_name": "그룹 중요성(Group Materiality) 배부표", "filename": "7300_그룹중요성배부.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7400-01", "account_name": "내부거래 및 상호채권채무 대사 제거", "filename": "7400-01_내부거래제거.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7400", "account_name": "미실현손익 제거 검증", "filename": "7400_미실현손익.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7410E", "account_name": "연결 이연법인세 및 세효과 조정", "filename": "7410E_연결이연법인세.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7410", "account_name": "연결 자본조정 및 지분변동 검토", "filename": "7410_연결자본조정.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7510A", "account_name": "해외종속기업 외화환산 검증", "filename": "7510A_해외외화환산.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7510", "account_name": "연결현금흐름표 검증", "filename": "7510_연결현금흐름.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7530", "account_name": "연결 주석공시 적합성 검토", "filename": "7530_연결주석공시.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7555", "account_name": "종속기업 취득/처분 및 영업권 산정", "filename": "7555_취득처분영업권.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7560A", "account_name": "비지배지분 측정 및 손익배분", "filename": "7560A_비지배지분.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7560", "account_name": "연결재무제표 총괄 검토표", "filename": "7560_연결총괄검토.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "7000", "section_name": "그룹감사 및 연결재무제표", "account_code": "7570", "account_name": "그룹감사 완결 및 최종 보고", "filename": "7570_그룹감사보고.xlsx", "default_assignee": "cpaeastsun@gmail.com"},

    # Section 8000: 감사완결 및 보고
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8100A", "account_name": "후속사건(Subsequent Events) 검토 (기준서 560)", "filename": "8100A_후속사건.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8100", "account_name": "기말 이후 거래 및 중대사건 확인표", "filename": "8100_기말이후거래.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8110A", "account_name": "계속기업가정(Going Concern) 평가 (기준서 570)", "filename": "8110A_계속기업평가.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8110", "account_name": "계속기업 불확실성 대응계획 검토", "filename": "8110_계속기업불확실성.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8200", "account_name": "경영자확인서(Management Representation) 징구 (기준서 580)", "filename": "8200_경영자확인서.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8300", "account_name": "미수정왜곡표시(Uncorrected Misstatements) 집계표 (기준서 450)", "filename": "8300_미수정왜곡표시.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8400", "account_name": "최종 분석적 검토(Final Analytical Procedures)", "filename": "8400_최종분석검토.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8500", "account_name": "감사조서 정리 및 업무품질관리검토(EQCR)", "filename": "8500_EQCR품질관리.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8550", "account_name": "지배기구와의 최종 커뮤니케이션", "filename": "8550_지배기구최종보고.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8600A", "account_name": "감사의견 형성 및 감사보고서 초안 작성 (기준서 700/705)", "filename": "8600A_감사의견초안.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8600", "account_name": "핵심감사사항(KAM) 결정 및 기재", "filename": "8600_핵심감사사항.xlsx", "default_assignee": "cpaeastsun@gmail.com"},
    {"section_code": "8000", "section_name": "감사완결 및 보고", "account_code": "8700", "account_name": "최종 감사문서 편철 및 보존 승인 (기준서 230)", "filename": "8700_조서편철보존.xlsx", "default_assignee": "cpaeastsun@gmail.com"}
]


@audit_bp.route('/api/audit/procedures/all', methods=['GET'])
def get_all_audit_procedures_api():
    """
    [신규] 우분투 서버 /mnt/storage/minio_data/audit-lakehouse/audit_procedure 및
    K-GAAP 2023 6대 섹션(1000~8000) 105개 전체 절차 목록 반환 API
    """
    logger.info("[PROCEDURES_ALL:REQ] GET /api/audit/procedures/all")
    try:
        # 섹션별 그룹화 트리 구성
        section_titles = {
            "1000": "Section 1000 - 감사계약 및 계획 (7개 절차)",
            "2000": "Section 2000 - 중요성 및 위험평가 (24개 절차)",
            "3000": "Section 3000 - 평가된 위험에 대한 대응 (12개 절차)",
            "4000": "Section 4000 - 계정별 입증감사절차 (33개 절차)",
            "7000": "Section 7000 - 그룹감사 및 연결재무제표 (17개 절차)",
            "8000": "Section 8000 - 감사완결 및 보고 (12개 절차)"
        }
        
        grouped_sections = {}
        for item in K_GAAP_STANDARD_PROCEDURES:
            sec = item["section_code"]
            if sec not in grouped_sections:
                grouped_sections[sec] = {
                    "section_code": sec,
                    "section_title": section_titles.get(sec, f"Section {sec}"),
                    "items": []
                }
            grouped_sections[sec]["items"].append(item)
            
        tree = list(grouped_sections.values())
        logger.info("[PROCEDURES_ALL:RES] Returned %d procedures in %d sections", len(K_GAAP_STANDARD_PROCEDURES), len(tree))
        return jsonify({
            "success": True,
            "total_count": len(K_GAAP_STANDARD_PROCEDURES),
            "sections": tree,
            "flat_list": K_GAAP_STANDARD_PROCEDURES
        })
    except Exception as e:
        logger.error("[PROCEDURES_ALL:ERR] Failed to list audit procedures: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/target-companies', methods=['GET'])
def get_audit_target_companies_api():
    """
    [신규] 감사대상회사현황 API: 로그인 시 주요업무를 '회계감사'로 체크한 사용자의 주요정보를 연도별로 반환
    """
    fiscal_year = request.args.get('fiscal_year', '2025').strip()
    logger.info("[TARGET_COMPANIES:REQ] GET /api/audit/target-companies (fiscal_year=%s)", fiscal_year)
    try:
        assignments = load_assignments_data() or []
        assign_map = {a.get('company_name'): a for a in assignments if not fiscal_year or fiscal_year == 'all' or str(a.get('fiscal_year', '2025')) == fiscal_year}
        
        target_list = []
        seen_companies = set()
        
        # 1. Supabase에서 사용자 및 서류제출 데이터 조회
        if supabase:
            try:
                # 회계감사 주요업무 또는 client 역할인 사용자 조회
                u_res = supabase.table('users').select('*').neq('email', MASTER_EMAIL).execute()
                all_users = u_res.data or []
                
                # 파일 제출 현황 조회
                f_res = supabase.table('company_files').select('company_name, file_url, file_name, status').execute()
                all_files = f_res.data or []
                
                for u in all_users:
                    cname = (u.get('company') or '').strip()
                    task = (u.get('task_type') or '').strip()
                    role = (u.get('role') or 'client').strip()
                    
                    # 주요업무가 '회계감사'이거나 client/partner로 감사 수임된 경우
                    is_audit_target = (task == '회계감사' or role in ['client', 'partner'] or cname in assign_map)
                    
                    if cname and is_audit_target and cname not in seen_companies:
                        seen_companies.add(cname)
                        
                        # 서류 제출율 계산
                        comp_files = [f for f in all_files if f.get('company_name') == cname]
                        valid_cnt = sum(1 for f in comp_files if f.get('file_url') or (f.get('file_name') and '해당사항없음' in f.get('file_name')))
                        upload_rate = min(100, int((valid_cnt / 16.0) * 100))
                        
                        # 6대 장부 수집 상태 (스토리지 및 파일 확인)
                        ledger_names = ['재무상태표', '손익계산서', '합계잔액시산표', '분개장', '총계정원장', '거래처원장']
                        ledger_hit = sum(1 for ln in ledger_names if any(ln in (f.get('file_name') or '') for f in comp_files))
                        ledger_status = f"6대 장부 완비 (6/6)" if ledger_hit >= 6 else (f"일부 수집 ({ledger_hit}/6)" if ledger_hit > 0 else "미수집 (0/6)")
                        
                        # 배정 정보 매핑
                        assigned = assign_map.get(cname, {})
                        in_charge_name = assigned.get('in_charge_name') or "김동선"
                        in_charge_email = assigned.get('in_charge_email') or "cpaeastsun@gmail.com"
                        audit_status = assigned.get('status_label') or ("실증감사 진행중" if upload_rate >= 50 else "기획/계획 단계")
                        
                        target_list.append({
                            "company_name": cname,
                            "corporate_number": u.get('corporate_number') or "110111-0000000",
                            "contact_name": u.get('username') or u.get('email', '').split('@')[0],
                            "email": u.get('email'),
                            "created_at": (u.get('created_at') or '')[:10] or "2025-01-01",
                            "fiscal_year": int(fiscal_year) if fiscal_year.isdigit() else 2025,
                            "task_type": "회계감사",
                            "upload_rate": upload_rate,
                            "ledger_status": ledger_status,
                            "audit_status": audit_status,
                            "in_charge_name": in_charge_name,
                            "in_charge_email": in_charge_email
                        })
            except Exception as db_err:
                logger.warning("[TARGET_COMPANIES:WARN] Supabase fetch warning: %s, fallback used", db_err)
                
        # 2. 로컬 Fallback 및 assignments 보완
        for cname, assigned in assign_map.items():
            if cname not in seen_companies:
                seen_companies.add(cname)
                target_list.append({
                    "company_name": cname,
                    "corporate_number": assigned.get('corporate_number', '110111-1234567'),
                    "contact_name": assigned.get('in_charge_name', '김동선'),
                    "email": assigned.get('in_charge_email', 'cpaeastsun@gmail.com'),
                    "created_at": "2025-01-15",
                    "fiscal_year": int(assigned.get('fiscal_year', 2025)),
                    "task_type": "회계감사",
                    "upload_rate": 85 if cname == '(주)프레오' else (100 if cname == '혜안_임시' else 40),
                    "ledger_status": "6대 장부 완비 (6/6)" if cname in ['(주)프레오', '혜안_임시'] else "일부 수집 (2/6)",
                    "audit_status": assigned.get('status_label', '실증감사 진행중'),
                    "in_charge_name": assigned.get('in_charge_name', '김동선'),
                    "in_charge_email": assigned.get('in_charge_email', 'cpaeastsun@gmail.com')
                })
                
        # 기본 예시 데이터 보장
        if not target_list:
            target_list = [
                {
                    "company_name": "혜안_임시",
                    "corporate_number": "110111-9999999",
                    "contact_name": "김동선",
                    "email": "cpaeastsun@gmail.com",
                    "created_at": "2025-01-01",
                    "fiscal_year": int(fiscal_year) if fiscal_year.isdigit() else 2025,
                    "task_type": "회계감사",
                    "upload_rate": 100,
                    "ledger_status": "6대 장부 완비 (6/6)",
                    "audit_status": "실증감사 진행중",
                    "in_charge_name": "김동선",
                    "in_charge_email": "cpaeastsun@gmail.com"
                },
                {
                    "company_name": "(주)프레오",
                    "corporate_number": "110111-1234567",
                    "contact_name": "프레오 담당자",
                    "email": "contact@freo.co.kr",
                    "created_at": "2025-02-10",
                    "fiscal_year": int(fiscal_year) if fiscal_year.isdigit() else 2025,
                    "task_type": "회계감사",
                    "upload_rate": 85,
                    "ledger_status": "6대 장부 완비 (6/6)",
                    "audit_status": "실증감사 진행중",
                    "in_charge_name": "김동선",
                    "in_charge_email": "cpaeastsun@gmail.com"
                },
                {
                    "company_name": "(주)더존비즈온",
                    "corporate_number": "110111-7654321",
                    "contact_name": "더존 회계팀",
                    "email": "audit@duzon.com",
                    "created_at": "2025-01-20",
                    "fiscal_year": int(fiscal_year) if fiscal_year.isdigit() else 2025,
                    "task_type": "회계감사",
                    "upload_rate": 45,
                    "ledger_status": "일부 수집 (3/6)",
                    "audit_status": "기획/계획 단계",
                    "in_charge_name": "이진우",
                    "in_charge_email": "jw.lee@hyean.com"
                }
            ]
            
        logger.info("[TARGET_COMPANIES:RES] Returned %d target companies for year=%s", len(target_list), fiscal_year)
        return jsonify({
            "success": True,
            "count": len(target_list),
            "fiscal_year": fiscal_year,
            "companies": target_list
        })
    except Exception as e:
        logger.error("[TARGET_COMPANIES:ERR] Failed to load target companies: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/auditor-pool', methods=['GET'])
def get_auditor_pool_api():
    """
    [고도화 1] 포털 내 감사인(CPA/Auditor) 인력 풀 조회 API
    - 서버 인메모리 TTL 캐싱(5분) 적용: 불필요한 반복 쿼리 방지
    - 전역 예외 처리 & 안전 Fallback 보장: 500 에러 원천 차단
    """
    global _auditor_pool_cache, _auditor_pool_cache_time
    logger.info("[AUDITOR_POOL:REQ] GET /api/audit/auditor-pool")
    
    force_refresh = request.args.get('refresh') == 'true'
    now = time.time()
    
    # 1. 서버 인메모리 캐시 히트 검사 (5분 TTL)
    if not force_refresh and _auditor_pool_cache is not None and (now - _auditor_pool_cache_time) < AUDITOR_POOL_CACHE_TTL:
        logger.info("[AUDITOR_POOL:CACHE_HIT] Returned %d cached auditors (age=%.1fs)", len(_auditor_pool_cache), now - _auditor_pool_cache_time)
        return jsonify({"success": True, "count": len(_auditor_pool_cache), "auditors": _auditor_pool_cache, "cached": True})

    try:
        auditors = []
        assignments = load_assignments_data() or []
        
        # 105개 K-GAAP 표준 절차 코드-정보 맵
        proc_lookup = {p.get('account_code'): p for p in K_GAAP_STANDARD_PROCEDURES}
        
        # 각 감사인별 배정 세부 데이터 구성 맵
        # structure: { email: { "companies": { (company_name, year): { "company_name": ..., "fiscal_year": ..., "status": ..., "role": ..., "procedures": [...] } } } }
        auditor_detail_map = {}

        def get_or_create_auditor_entry(em):
            if em not in auditor_detail_map:
                auditor_detail_map[em] = {"companies": {}}
            return auditor_detail_map[em]

        for a in assignments:
            cname = a.get('company_name', '')
            fyear = int(a.get('fiscal_year', 2025))
            st_label = a.get('status_label', '진행중')
            key = (cname, fyear)
            
            # (1) 주임 감사인 (In-charge)
            in_chg = a.get('in_charge_email')
            if in_chg:
                entry = get_or_create_auditor_entry(in_chg)
                if key not in entry["companies"]:
                    entry["companies"][key] = {
                        "company_name": cname,
                        "fiscal_year": fyear,
                        "status": st_label,
                        "role": "주임 감사인 (In-charge)",
                        "procedures": []
                    }
                else:
                    entry["companies"][key]["role"] = "주임 감사인 (In-charge)"

            # (2) 참여 감사인 (Members)
            for m in a.get('members', []):
                m_em = m.get('email')
                if m_em:
                    entry = get_or_create_auditor_entry(m_em)
                    if key not in entry["companies"]:
                        entry["companies"][key] = {
                            "company_name": cname,
                            "fiscal_year": fyear,
                            "status": st_label,
                            "role": m.get('role', '담당 감사인'),
                            "procedures": []
                        }

            # (3) 105개 감사 절차별 개별 배정자 매핑
            acc_assigns = a.get('account_assignments') or {}
            for acc_code, assignee_em in acc_assigns.items():
                if assignee_em:
                    entry = get_or_create_auditor_entry(assignee_em)
                    if key not in entry["companies"]:
                        entry["companies"][key] = {
                            "company_name": cname,
                            "fiscal_year": fyear,
                            "status": st_label,
                            "role": "절차 담당 감사인",
                            "procedures": []
                        }
                    
                    p_info = proc_lookup.get(acc_code, {})
                    entry["companies"][key]["procedures"].append({
                        "code": acc_code,
                        "name": p_info.get("account_name", f"감사절차 {acc_code}"),
                        "section_code": p_info.get("section_code", "4000"),
                        "section_name": p_info.get("section_name", "계정별 입증감사절차"),
                        "status": "진행중"
                    })

        # 1. Supabase 연동 시 실시간 감사인 사용자 조회
        if supabase:
            try:
                res = supabase.table('users').select('*').execute()
                user_list = res.data or []
                for u in user_list:
                    role = u.get('role', 'client')
                    task = u.get('task_type', '')
                    is_aud = role in ['cpa', 'auditor', 'master'] or task == '회계감사' or u.get('is_auditor')
                    u_email = u.get('email', '')
                    if is_aud or u_email == MASTER_EMAIL:
                        comp_dict = auditor_detail_map.get(u_email, {}).get("companies", {})
                        assigned_companies_list = []
                        for comp_data in comp_dict.values():
                            assigned_companies_list.append({
                                "company_name": comp_data["company_name"],
                                "fiscal_year": comp_data["fiscal_year"],
                                "status": comp_data["status"],
                                "role": comp_data["role"],
                                "procedure_count": len(comp_data["procedures"]),
                                "procedures": comp_data["procedures"]
                            })
                            
                        auditors.append({
                            "id": u.get('id'),
                            "name": u.get('username') or u_email.split('@')[0],
                            "email": u_email,
                            "company": u.get('company', '회계법인 혜안'),
                            "role": role,
                            "task_type": task or '회계감사',
                            "cpa_number": u.get('cpa_number') or ('CPA-2024-001' if u_email == MASTER_EMAIL else '-'),
                            "title": "대표/품질관리실장 (CPA)" if u_email == MASTER_EMAIL else ("공인회계사(CPA)" if role in ['cpa', 'master'] else "감사팀원 (Staff)"),
                            "created_at": (u.get('created_at') or '')[:10] or "2025-01-01",
                            "assigned_count": len(assigned_companies_list),
                            "assigned_companies": assigned_companies_list
                        })
                logger.info("[AUDITOR_POOL:DB] Retrieved %d auditors from Supabase", len(auditors))
            except Exception as e:
                logger.warning("[AUDITOR_POOL:WARN] Supabase query failed: %s, using fallback", e)

        # 2. 로컬 Fallback 기본 감사인 풀 (DB 미연결 또는 초기 상태 방어)
        if not auditors:
            fallback_seeds = [
                {"id": 1, "name": "김동선", "email": "cpaeastsun@gmail.com", "role": "master", "cpa_number": "CPA-2024-001", "title": "대표/품질관리실장 (CPA)", "created_at": "2024-01-01"},
                {"id": 2, "name": "김동선(CPA)", "email": "cpaeastsun@naver.com", "role": "cpa", "cpa_number": "CPA-2024-002", "title": "시니어 공인회계사 (CPA)", "created_at": "2024-03-01"},
                {"id": 3, "name": "이진우", "email": "jw.lee@hyean.com", "role": "cpa", "cpa_number": "CPA-2020-045", "title": "업무수행이사 (Partner)", "created_at": "2024-01-15"},
                {"id": 4, "name": "박지민", "email": "jm.park@hyean.com", "role": "auditor", "cpa_number": "CPA-2025-112", "title": "스태프 회계사 (Staff)", "created_at": "2025-01-10"},
                {"id": 5, "name": "최영수", "email": "ys.choi@hyean.com", "role": "auditor", "cpa_number": "CPA-2025-118", "title": "스태프 회계사 (Staff)", "created_at": "2025-01-15"},
                {"id": 6, "name": "정다은", "email": "de.jung@hyean.com", "role": "auditor", "cpa_number": "CPA-2025-120", "title": "스태프 회계사 (Staff)", "created_at": "2025-02-01"}
            ]
            for s in fallback_seeds:
                u_email = s["email"]
                comp_dict = auditor_detail_map.get(u_email, {}).get("companies", {})
                assigned_companies_list = []
                for comp_data in comp_dict.values():
                    assigned_companies_list.append({
                        "company_name": comp_data["company_name"],
                        "fiscal_year": comp_data["fiscal_year"],
                        "status": comp_data["status"],
                        "role": comp_data["role"],
                        "procedure_count": len(comp_data["procedures"]),
                        "procedures": comp_data["procedures"]
                    })
                auditors.append({
                    "id": s["id"],
                    "name": s["name"],
                    "email": u_email,
                    "company": "회계법인 혜안",
                    "role": s["role"],
                    "task_type": "회계감사",
                    "cpa_number": s["cpa_number"],
                    "title": s["title"],
                    "created_at": s["created_at"],
                    "assigned_count": len(assigned_companies_list),
                    "assigned_companies": assigned_companies_list
                })

        # 캐시 저장
        _auditor_pool_cache = auditors
        _auditor_pool_cache_time = now

        logger.info("[AUDITOR_POOL:RES] Returned %d auditors in pool", len(auditors))
        return jsonify({"success": True, "count": len(auditors), "auditors": auditors, "cached": False})
    except Exception as err:
        logger.error("[AUDITOR_POOL:ERR] Unexpected error in get_auditor_pool_api: %s", err, exc_info=True)
        fallback_auditors = [
            {"id": 1, "name": "김동선", "email": "cpaeastsun@gmail.com", "company": "회계법인 혜안", "role": "master", "task_type": "회계감사", "cpa_number": "CPA-2024-001", "title": "대표/품질관리실장 (CPA)", "created_at": "2024-01-01", "assigned_count": 2, "assigned_companies": []},
            {"id": 2, "name": "김동선(CPA)", "email": "cpaeastsun@naver.com", "company": "회계법인 혜안", "role": "cpa", "task_type": "회계감사", "cpa_number": "CPA-2024-002", "title": "시니어 공인회계사 (CPA)", "created_at": "2024-03-01", "assigned_count": 1, "assigned_companies": []},
            {"id": 3, "name": "이진우", "email": "jw.lee@hyean.com", "company": "회계법인 혜안", "role": "cpa", "task_type": "회계감사", "cpa_number": "CPA-2020-045", "title": "업무수행이사 (Partner)", "created_at": "2024-01-15", "assigned_count": 1, "assigned_companies": []}
        ]
        return jsonify({"success": True, "count": len(fallback_auditors), "auditors": fallback_auditors, "fallback": True})


@audit_bp.route('/api/audit/auditor-workload/<email>', methods=['GET'])
def get_auditor_workload_detail_api(email):
    """
    [고도화 2] 개별 감사인별 상세 수임사 및 배정 절차 목록 단일 조회 API
    """
    logger.info("[AUDITOR_WORKLOAD:REQ] GET /api/audit/auditor-workload/%s", email)
    try:
        assignments = load_assignments_data() or []
        proc_lookup = {p.get('account_code'): p for p in K_GAAP_STANDARD_PROCEDURES}
        
        matched_companies = []
        for a in assignments:
            cname = a.get('company_name', '')
            fyear = int(a.get('fiscal_year', 2025))
            st_label = a.get('status_label', '진행중')
            
            is_in_charge = (a.get('in_charge_email') == email)
            is_member = any(m.get('email') == email for m in a.get('members', []))
            
            acc_assigns = a.get('account_assignments') or {}
            my_procedures = []
            for code, assignee_em in acc_assigns.items():
                if assignee_em == email:
                    p_info = proc_lookup.get(code, {})
                    my_procedures.append({
                        "code": code,
                        "name": p_info.get("account_name", f"감사절차 {code}"),
                        "section_code": p_info.get("section_code", "4000"),
                        "section_name": p_info.get("section_name", "계정별 입증감사절차")
                    })
                    
            if is_in_charge or is_member or my_procedures:
                role = "주임 감사인 (In-charge)" if is_in_charge else ("담당 감사인 (Member)" if is_member else "절차 배정")
                matched_companies.append({
                    "company_name": cname,
                    "fiscal_year": fyear,
                    "status": st_label,
                    "role": role,
                    "procedure_count": len(my_procedures),
                    "procedures": my_procedures
                })
                
        logger.info("[AUDITOR_WORKLOAD:RES] Matched %d companies for %s", len(matched_companies), email)
        return jsonify({
            "success": True,
            "email": email,
            "company_count": len(matched_companies),
            "companies": matched_companies
        })
    except Exception as e:
        logger.error("[AUDITOR_WORKLOAD:ERR] Failed to load workload for %s: %s", email, e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@audit_bp.route('/api/audit/assignment-summary', methods=['GET'])
def get_assignment_summary_api():
    """
    [고도화 2] 마스터 포털용 감사 배정 종합 통계 및 감사인별 Workload 요약 API
    """
    logger.info("[ASSIGN_SUMMARY:REQ] GET /api/audit/assignment-summary")
    try:
        assignments = load_assignments_data() or []
        
        # 1. 단계별 통계
        status_counts = {
            "planned": 0,       # 기획/계획
            "interim": 0,       # 사전/중간
            "in_progress": 0,   # 실증감사
            "final_review": 0,  # 감사완결/심리
            "completed": 0      # 보고서 발행
        }
        
        # 2. 감사인별 담당 수임사 매핑 (Workload)
        auditor_workload = {}
        
        for a in assignments:
            st = a.get('status', 'planned')
            if st in status_counts:
                status_counts[st] += 1
            else:
                status_counts['planned'] += 1
                
            in_charge_email = a.get('in_charge_email') or 'unknown'
            in_charge_name = a.get('in_charge_name') or in_charge_email.split('@')[0]
            
            if in_charge_email not in auditor_workload:
                auditor_workload[in_charge_email] = {
                    "name": in_charge_name,
                    "email": in_charge_email,
                    "in_charge_count": 0,
                    "member_count": 0,
                    "companies": []
                }
            auditor_workload[in_charge_email]["in_charge_count"] += 1
            auditor_workload[in_charge_email]["companies"].append({
                "company_name": a.get('company_name'),
                "role": "In-charge",
                "status": a.get('status_label', '진행중')
            })
            
            # 참여 감사인(Members) 집계
            for m in a.get('members', []):
                m_email = m.get('email')
                m_name = m.get('name') or m_email.split('@')[0]
                if m_email and m_email != in_charge_email:
                    if m_email not in auditor_workload:
                        auditor_workload[m_email] = {
                            "name": m_name,
                            "email": m_email,
                            "in_charge_count": 0,
                            "member_count": 0,
                            "companies": []
                        }
                    auditor_workload[m_email]["member_count"] += 1
                    auditor_workload[m_email]["companies"].append({
                        "company_name": a.get('company_name'),
                        "role": m.get('role', 'Staff CPA'),
                        "status": a.get('status_label', '진행중')
                    })
                    
        total_companies = len(assignments)
        in_progress_count = status_counts["in_progress"] + status_counts["interim"]
        
        summary = {
            "total_companies": total_companies,
            "in_progress_count": in_progress_count,
            "status_counts": status_counts,
            "total_auditors": len(auditor_workload),
            "workload": list(auditor_workload.values())
        }
        
        logger.info("[ASSIGN_SUMMARY:RES] total=%d, in_progress=%d, auditors=%d", 
                    total_companies, in_progress_count, len(auditor_workload))
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        logger.error("[ASSIGN_SUMMARY:ERR] Failed to compute summary: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# 6. DSD 감사보고서 자동화 4대 핵심 REST API 엔드포인트
# ==============================================================================

from core.dsd_manager import parse_dsd_file
from core.audit_engine import apply_audit_adjustments
from core.notes_generator import generate_all_k_gaap_notes
from core.dsd_builder import build_dsd_archive


@audit_bp.route('/api/audit/dsd/parse-prior', methods=['POST'])
def parse_prior_dsd_api():
    """
    [API 1] 전기 DSD 파일 업로드 또는 샘플 DSD ➔ 비교표시 재무제표 4종 및 주석 역추출 반환
    """
    logger.info("[API_REQ] POST /api/audit/dsd/parse-prior")
    try:
        if 'file' in request.files and request.files['file'].filename:
            uploaded_file = request.files['file']
            logger.info("[DSD_PARSE:REQ] Uploaded file: %s (%d bytes)", uploaded_file.filename, len(uploaded_file.read()))
            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
            parse_result = parse_dsd_file(file_bytes)
        else:
            data = request.get_json(silent=True) or {}
            sample_name = data.get('filename') or '(주)이노플로우_감사보고서_25.dsd'
            sample_path = os.path.join("uploads", "dsd", sample_name)
            logger.info("[DSD_PARSE:REQ] Using local sample file: %s", sample_path)
            
            if not os.path.exists(sample_path):
                logger.error("[DSD_PARSE:ERR] Sample file not found: %s", sample_path)
                return jsonify({"success": False, "error": f"파일을 찾을 수 없습니다: {sample_path}"}), 404
                
            parse_result = parse_dsd_file(sample_path)
            
        if not parse_result.get("success"):
            logger.error("[DSD_PARSE:ERR] DSD parse error: %s", parse_result.get("error"))
            return jsonify({"success": False, "error": parse_result.get("error")}), 400
            
        logger.info("[DSD_PARSE:RES] Parsed successfully: Company=%s, Notes=%d", 
                    parse_result.get("company_name"), parse_result.get("notes_count", 0))
        return jsonify({"success": True, "data": parse_result})

    except Exception as e:
        logger.error("[API_ERROR] parse_prior_dsd_api failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/aje/apply', methods=['POST'])
def apply_aje_api():
    """
    [API 2] 결산 수정분개(AJE) 목록 적용 ➔ 실시간 수정후 B/S, I/S 및 대차평형 재계산 반환
    """
    logger.info("[API_REQ] POST /api/audit/aje/apply")
    try:
        data = request.get_json() or {}
        raw_tb = data.get('raw_tb', [])
        adjustments = data.get('adjustments', [])
        
        logger.info("[AJE_API:REQ] Applying %d AJEs on %d raw TB rows", len(adjustments), len(raw_tb))
        
        result = apply_audit_adjustments(raw_tb_data=raw_tb, adjustments=adjustments)
        
        if not result.get("success"):
            logger.error("[AJE_API:ERR] Failed to apply AJEs: %s", result.get("error"))
            return jsonify({"success": False, "error": result.get("error")}), 400
            
        logger.info("[AJE_API:RES] Completed. Adj Net Income: %d, Diff: %d", 
                    result.get("adjusted_summary", {}).get("net_income", 0),
                    result.get("adjusted_summary", {}).get("balance_diff", 0))
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error("[API_ERROR] apply_aje_api failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/notes/generate', methods=['POST'])
def generate_notes_api():
    """
    [API 3] 원장 및 수정후 T/B 기반 K-GAAP 1~18번 주석 데이터 및 표 자동 집계 반환
    """
    logger.info("[API_REQ] POST /api/audit/notes/generate")
    try:
        data = request.get_json() or {}
        company_name = data.get('company_name', '주식회사 이노플로우')
        fiscal_year = int(data.get('fiscal_year', 2025))
        company_meta = data.get('company_meta') or {"company_name": company_name, "fiscal_year": fiscal_year}
        adjusted_tb_items = data.get('adjusted_tb', [])
        prior_dsd_notes = data.get('prior_notes', [])
        
        logger.info("[NOTES_API:REQ] Generating notes for company=%s, FY=%d", company_name, fiscal_year)
        
        notes_bundle = generate_all_k_gaap_notes(
            company_meta=company_meta,
            adjusted_tb_items=adjusted_tb_items,
            prior_dsd_notes=prior_dsd_notes
        )
        
        logger.info("[NOTES_API:RES] Generated %d K-GAAP notes", len(notes_bundle))
        return jsonify({"success": True, "notes_count": len(notes_bundle), "notes": notes_bundle})

    except Exception as e:
        logger.error("[API_ERROR] generate_notes_api failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@audit_bp.route('/api/audit/dsd/build-export', methods=['POST'])
def build_and_export_dsd_api():
    """
    [API 4] 최종 감사의견 + 재무제표 4종 + 주석 ➔ 금융감독원 DART 표준 .dsd 파일 스트리밍 다운로드
    """
    logger.info("[API_REQ] POST /api/audit/dsd/build-export")
    try:
        data = request.get_json() or {}
        company_name = data.get('company_name', '주식회사 이노플로우').strip()
        cik = data.get('cik', '01294846').strip()
        fiscal_year = int(data.get('fiscal_year', 2025))
        period = int(data.get('period', 15))
        opinion_text = data.get('opinion_text', '우리의 의견으로는 별첨된 재무제표는 일반기업회계기준에 따라 중요성의 관점에서 공정하게 표시하고 있습니다.')
        audit_firm = data.get('audit_firm', '회계법인 혜안')
        
        balance_sheet_data = data.get('balance_sheet_data', {})
        income_statement_data = data.get('income_statement_data', {})
        notes_data = data.get('notes_data', [])
        
        logger.info("[DSD_EXPORT:REQ] Packaging .dsd for %s (FY %d, Period %d)", company_name, fiscal_year, period)
        
        dsd_stream = build_dsd_archive(
            company_name=company_name,
            cik=cik,
            fiscal_year=fiscal_year,
            period=period,
            opinion_text=opinion_text,
            audit_firm=audit_firm,
            balance_sheet_data=balance_sheet_data,
            income_statement_data=income_statement_data,
            notes_data=notes_data
        )
        
        safe_company = company_name.replace(' ', '_')
        download_filename = f"{safe_company}_감사보고서_{period}.dsd"
        
        logger.info("[DSD_EXPORT:RES] Streaming .dsd download: %s (%d bytes)", download_filename, len(dsd_stream.getvalue()))
        return send_file(
            dsd_stream,
            mimetype="application/x-zip-compressed",
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        logger.error("[API_ERROR] build_and_export_dsd_api failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

