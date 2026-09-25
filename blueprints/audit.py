# -*- coding: utf-8 -*-
"""
Hyean AI 회계감사 전용 포털 블루프린트 (blueprints/audit.py)
참여 회계사(CPA / Auditor) 및 마스터 관리자 전용 독립 포털 라우트 및 REST API
"""
import os
import json
import logging
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
        
        logger.info("[ASSIGN:POST] Update assignment for company=%s, year=%d", company_name, fiscal_year)
        
        if not company_name:
            return jsonify({"success": False, "error": "회사명을 입력해주세요."}), 400
            
        try:
            assignments = load_assignments_data()
            found = False
            for idx, item in enumerate(assignments):
                if item.get('company_name') == company_name and int(item.get('fiscal_year', 0)) == fiscal_year:
                    # 업데이트
                    assignments[idx].update(payload)
                    found = True
                    break
            
            if not found:
                new_id = max([a.get('id', 0) for a in assignments] or [0]) + 1
                payload['id'] = new_id
                assignments.append(payload)
                
            save_assignments_data(assignments)
            logger.info("[ASSIGN:POST_SUCCESS] Saved assignment for %s", company_name)
            return jsonify({"success": True, "assignment": payload})
        except Exception as e:
            logger.error("[ASSIGN:POST_ERR] Failed to save assignment: %s", e, exc_info=True)
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

