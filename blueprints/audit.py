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
    
    # 최고 관리자 또는 회계사/감사인 또는 회계감사 업무담당자 허용
    is_authorized = (
        user_email == MASTER_EMAIL or 
        user_role in ['master', 'cpa', 'auditor'] or 
        user_task == '회계감사'
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
    """감사 대상 고객사 목록 반환"""
    logger.info("[API_REQ] GET /api/audit/companies")
    try:
        if supabase:
            res = supabase.table('companies').select('id, company_name, corporate_number').execute()
            companies = res.data or []
        else:
            # Fallback 로컬 목록
            companies = [
                {"id": 1, "company_name": "(주)프레오", "corporate_number": "110111-1234567"},
                {"id": 2, "company_name": "(주)더존비즈온", "corporate_number": "110111-2345678"},
                {"id": 3, "company_name": "회계법인 혜안", "corporate_number": "110111-3456789"}
            ]
        logger.info("[API_RES] /api/audit/companies count=%d", len(companies))
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
# 5. 감사 프로젝트 & 담당 배정 API
# ==============================================================================

@audit_bp.route('/api/audit/projects', methods=['GET'])
def get_audit_projects():
    """사업연도별 감사 프로젝트 및 참여 배정 목록 조회"""
    logger.info("[ASSIGN_REQ] GET /api/audit/projects")
    try:
        # 모의 프로젝트 목록
        mock_projects = [
            {
                "id": 1,
                "company_name": "(주)프레오",
                "fiscal_year": 2025,
                "in_charge": "김동선 공인회계사",
                "engagement_partner": "이진우 파트너",
                "members": ["김동선", "박지민", "최영수"],
                "target_report_date": "2026-03-20",
                "status": "in_progress",
                "status_label": "실증감사 진행중"
            },
            {
                "id": 2,
                "company_name": "(주)더존비즈온",
                "fiscal_year": 2025,
                "in_charge": "이진우 공인회계사",
                "engagement_partner": "이진우 파트너",
                "members": ["이진우", "정다은"],
                "target_report_date": "2026-03-15",
                "status": "planned",
                "status_label": "기획/계획 단계"
            }
        ]
        return jsonify({"success": True, "projects": mock_projects})
    except Exception as e:
        logger.error("[ASSIGN_ERROR] Failed to fetch projects: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
