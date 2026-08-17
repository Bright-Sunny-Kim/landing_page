import os
import re
import json
import datetime
import requests
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from core.extensions import (
    supabase, s3_client, minio_endpoint, MASTER_EMAIL,
    NOTION_API_BASE_URL, NOTION_API_VERSION, NOTION_TODO_DATABASE_ID, logger
)
from core.audit_engine import (
    parse_tb_file, run_variance_analysis, retrieve_k_gaap, generate_working_paper,
    classify_source_file, parse_trial_balance_structured, parse_financial_statement,
    financial_statement_to_variance_input, build_standard_statements,
    run_comprehensive_enterprise_analysis
)
from core.storage_manager import storage_manager

master_bp = Blueprint('master', __name__)

@master_bp.route('/master')
def master_page():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('auth.login_page'))
    
    partners = []
    stats = {
        'total_partners': 0,
        'total_files': 0,
        'pending_tasks': 0
    }
    
    if supabase:
        try:
            response = supabase.table('users').select('*').neq('email', MASTER_EMAIL).order('created_at', desc=True).execute()
            partners = response.data
            stats['total_partners'] = len(partners)
            
            files_response = supabase.table('company_files').select('company_name, file_url, file_name, status').execute()
            all_files = files_response.data
            stats['total_files'] = len(all_files)
            stats['pending_tasks'] = sum(1 for f in all_files if f.get('status') == '대기중' or not f.get('status'))

            for p in partners:
                p_company = p.get('company')
                p_files = [f for f in all_files if f.get('company_name') == p_company]
                valid_count = sum(1 for f in p_files if f.get('file_url') or (f.get('file_name') and '해당사항없음' in f.get('file_name')))
                rate = int((valid_count / 16.0) * 100)
                if rate > 100: rate = 100
                p['upload_rate'] = rate
            
        except Exception as e:
            logger.exception("Master page error: %s", e)
            
    return render_template('master.html', partners=partners, stats=stats)


def _notion_plain_text(property_value):
    if not property_value:
        return ''

    property_type = property_value.get('type')
    value = property_value.get(property_type)
    if property_type in ('title', 'rich_text'):
        return ''.join(item.get('plain_text', '') for item in (value or []))
    if property_type in ('select', 'status'):
        return (value or {}).get('name', '')
    if property_type == 'multi_select':
        return ', '.join(item.get('name', '') for item in (value or []))
    if property_type in ('url', 'email', 'phone_number'):
        return value or ''
    if property_type == 'formula' and isinstance(value, dict):
        formula_type = value.get('type')
        return str(value.get(formula_type, '') or '')
    return str(value or '') if value is not None else ''


def _notion_checkbox(property_value):
    if not property_value:
        return False
    if property_value.get('type') == 'checkbox':
        return bool(property_value.get('checkbox'))
    return _notion_plain_text(property_value).strip().lower() in ('true', 'yes', '1', 'y')


def _normalize_notion_todo(page):
    properties = page.get('properties', {})
    date_value = properties.get('날짜', {}).get('date') or {}
    return {
        'id': page.get('id', ''),
        'title': _notion_plain_text(properties.get('일정과할일')) or '제목 없는 일정',
        'start': date_value.get('start'),
        'end': date_value.get('end'),
        'status': _notion_plain_text(properties.get('상태')),
        'category': _notion_plain_text(properties.get('세부내역')),
        'description': _notion_plain_text(properties.get('Description')),
        'important': _notion_checkbox(properties.get('중요')),
        'urgent': _notion_checkbox(properties.get('긴급')),
        'must_do': _notion_checkbox(properties.get('Must-DO')),
        'url': page.get('url', ''),
    }


def _query_notion_todos(start_date, end_date):
    token = os.getenv('NOTION_ACCESS_TOKEN', '').strip()
    database_id = os.getenv('NOTION_TODO_DATABASE_ID', NOTION_TODO_DATABASE_ID).strip()
    if not token:
        raise RuntimeError('NOTION_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.')
    if not database_id:
        raise RuntimeError('NOTION_TODO_DATABASE_ID 환경변수가 설정되지 않았습니다.')

    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': NOTION_API_VERSION,
        'Content-Type': 'application/json',
    }
    payload = {
        'page_size': 100,
        'filter': {
            'and': [
                {'property': '날짜', 'date': {'on_or_after': start_date}},
                {'property': '날짜', 'date': {'before': end_date}},
            ]
        },
        'sorts': [{'property': '날짜', 'direction': 'ascending'}],
    }
    pages = []
    while True:
        response = requests.post(
            f'{NOTION_API_BASE_URL}/databases/{database_id}/query',
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        pages.extend(data.get('results', []))
        if not data.get('has_more') or not data.get('next_cursor'):
            break
        payload['start_cursor'] = data['next_cursor']

    return [_normalize_notion_todo(page) for page in pages if page.get('properties', {}).get('날짜', {}).get('date')]


@master_bp.route('/api/master/calendar', methods=['GET'])
def master_calendar_api():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401

    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start_date) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', end_date):
        return jsonify({'error': 'start와 end는 YYYY-MM-DD 형식이어야 합니다.'}), 400
    if start_date >= end_date:
        return jsonify({'error': 'end는 start보다 이후 날짜여야 합니다.'}), 400

    logger.info('Notion calendar query started: start=%s end=%s', start_date, end_date)
    try:
        events = _query_notion_todos(start_date, end_date)
        logger.info('Notion calendar query completed: count=%d', len(events))
        return jsonify({'events': events, 'count': len(events)})
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 'unknown'
        logger.error('Notion API request failed: status=%s', status_code, exc_info=True)
        return jsonify({'error': 'Notion 일정 조회에 실패했습니다. 연동 권한과 DB 설정을 확인해 주세요.'}), 502
    except requests.RequestException:
        logger.error('Notion API network error', exc_info=True)
        return jsonify({'error': 'Notion API에 연결할 수 없습니다.'}), 502
    except RuntimeError as exc:
        logger.error('Notion calendar configuration error: %s', exc)
        return jsonify({'error': str(exc)}), 503
    except Exception:
        logger.error('Unexpected Notion calendar error', exc_info=True)
        return jsonify({'error': '일정 조회 중 예기치 않은 오류가 발생했습니다.'}), 500


@master_bp.route('/master/<company_name>')
def master_detail(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('auth.login_page'))
        
    company_info = None
    files = []
    
    if supabase:
        try:
            comp_res = supabase.table('users').select('*').eq('company', company_name).execute()
            if comp_res.data:
                company_info = comp_res.data[0]
            
            files_res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=True).execute()
            
            for f in files_res.data:
                file_url_path = f.get('file_url')
                if file_url_path:
                    if file_url_path.startswith('http'):
                        f['public_url'] = file_url_path
                    else:
                        f['public_url'] = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                else:
                    f['public_url'] = '#'
                if not f.get('status'):
                    f['status'] = '대기중'
                files.append(f)
                
        except Exception as e:
            logger.exception("Master detail error: %s", e)
            
    if not company_info:
        return redirect(url_for('master.master_page'))
        
    return render_template('master_detail.html', company_info=company_info, files=files)

@master_bp.route('/update-status', methods=['POST'])
def update_status():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    file_id = data.get('id')
    new_status = data.get('status')
    
    if not file_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400
        
    if supabase:
        try:
            supabase.table('company_files').update({'status': new_status}).eq('id', file_id).execute()
            return jsonify({'success': True})
        except Exception as e:
            logger.exception("Update status error: %s", e)
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Supabase not configured'}), 500

@master_bp.route('/submit-request', methods=['POST'])
def submit_request():
    if 'email' not in session:
        return jsonify({'error': '세션이 만료되었습니다. 다시 로그인해 주세요'}), 401
        
    email = session.get('email')
    company = session.get('company')
    
    industry = request.form.get('industry_select', '')
    acc_std = request.form.get('accounting_standard', '')
    raw_help_text = request.form.get('help_text', '').strip()
    
    industry_map = {
        'manufacturing': '제조업/도소매업',
        'finance': '금융/보험업',
        'it': 'IT/소프트웨어',
        'construction': '건설업'
    }
    acc_std_map = {
        'k-gaap': '일반기업회계기준 (K-GAAP)',
        'k-ifrs': '한국채택국제회계기준 (K-IFRS)'
    }
    
    help_text = f"[업종: {industry_map.get(industry, industry)}] [회계기준: {acc_std_map.get(acc_std, acc_std)}]\n"
    if raw_help_text:
        help_text += f"문의내용: {raw_help_text}"
    
    document_labels = {
        'tb_current': '합계잔액시산표(당연도)',
        'tb_prior': '합계잔액시산표(전년도)',
        'bs_current': '재무상태표(당연도)',
        'bs_prior': '재무상태표(전년도)',
        'is_current': '손익계산서(당연도)',
        'is_prior': '손익계산서(전년도)',
        'je_current': '분개장(당연도)',
        'je_prior': '분개장(전년도)',
        'gl_current': '계정별원장(당연도)',
        'gl_prior': '계정별원장(전년도)',
        'fa_current': '유형자산명세서(당연도)',
        'fa_prior': '유형자산명세서(전년도)',
        'vat_current': '부가가치세신고서(당연도)',
        'vat_prior': '부가가치세신고서(전년도)',
        'payroll_current': '급여대장(당연도)',
        'payroll_prior': '급여대장(전년도)',
        'withholding_current': '원천징수이행상황신고서(당연도)',
        'withholding_prior': '원천징수이행상황신고서(전년도)',
        'severance_current': '퇴직금추계액명세서(당연도)',
        'severance_prior': '퇴직금추계액명세서(전년도)',
        'inv_current': '재고자산수불부(당연도)',
        'inv_prior': '재고자산수불부(전년도)',
        'pinv_current': '재물조사 결과표(당연도)',
        'pinv_prior': '재물조사 결과표(전년도)',
        'fina_current': '금융자산명세서(당연도)',
        'fina_prior': '금융자산명세서(전년도)',
        'borr_current': '차입금명세서(당연도)',
        'borr_prior': '차입금명세서(전년도)',
        'risk_current': '위험관리보고서(당연도)',
        'risk_prior': '위험관리보고서(전년도)',
        'inta_current': '무형자산명세서(당연도)',
        'inta_prior': '무형자산명세서(전년도)',
        'proj_current': '프로젝트 진행률 명세(당연도)',
        'proj_prior': '프로젝트 진행률 명세(전년도)',
        'conc_current': '공사원가명세서(당연도)',
        'conc_prior': '공사원가명세서(전년도)',
        'cont_current': '도급계약서 및 진행률 산정표(당연도)',
        'cont_prior': '도급계약서 및 진행률 산정표(전년도)',
        'other_current': '기타 증빙(당연도)',
        'other_prior': '기타 증빙(전년도)',
        'finance_inquiry': '외부조회(금융기관)',
        'partner_inquiry': '외부조회(거래처)',
        'pfile_01': '[PBC-P-01] 최신 정관',
        'pfile_02': '[PBC-P-02] 법인 등기부등본',
        'pfile_03': '[PBC-P-03] 주주명부 및 특수관계자 지분 구조도',
        'pfile_04': '[PBC-P-04] 과거 3개년 주주총회 및 이사회 의사록 일체',
        'pfile_05': '[PBC-P-05] 전사 조직도 및 직무 권한·업무분장표',
        'pfile_06': '[PBC-P-06] 내부회계관리제도 설계 및 운영 기술서',
        'pfile_07': '[PBC-P-07] 주요 사규 및 위임전결 규정집',
        'pfile_08': '[PBC-P-08] ERP 및 회계 프로그램 시스템 사양서',
        'pfile_09': '[PBC-P-09] 장기 차입금 및 사채 발행 계약서 총괄표',
        'pfile_10': '[PBC-P-10] 주요 자산 리스 계약서 및 스케줄표',
        'pfile_11': '[PBC-P-11] 부동산 등기부등본 및 관련 계약서',
        'pfile_12': '[PBC-P-12] 국책과제 협약서 및 기술 이전 계약서',
        'pfile_13': '[PBC-P-13] 주주간 계약서 및 금융기관 담보·보증 제공 내역서',
        'pfile_14': '[PBC-P-14] 최근 3개년 법인세 신고서 및 세무조정계산서 일체',
        'pfile_15': '[PBC-P-15] 이월결손금 및 세액공제 이력 관리대장',
        'pfile_16': '[PBC-P-16] 과거 세무조사 결과통지서 및 조치 결과 보고서',
        'pfile_17': '[PBC-P-17] 최근 3개년 외부감사보고서'
    }

    uploaded_files_data = []

    single_category = request.form.get('category')
    if single_category:
        field_name = None
        if single_category == 'P-File': field_name = request.form.get('pfile_doc')
        elif single_category == 'Temp': field_name = request.form.get('written_doc')
        elif single_category == 'Ext_F': field_name = request.form.get('finance_doc')
        elif single_category == 'Ext_C': field_name = request.form.get('partner_doc')
        if field_name and field_name in document_labels:
            label = document_labels[field_name]
            files = request.files.getlist('file')
            if field_name.startswith('pfile_'): year_folder = 'P-File'
            elif 'finance' in field_name: year_folder = 'Ext_F'
            elif 'partner' in field_name: year_folder = 'Ext_C'
            elif 'current' in field_name: year_folder = 'Temp/Temp_P'
            else: year_folder = 'Temp/Temp_L'
            for file in files:
                if file.filename != '':
                    uploaded_files_data.append((field_name, label, file, '완료', year_folder))
    else:
        for field_name, label in document_labels.items():
            status = request.form.get(f'{field_name}_status', '제출')
            files = request.files.getlist(field_name)
    
            if field_name.startswith('pfile_'):
                year_folder = 'P-File'
            elif field_name == 'finance_inquiry':
                year_folder = 'Ext_F'
            elif field_name == 'partner_inquiry':
                year_folder = 'Ext_C'
            elif 'current' in field_name:
                year_folder = 'Temp/Temp_P'
            else:
                year_folder = 'Temp/Temp_L'
    
            if status == '제출' and len(files) > 0 and files[0].filename != '':
                for file in files:
                    if file.filename != '':
                        uploaded_files_data.append((field_name, label, file, status, year_folder))
            elif status in ['미제출', '해당사항없음']:
                uploaded_files_data.append((field_name, label, None, status, year_folder))
        
    if not help_text and not uploaded_files_data:
        return jsonify({'error': '업로드할 파일을 선택하거나 문의 사항을 작성해 주세요.'}), 400

    import time
    for field_name, label, file, status, year_folder in uploaded_files_data:
        if status == '제출' and file:
            original_filename = secure_filename(file.filename)
            if not original_filename:
                original_filename = "unnamed_file"
                
            db_filename = f"[{label}] {original_filename}"
            timestamp = int(time.time() * 1000)
            
            file_path = f"{company}/{year_folder}/{timestamp}_{field_name}_{original_filename}"
            
            file_bytes = file.read()
            file_url = None
            
            if s3_client:
                try:
                    bucket_name = 'company-uploads'
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=file_path,
                        Body=file_bytes,
                        ContentType=file.content_type
                    )
                    file_url = f"{minio_endpoint}/{bucket_name}/{file_path}"
                except Exception as e:
                    logger.exception("MinIO upload error for %s: %s", field_name, e)
            
            if supabase:
                try:
                    formatted_help = f"[{label}] 상태: 제출"
                    if help_text:
                        formatted_help += f"\n추가 메시지: {help_text}"
                        
                    supabase.table('company_files').insert({
                        'company_name': company,
                        'uploaded_by': email,
                        'file_name': db_filename,
                        'file_url': file_url,
                        'help_text': formatted_help
                    }).execute()
                except Exception as e:
                    logger.exception("DB insert error for %s: %s", field_name, e)
        else:
            if supabase:
                try:
                    formatted_help = f"[{label}] 상태: {status}"
                    if help_text:
                        formatted_help += f"\n추가 메시지: {help_text}"
                        
                    supabase.table('company_files').insert({
                        'company_name': company,
                        'uploaded_by': email,
                        'file_name': f"[{status}] {label}",
                        'file_url': None,
                        'help_text': formatted_help
                    }).execute()
                except Exception as e:
                    logger.exception("DB insert error for text-only request: %s", e)
 
    return redirect(url_for('pages.company_page', company_name=session['company'], success='true'))

def _run_audit_analysis(company_name, allow_simulated_fallback=True):
    if not supabase:
        return {'error': 'Supabase not configured'}, 500

    file_res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=True).execute()
    if not file_res.data:
        if allow_simulated_fallback:
            return {'error': '해당 회사가 업로드한 파일이 없습니다.'}, 404
        return {'success': False, 'error_code': 'NO_FILES', 'error': '아직 업로드한 자료가 없습니다.'}, 200

    files_list = file_res.data
    df_list = []
    parsed_filenames = []
    tb_frames = []
    bs_df, is_df = None, None

    for f_info in files_list:
        file_url = f_info.get('file_url')
        file_name = f_info.get('file_name', 'simulated.csv')

        file_bytes = None
        if file_url:
            try:
                if file_url.startswith('http'):
                    res = requests.get(file_url)
                    if res.status_code == 200:
                        file_bytes = res.content
                    else:
                        raise Exception(f"Failed to fetch from MinIO, status: {res.status_code}")
                else:
                    file_bytes = supabase.storage.from_('company-uploads').download(file_url)

                file_kind = classify_source_file(file_name)
                if file_kind == 'balance_sheet' and bs_df is None:
                    bs_df = parse_financial_statement(file_bytes, file_name)
                elif file_kind == 'income_statement' and is_df is None:
                    is_df = parse_financial_statement(file_bytes, file_name)
                elif file_kind == 'trial_balance':
                    tb_frames.append(parse_trial_balance_structured(file_bytes, file_name))
                else:
                    try:
                        tb_frames.append(parse_trial_balance_structured(file_bytes, file_name))
                    except Exception:
                        df_list.append(parse_tb_file(file_bytes, file_name))
                parsed_filenames.append(file_name)
            except Exception as download_err:
                logger.exception("Storage download failed for %s: %s", file_url, download_err)

    tb_df = None
    if tb_frames:
        tb_df = pd.concat(tb_frames, ignore_index=True) if len(tb_frames) > 1 else tb_frames[0]

    standard_statements = None
    if bs_df is not None and is_df is not None:
        df_integrated = financial_statement_to_variance_input(bs_df, is_df)
        if tb_df is not None:
            standard_statements = build_standard_statements(tb_df, bs_df, is_df)
    else:
        if tb_df is not None and not df_list:
            df_list.append(
                tb_df.rename(columns={'NetBalance': 'Current'})[['Account', 'Current']].assign(Prior=0.0)
            )
        if not df_list:
            if not allow_simulated_fallback:
                return {
                    'success': False, 'error_code': 'NO_DATA',
                    'error': '분석 가능한 재무 데이터를 아직 인식하지 못했습니다. 합계잔액시산표(또는 재무상태표/손익계산서)를 업로드해주세요.',
                }, 200
            df_tb = parse_tb_file(None, "fallback_simulated.csv")
            df_list.append(df_tb)
            parsed_filenames.append("Fallback Simulated T/B")

        from core.audit_engine import merge_multiple_tb_dfs
        df_integrated = merge_multiple_tb_dfs(df_list)

    analysis_res = run_variance_analysis(df_integrated, performance_materiality=50000000.0)

    combined_standards = []
    seen_para = set()

    for sig in analysis_res["RiskSignals"]:
        query = sig["K_GAAP_Query"]
        matched = retrieve_k_gaap(query, limit=2, supabase_client=supabase)
        for m in matched:
            para_key = f"{m.get('standard_no')}_{m.get('paragraph_no')}"
            if para_key not in seen_para:
                seen_para.add(para_key)
                combined_standards.append(m)

    if not combined_standards:
        combined_standards = retrieve_k_gaap("기본 기준", limit=2, supabase_client=supabase)

    working_paper_md = generate_working_paper(company_name, analysis_res, combined_standards)

    return {
        'success': True,
        'company_name': company_name,
        'analyzed_files': parsed_filenames,
        'performance_materiality': analysis_res['PerformanceMateriality'],
        'total_assets': analysis_res['TotalAssets'],
        'total_sales': analysis_res['TotalSales'],
        'outliers': analysis_res['Outliers'],
        'risk_signals': analysis_res['RiskSignals'],
        'matched_standards': combined_standards,
        'working_paper_md': working_paper_md,
        'standard_statements': standard_statements
    }, 200


@master_bp.route('/master/audit-analyze/<string:company_name>', methods=['POST'])
def audit_analyze(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        payload, status = _run_audit_analysis(company_name, allow_simulated_fallback=True)
        return jsonify(payload), status
    except Exception as e:
        logger.exception("Audit analysis api error: %s", e)
        return jsonify({'error': f'종합 분석 수행 중 에러 발생: {str(e)}'}), 500


@master_bp.route('/company/audit-analysis/<string:company_name>', methods=['GET'])
def company_audit_analysis(company_name):
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if session['email'] != MASTER_EMAIL and session.get('company') != company_name:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        payload, status = _run_audit_analysis(company_name, allow_simulated_fallback=False)
        return jsonify(payload), status
    except Exception as e:
        logger.exception("Company audit analysis api error: %s", e)
        return jsonify({'error': f'분석 수행 중 오류가 발생했습니다: {str(e)}'}), 500


def _resolve_company_id(company_name):
    user_res = supabase.table('users').select('corporate_number').eq('company', company_name).limit(1).execute()
    if not user_res.data or not user_res.data[0].get('corporate_number'):
        return None
    corp_no = user_res.data[0]['corporate_number']
    comp_res = supabase.table('companies').select('id').eq('corporate_number', corp_no).execute()
    if comp_res.data:
        return comp_res.data[0]['id']
    insert_res = supabase.table('companies').insert({'corporate_number': corp_no, 'company_name': company_name}).execute()
    return insert_res.data[0]['id']


@master_bp.route('/master/audit-working-paper/<string:company_name>/save', methods=['POST'])
def audit_working_paper_save(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401

    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        payload = request.get_json(force=True) or {}
        fiscal_year = payload.get('fiscal_year')
        analysis_result_json = payload.get('analysis_result_json')
        working_paper_md = payload.get('working_paper_md')

        if not fiscal_year or not analysis_result_json or not working_paper_md:
            return jsonify({'error': 'fiscal_year, analysis_result_json, working_paper_md는 필수입니다.'}), 400

        company_id = _resolve_company_id(company_name)
        if company_id is None:
            return jsonify({'error': '등록된 회사 정보를 찾을 수 없습니다.'}), 404

        version_res = supabase.table('audit_working_papers').select('version') \
            .eq('company_id', company_id).eq('fiscal_year', fiscal_year) \
            .order('version', desc=True).limit(1).execute()
        next_version = (version_res.data[0]['version'] + 1) if version_res.data else 1

        insert_res = supabase.table('audit_working_papers').insert({
            'company_id': company_id,
            'company_name': company_name,
            'fiscal_year': fiscal_year,
            'version': next_version,
            'status': 'draft',
            'analysis_result_json': analysis_result_json,
            'working_paper_md': working_paper_md,
            'created_by': session['email']
        }).execute()

        return jsonify({'success': True, 'paper': insert_res.data[0]})

    except Exception as e:
        logger.exception("Audit working paper save error: %s", e)
        return jsonify({'error': f'감사조서 저장 중 에러 발생: {str(e)}'}), 500


@master_bp.route('/master/audit-working-paper/<string:company_name>', methods=['GET'])
def audit_working_paper_list(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401

    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        company_id = _resolve_company_id(company_name)
        if company_id is None:
            return jsonify({'error': '등록된 회사 정보를 찾을 수 없습니다.'}), 404

        res = supabase.table('audit_working_papers') \
            .select('id, fiscal_year, version, status, created_at, reviewed_at, approved_at') \
            .eq('company_id', company_id) \
            .order('fiscal_year', desc=True).order('version', desc=True).execute()

        return jsonify({'success': True, 'papers': res.data})

    except Exception as e:
        logger.exception("Audit working paper list error: %s", e)
        return jsonify({'error': f'감사조서 이력 조회 중 에러 발생: {str(e)}'}), 500


@master_bp.route('/master/audit-working-paper/detail/<int:paper_id>', methods=['GET'])
def audit_working_paper_detail(paper_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401

    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        res = supabase.table('audit_working_papers').select('*').eq('id', paper_id).execute()
        if not res.data:
            return jsonify({'error': '해당 감사조서를 찾을 수 없습니다.'}), 404

        return jsonify({'success': True, 'paper': res.data[0]})

    except Exception as e:
        logger.exception("Audit working paper detail error: %s", e)
        return jsonify({'error': f'감사조서 상세 조회 중 에러 발생: {str(e)}'}), 500


AUDIT_WP_STATUS_TRANSITIONS = {
    'draft': 'reviewed',
    'reviewed': 'approved'
}


@master_bp.route('/master/audit-working-paper/<int:paper_id>/status', methods=['POST'])
def audit_working_paper_status(paper_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401

    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        data = request.get_json(force=True) or {}
        new_status = data.get('new_status')
        memo = data.get('memo')

        paper_res = supabase.table('audit_working_papers').select('status').eq('id', paper_id).execute()
        if not paper_res.data:
            return jsonify({'error': '해당 감사조서를 찾을 수 없습니다.'}), 404

        current_status = paper_res.data[0]['status']
        if AUDIT_WP_STATUS_TRANSITIONS.get(current_status) != new_status:
            return jsonify({'error': f"'{current_status}' 상태에서 '{new_status}'(으)로 전이할 수 없습니다."}), 400

        now_str = datetime.datetime.now().isoformat()
        update_data = {'status': new_status}
        if new_status == 'reviewed':
            update_data['reviewed_at'] = now_str
            update_data['reviewed_by'] = session['email']
        elif new_status == 'approved':
            update_data['approved_at'] = now_str
            update_data['approved_by'] = session['email']

        supabase.table('audit_working_papers').update(update_data).eq('id', paper_id).execute()

        supabase.table('audit_working_paper_logs').insert({
            'paper_id': paper_id,
            'status_from': current_status,
            'status_to': new_status,
            'changed_by': session['email'],
            'memo': memo
        }).execute()

        return jsonify({'success': True})

    except Exception as e:
        logger.exception("Audit working paper status update error: %s", e)
        return jsonify({'error': f'감사조서 상태 변경 중 에러 발생: {str(e)}'}), 500


@master_bp.route('/master/api/storage/status', methods=['GET'])
def master_storage_status():
    """
    현재 사내 로컬 보관함 및 사내 Ubuntu 서버 연결 상태 메타데이터를 반환합니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401
    return jsonify(storage_manager.get_storage_status()), 200


def save_financial_analysis_to_local_archive(company_name, fiscal_year, payload):
    """
    하이브리드 스토리지 어댑터를 통해 사내 로컬 보관함 및 사내 Ubuntu 서버에 동시 저장합니다.
    """
    return storage_manager.save_analysis(company_name, fiscal_year, payload)


@master_bp.route('/master/api/datasets/local-list/<string:company_name>', methods=['GET'])
def master_list_local_datasets(company_name):
    """
    사내 로컬 보관함 및 Ubuntu 서버에 저장된 과거 분석 데이터셋 목록을 통합 반환합니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    try:
        datasets = storage_manager.list_datasets(company_name)
        return jsonify({'success': True, 'company_name': company_name, 'datasets': datasets}), 200
    except Exception as e:
        logger.error("[MASTER_ANALYTICS:ERROR] 데이터셋 목록 조회 실패: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@master_bp.route('/master/api/datasets/local-load', methods=['GET'])
def master_load_local_dataset():
    """
    사내 로컬 또는 Ubuntu 서버에 보관된 과거 JSON 데이터를 0.01초 만에 즉시 불러옵니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    company_name = request.args.get('company_name', '').strip()
    filename = request.args.get('filename', '').strip()

    if not company_name or not filename:
        return jsonify({'error': 'company_name 및 filename 파라미터가 필요합니다.'}), 400

    try:
        payload = storage_manager.load_dataset(company_name, filename)
        logger.info("[MASTER_ANALYTICS:LOAD] 데이터셋 로드 성공: %s / %s", company_name, filename)
        return jsonify(payload), 200
    except FileNotFoundError as fe:
        return jsonify({'error': str(fe)}), 404
    except Exception as e:
        logger.error("[MASTER_ANALYTICS:ERROR] 데이터셋 로드 실패: %s", e, exc_info=True)
        return jsonify({'error': f'데이터 로드 실패: {str(e)}'}), 500


@master_bp.route('/master/api/analyze-direct', methods=['POST'])
def master_analyze_direct():
    """
    관리자가 엑셀(.xlsx, .xls) 또는 CSV 파일들을 직접 드래그앤드롭으로 업로드하여 원스톱 정밀 분석을 수행합니다.
    분석 완료 시 uploads/작업완료_보관함에 자동 영속화됩니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        logger.warning("[MASTER_ANALYTICS:REQUEST] 비인가 접근 차단: %s", session.get('email'))
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    company_name = request.form.get('company_name', '').strip() or '직접 분석 기업'
    fiscal_year = request.form.get('fiscal_year', '').strip()
    uploaded_files = request.files.getlist('files')

    if not uploaded_files or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
        logger.warning("[MASTER_ANALYTICS:REQUEST] 업로드된 파일 없음")
        return jsonify({'error': '분석할 엑셀/CSV 파일을 최소 1개 이상 업로드해 주세요.'}), 400

    logger.info("[MASTER_ANALYTICS:REQUEST] 직접 분석 요청 수신: company=%s, fiscal_year=%s, file_count=%d", 
                company_name, fiscal_year, len(uploaded_files))

    files_data_list = []
    for f in uploaded_files:
        if f and f.filename:
            raw_fname = os.path.basename(f.filename).strip()
            fname = re.sub(r'[\\/:*?"<>|]', '_', raw_fname) or f.filename
            content = f.read()
            files_data_list.append({
                'filename': fname,
                'content': content
            })

    try:
        payload = run_comprehensive_enterprise_analysis(
            company_name=company_name,
            files_data_list=files_data_list,
            fiscal_year=fiscal_year,
            supabase_client=supabase
        )
        
        # [Phase 3] 로컬 작업완료_보관함에 자동 영속화 저장
        save_res = save_financial_analysis_to_local_archive(company_name, fiscal_year, payload)
        payload["local_archive_info"] = save_res

        logger.info("[MASTER_ANALYTICS:SUCCESS] 직접 분석 완료: company=%s, files=%s", 
                    company_name, payload.get('analyzed_files'))
        return jsonify(payload), 200

    except Exception as e:
        logger.error("[MASTER_ANALYTICS:ERROR] 직접 분석 중 예외 발생: %s", e, exc_info=True)
        return jsonify({'error': f'기업 분석 수행 중 오류가 발생했습니다: {str(e)}'}), 500


@master_bp.route('/master/api/analyze-company/<string:company_name>', methods=['POST', 'GET'])
def master_analyze_company(company_name):
    """
    특정 고객사가 업로드한 기존 엑셀/CSV 파일들을 스토리지에서 조회하여 원클릭으로 정밀 분석합니다.
    분석 완료 시 uploads/작업완료_보관함에 자동 영속화됩니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        logger.warning("[MASTER_ANALYTICS:REQUEST] 비인가 접근 차단: %s", session.get('email'))
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    req_data = request.get_json(silent=True) or {}
    selected_ids = req_data.get('selected_file_ids') or []
    fiscal_year = req_data.get('fiscal_year') or request.args.get('fiscal_year', '').strip()
    
    logger.info("[MASTER_ANALYTICS:REQUEST] 고객사 분석 요청: company=%s, fiscal_year=%s, selected_ids=%s", 
                company_name, fiscal_year, selected_ids)

    files_data_list = []

    # 1. Supabase company_files 테이블 조회
    if supabase:
        try:
            query = supabase.table('company_files').select('*').eq('company_name', company_name)
            if selected_ids:
                query = query.in_('id', selected_ids)
            file_res = query.order('created_at', desc=True).execute()

            for f_info in (file_res.data or []):
                f_name = str(f_info.get('file_name') or '').strip()
                f_url = f_info.get('file_url')
                
                if not f_name or not any(f_name.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
                    continue

                f_bytes = None
                if f_url:
                    try:
                        if f_url.startswith('http'):
                            resp = requests.get(f_url, timeout=10)
                            if resp.status_code == 200:
                                f_bytes = resp.content
                        else:
                            f_bytes = supabase.storage.from_('company-uploads').download(f_url)
                    except Exception as down_err:
                        logger.warning("[MASTER_ANALYTICS:PARSE] 원격 스토리지 다운로드 실패 (%s): %s", f_url, down_err)

                if not f_bytes:
                    local_path = os.path.join(os.getcwd(), "uploads", company_name, f_name)
                    if os.path.exists(local_path):
                        with open(local_path, "rb") as lf:
                            f_bytes = lf.read()

                if f_bytes:
                    files_data_list.append({
                        'filename': f_name,
                        'content': f_bytes
                    })

        except Exception as se:
            logger.error("[MASTER_ANALYTICS:ERROR] Supabase 파일 메타데이터 조회 오류: %s", se, exc_info=True)

    # 2. 로컬 uploads/<company_name> 및 uploads/고객제시자료 폴더 추가 탐색
    if not files_data_list:
        candidate_dirs = [
            os.path.join(os.getcwd(), "uploads", company_name),
            os.path.join(os.getcwd(), "uploads", "고객제시자료")
        ]
        for cdir in candidate_dirs:
            if os.path.exists(cdir):
                for lf in os.listdir(cdir):
                    if any(lf.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
                        with open(os.path.join(cdir, lf), "rb") as f:
                            files_data_list.append({
                                'filename': lf,
                                'content': f.read()
                            })
                if files_data_list:
                    break

    if not files_data_list:
        logger.warning("[MASTER_ANALYTICS:REQUEST] 분석 가능한 회계 엑셀/CSV 파일 없음: company=%s", company_name)
        return jsonify({
            'success': False,
            'error_code': 'NO_EXCEL_FILES',
            'error': f"'{company_name}' 고객사가 업로드한 회계 파일(.xlsx, .xls, .csv)이 없습니다. 상단의 '파일 직접 업로드' 기능을 이용하거나 고객사 자료 업로드를 요청해 주세요."
        }), 404

    try:
        payload = run_comprehensive_enterprise_analysis(
            company_name=company_name,
            files_data_list=files_data_list,
            fiscal_year=fiscal_year,
            supabase_client=supabase
        )
        
        # [Phase 3] 로컬 작업완료_보관함에 자동 영속화 저장
        save_res = save_financial_analysis_to_local_archive(company_name, fiscal_year, payload)
        payload["local_archive_info"] = save_res

        logger.info("[MASTER_ANALYTICS:SUCCESS] 고객사 분석 완료: company=%s, files=%s", 
                    company_name, payload.get('analyzed_files'))
        return jsonify(payload), 200

    except Exception as e:
        logger.error("[MASTER_ANALYTICS:ERROR] 고객사 분석 중 예외 발생: %s", e, exc_info=True)
        return jsonify({'error': f'기업 분석 수행 중 오류가 발생했습니다: {str(e)}'}), 500


@master_bp.route('/master/api/save-analysis', methods=['POST'])
def master_save_analysis():
    """
    기업 분석 결과(JSON 지표 및 마크다운 조서)를 Supabase 및 uploads/작업완료_보관함 로컬 영속화합니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        logger.warning("[MASTER_ANALYTICS:REQUEST] 비인가 저장 요청 차단: %s", session.get('email'))
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    try:
        data = request.get_json(force=True) or {}
        company_name = data.get('company_name', '').strip() or '미지정 기업'
        fiscal_year = int(data.get('fiscal_year', 2025))
        analysis_payload = data.get('analysis_data', {})
        report_md = data.get('report_md', '') or analysis_payload.get('report_md', '')

        logger.info("[MASTER_ANALYTICS:REQUEST] 수동 저장 요청: company=%s, fiscal_year=%d", 
                    company_name, fiscal_year)

        saved_paper = None
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Supabase 영속화
        if supabase:
            try:
                company_id = _resolve_company_id(company_name) or 1
                version_res = supabase.table('audit_working_papers').select('version') \
                    .eq('company_id', company_id).eq('fiscal_year', fiscal_year) \
                    .order('version', desc=True).limit(1).execute()
                next_version = (version_res.data[0]['version'] + 1) if (version_res.data and len(version_res.data) > 0) else 1

                insert_res = supabase.table('audit_working_papers').insert({
                    'company_id': company_id,
                    'company_name': company_name,
                    'fiscal_year': fiscal_year,
                    'version': next_version,
                    'status': 'draft',
                    'analysis_result_json': analysis_payload,
                    'working_paper_md': report_md,
                    'created_by': session['email']
                }).execute()

                if insert_res.data:
                    saved_paper = insert_res.data[0]
                    logger.info("[MASTER_ANALYTICS:SUCCESS] Supabase 조서 저장 성공 (ID: %s, v%d)", 
                                saved_paper.get('id'), next_version)
            except Exception as se:
                logger.error("[MASTER_ANALYTICS:ERROR] Supabase 영속화 오류 (로컬 백업 진행): %s", se)

        # 2. [Phase 3] uploads/작업완료_보관함에 로컬 영속화 동기화 저장
        archive_res = save_financial_analysis_to_local_archive(company_name, fiscal_year, analysis_payload)

        return jsonify({
            'success': True,
            'message': f"'{company_name}' 기업의 {fiscal_year}년도 분석 데이터 및 조서가 로컬 보관함(uploads/작업완료_보관함)에 안전하게 저장되었습니다.",
            'saved_at': now_str,
            'archive_info': archive_res,
            'paper': saved_paper or {
                'company_name': company_name,
                'fiscal_year': fiscal_year,
                'version': 1,
                'status': 'saved',
                'created_at': now_str
            }
        }), 200

    except Exception as e:
        logger.error("[MASTER_ANALYTICS:ERROR] 분석 조서 저장 실패: %s", e, exc_info=True)
        return jsonify({'error': f'저장 처리 중 오류가 발생했습니다: {str(e)}'}), 500


@master_bp.route('/master/api/analysis-history/<string:company_name>', methods=['GET'])
def master_analysis_history(company_name):
    """
    특정 회사의 과거 저장된 감사/기업분석 보고서 이력 목록을 반환합니다.
    """
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 401

    logger.info("[MASTER_ANALYTICS:REQUEST] 기업분석 이력 조회: company=%s", company_name)
    history_list = []

    # 1. Supabase 조회
    if supabase:
        try:
            company_id = _resolve_company_id(company_name)
            if company_id:
                res = supabase.table('audit_working_papers') \
                    .select('id, company_name, fiscal_year, version, status, created_at, reviewed_at, approved_at') \
                    .eq('company_id', company_id) \
                    .order('created_at', desc=True).execute()
                history_list = res.data or []
        except Exception as se:
            logger.error("[MASTER_ANALYTICS:ERROR] Supabase 이력 조회 오류: %s", se)

    # 2. 로컬 백업 폴더 조회 보강
    backup_dir = os.path.join(os.getcwd(), "temporary_data", "saved_reports", company_name)
    if os.path.exists(backup_dir):
        for fname in os.listdir(backup_dir):
            if fname.endswith("_report.md"):
                ts_str = fname.replace("_report.md", "")
                history_list.append({
                    'id': f"local_{ts_str}",
                    'company_name': company_name,
                    'fiscal_year': ts_str.split('_')[0] if '_' in ts_str else '2025',
                    'version': 1,
                    'status': 'saved_local',
                    'created_at': ts_str
                })

    return jsonify({
        'success': True,
        'company_name': company_name,
        'count': len(history_list),
        'history': history_list
    }), 200



