# -*- coding: utf-8 -*-
import os
import re
import time
import logging
from datetime import timedelta
from flask import Flask, request, render_template, redirect, url_for, session, jsonify

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import OpenAI
from audit_engine import parse_tb_file, run_variance_analysis, retrieve_k_gaap, generate_working_paper

def get_safe_path_name(name):
    # 경로 위험 문자를 제거하되, 한글/영문/숫자 문자는 보존
    cleaned = re.sub(r'[\x00\\/:*?"<>|]', '', name).strip()
    return cleaned if cleaned else "unknown"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# 세션 유지 시간 기본 설정 (30일)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

@app.after_request
def add_header(response):
    # 뒤로가기 캐시 방지 (로그아웃 후 뒤로가기로 이전 페이지 접근 불가하도록 설정)
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

# UPLOAD_FOLDER = 'uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 마스터 관리자 이메일 상수 정의
MASTER_EMAIL = 'cpaeastsun@gmail.com'

# 환경 변수 로드 (.env)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Supabase 초기화
url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_KEY", "")

# 클라이언트 객체는 URL과 KEY가 있을 때만 생성
if url and key and url != "YOUR_SUPABASE_PROJECT_URL_HERE":
    supabase: Client = create_client(url, key)
else:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY is missing in .env")
    supabase = None

# OpenAI 초기화
openai_api_key = os.getenv("OPENAI_API_KEY", "")
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)
else:
    print("WARNING: OPENAI_API_KEY is missing in .env")
    openai_client = None

# Boto3 MinIO 초기화
import boto3
from botocore.exceptions import ClientError
minio_endpoint = os.getenv("MINIO_ENDPOINT", "https://s3.hyean-dskim.com")
minio_access_key = os.getenv("MINIO_ACCESS_KEY", "")
minio_secret_key = os.getenv("MINIO_SECRET_KEY", "")

if minio_access_key and minio_secret_key:
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        region_name='us-east-1' # required for boto3 although unused in minio
    )
else:
    print("WARNING: MINIO credentials missing in .env")
    s3_client = None


@app.route('/')
def index():
    if 'email' in session:
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master_page'))
        return redirect(url_for('company_page', company_name=session['company']))
    
    return render_template('intro.html')

@app.route('/intro')
def intro():
    return render_template('intro.html')

@app.route('/login_page')
def login_page():
    if 'email' in session:
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master_page'))
        return redirect(url_for('company_page', company_name=session['company']))
    
    error = request.args.get('error', '')
    return render_template('login.html', error=error)

@app.route('/profile')
def profile():
    return render_template('profile.html')

# 비동기 이메일 체크 API
@app.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'exists': False})
        
    # 마스터 이메일인 경우 무조건 가입된 것으로 판단하여 패스시킴
    if email == MASTER_EMAIL:
        if supabase:
            try:
                response = supabase.table('users').select('*').eq('email', MASTER_EMAIL).execute()
                user = response.data[0] if response.data else None
                if user:
                    has_password = bool(user.get('password'))
                    return jsonify({'exists': True, 'has_password': has_password})
            except Exception as e:
                print(f"Master check-email database error: {e}")
        return jsonify({'exists': True, 'has_password': False})
        
    if not supabase:
        return jsonify({'exists': False, 'error': 'Supabase not configured'})

    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            has_password = bool(user.get('password'))
            return jsonify({'exists': True, 'has_password': has_password})
    except Exception as e:
        print(f"Check email error: {e}")
        return jsonify({'exists': False, 'error': str(e)})
        
    return jsonify({'exists': False})

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    corporate_number = request.form.get('corporate_number', '').strip()
    company = request.form.get('company', '').strip()
    username = request.form.get('username', '').strip()
    task_type = request.form.get('task_type', '')
    remember = request.form.get('remember') == 'on'
    
    if not email or not supabase:
        return redirect(url_for('login_page', error='missing_fields'))
        
    try:
        # 로그인 유지 여부 쿠키 기한 조정
        if remember:
            session.permanent = True
        else:
            session.permanent = False
            
        # 마스터 계정 처리
        if email == MASTER_EMAIL:
            response = supabase.table('users').select('*').eq('email', email).execute()
            user = response.data[0] if response.data else None
            
            if user:
                user_password = user.get('password')
                if user_password:
                    # 비밀번호 해시 형태 확인
                    is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                    if is_hashed:
                        if not check_password_hash(user_password, password):
                            return redirect(url_for('login_page', error='invalid_password'))
                    else:
                        # 평문 비밀번호 검증 (예: '0000')
                        if user_password != password:
                            return redirect(url_for('login_page', error='invalid_password'))
                        # 로그인 성공 시 보안을 위해 해시로 자동 마이그레이션
                        try:
                            hashed = generate_password_hash(password)
                            supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                        except Exception as migration_err:
                            print(f"Failed to migrate master password to hash: {migration_err}")
                else:
                    # 마스터 비밀번호 등록이 없는 경우 첫 로그인 시 자동 생성
                    if not password:
                        return redirect(url_for('login_page', error='missing_password'))
                    hashed = generate_password_hash(password)
                    supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
                session['email'] = user['email']
                session['company'] = user.get('company', '회계법인 혜안')
                session['username'] = user.get('username', '마스터관리자')
                session['task_type'] = user.get('task_type', '기타')
            else:
                # 최초 가동 등으로 DB에 마스터 계정이 없을 시 자동 등록
                if not password:
                    return redirect(url_for('login_page', error='missing_password'))
                hashed = generate_password_hash(password)
                supabase.table('users').insert({
                    'email': MASTER_EMAIL, 
                    'company': '회계법인 혜안', 
                    'username': '마스터관리자', 
                    'task_type': '기타',
                    'password': hashed
                }).execute()
                
                session['email'] = MASTER_EMAIL
                session['company'] = '회계법인 혜안'
                session['username'] = '마스터관리자'
                session['task_type'] = '기타'
                
            return redirect(url_for('master_page'))
            
        # 일반 계정 처리
        response = supabase.table('users').select('*').eq('email', email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            # 1) 기존 회원
            user_password = user.get('password')
            if user_password:
                # 소셜 가입 회원인 경우 소셜로만 로그인 제한
                if user_password.startswith('OAUTH:'):
                    provider = user_password.split(':')[1].capitalize()
                    return redirect(url_for('login_page', error=f'social_only_{provider}'))
                    
                # 비밀번호 해시 형태 확인
                is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                if is_hashed:
                    if not check_password_hash(user_password, password):
                        return redirect(url_for('login_page', error='invalid_password'))
                else:
                    # 평문 비밀번호 검증 (예: 사용자가 DB에 직접 텍스트로 넣은 경우)
                    if user_password != password:
                        return redirect(url_for('login_page', error='invalid_password'))
                    # 성공 시 해시 자동 마이그레이션
                    try:
                        hashed = generate_password_hash(password)
                        supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                    except Exception as migration_err:
                        print(f"Failed to migrate user password to hash: {migration_err}")
            else:
                # 기존 회원 중 비밀번호가 아직 없는 유저: 이번에 입력한 비밀번호로 최초 등록(마이그레이션)
                if not password:
                    return redirect(url_for('login_page', error='missing_password'))
                hashed = generate_password_hash(password)
                supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
        else:
            # 2) 신규 회원 등록 및 로그인
            if not (corporate_number and company and username and task_type and password):
                return redirect(url_for('login_page', error='missing_fields'))
                
            import re
            if not re.match(r'^\d{6}-\d{7}$', corporate_number):
                # 에러 처리는 편의상 login_page에서 missing_fields와 같이 표시 가능하도록 설정
                return redirect(url_for('login_page', error='invalid_corp_num'))
                
            # 기존 동일 법인번호 존재 여부 체크 및 회사명 강제 동기화
            existing_corp = supabase.table('users').select('company').eq('corporate_number', corporate_number).execute()
            if existing_corp.data:
                company = existing_corp.data[0]['company']
                
            hashed = generate_password_hash(password)
            supabase.table('users').insert({
                'email': email,
                'corporate_number': corporate_number,
                'company': company,
                'username': username,
                'task_type': task_type,
                'password': hashed
            }).execute()
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
            session['task_type'] = task_type
            
    except Exception as e:
        print(f"Database error during login: {e}")
        return redirect(url_for('login_page', error='db_error'))
        
    return redirect(url_for('company_page', company_name=session['company']))

@app.route('/login/social', methods=['POST'])
def login_social():
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    provider = data.get('provider', '').strip() # 'google' or 'naver'
    corporate_number = data.get('corporate_number', '').strip()
    company = data.get('company', '').strip()
    username = data.get('username', '').strip()
    task_type = data.get('task_type', '').strip()
    remember = data.get('remember') == True
    
    if not email or not provider:
        return jsonify({'error': '이메일과 소셜 제공자 정보가 누락되었습니다.'}), 400
        
    try:
        if remember:
            session.permanent = True
        else:
            session.permanent = False
            
        # 해당 이메일로 이미 가입되었는지 확인
        response = supabase.table('users').select('*').eq('email', email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
            
            if email == MASTER_EMAIL:
                return jsonify({'success': True, 'redirect': url_for('master_page')})
                
            return jsonify({'success': True, 'redirect': url_for('company_page', company_name=session['company'])})
        else:
            # 신규 소셜 가입 정보가 다 넘어온 경우 바로 가입 승인
            if corporate_number and company and username and task_type:
                import re
                if not re.match(r'^\d{6}-\d{7}$', corporate_number):
                    return jsonify({'error': '법인등록번호는 000000-0000000 형식이어야 합니다.'}), 400
                    
                existing_corp = supabase.table('users').select('company').eq('corporate_number', corporate_number).execute()
                if existing_corp.data:
                    company = existing_corp.data[0]['company']
                    
                oauth_pwd = f"OAUTH:{provider}"
                supabase.table('users').insert({
                    'email': email,
                    'corporate_number': corporate_number,
                    'company': company,
                    'username': username,
                    'task_type': task_type,
                    'password': oauth_pwd
                }).execute()
                
                session['email'] = email
                session['company'] = company
                session['username'] = username
                session['task_type'] = task_type
                
                return jsonify({'success': True, 'redirect': url_for('company_page', company_name=session['company'])})
            else:
                # 가입 정보가 없을 경우, 추가 입력을 요구하는 응답 전달
                return jsonify({'need_registration': True, 'email': email})
                
    except Exception as e:
        print(f"Social login database error: {e}")
        return jsonify({'error': f'소셜 로그인 처리 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/company/<company_name>')
def company_page(company_name):
    if 'email' not in session:
        return redirect(url_for('login_page'))
        
    # 마스터 계정 처리
    if session['email'] == MASTER_EMAIL:
        pass # Allow access
    elif session['company'] != company_name:
        return redirect(url_for('login_page'))
        
    success = request.args.get('success', 'false') == 'true'
    
    document_labels = {
        'tb_current': '시산표(당연도)',
        'tb_prior': '시산표(전년도)',
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
    
    history_files = []
    missing_items = []
    progress = {'total': len(document_labels), 'submitted': 0, 'percent': 0}
    
    if supabase:
        try:
            res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=False).execute()
            history_files = res.data
            
            # Extract latest status for each label (iterating ascending so latest overrides)
            label_status = {}
            for f in history_files:
                help_text = f.get('help_text', '')
                if not help_text: continue
                import re as regex
                m = regex.search(r'\[(.*?)\] 상태: (.*)', help_text)
                if m:
                    label = m.group(1).strip()
                    status = m.group(2).split('\\n')[0].strip()
                    label_status[label] = status
            
            for key, label in document_labels.items():
                status = label_status.get(label, '미제출')
                if status in ['제출', '해당사항없음']:
                    progress['submitted'] += 1
                else:
                    cat = '기타'
                    if key.startswith('pfile_'): cat = 'P-File'
                    elif 'finance' in key or 'partner' in key: cat = '외부조회'
                    elif 'current' in key: cat = '서면(당기)'
                    elif 'prior' in key: cat = '서면(전기)'
                    missing_items.append({'category': cat, 'label': label})
                    
            if progress['total'] > 0:
                progress['percent'] = int((progress['submitted'] / progress['total']) * 100)
                
            # Re-order history files to descending for display
            history_files.reverse()
            for f in history_files:
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
                    
        except Exception as e:
            print(f"History error: {e}")
    
    return render_template('company.html', 
                           company_name=company_name,
                           success=success,
                           history_files=history_files,
                           missing_items=missing_items,
                           progress=progress)

@app.route('/master')
def master_page():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('login_page'))
    
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
            
            # 전체 파일 및 상태 통계 집계
            # 전체 파일 가져오기
            files_response = supabase.table('company_files').select('company_name, file_url, file_name, status').execute()
            all_files = files_response.data
            stats['total_files'] = len(all_files)
            stats['pending_tasks'] = sum(1 for f in all_files if f.get('status') == '대기중' or not f.get('status'))

            # 파트너별 업로드율 계산
            for p in partners:
                p_company = p.get('company')
                p_files = [f for f in all_files if f.get('company_name') == p_company]
                valid_count = sum(1 for f in p_files if f.get('file_url') or (f.get('file_name') and '해당사항없음' in f.get('file_name')))
                rate = int((valid_count / 16.0) * 100)
                if rate > 100: rate = 100
                p['upload_rate'] = rate
            
        except Exception as e:
            print(f"Master page error: {e}")
            
    return render_template('master.html', partners=partners, stats=stats)

@app.route('/master/<company_name>')
def master_detail(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('login_page'))
        
    company_info = None
    files = []
    
    if supabase:
        try:
            # 회사 기본 정보
            comp_res = supabase.table('users').select('*').eq('company', company_name).execute()
            if comp_res.data:
                company_info = comp_res.data[0]
            
            # 회사 업로드 파일 목록
            files_res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=True).execute()
            
            for f in files_res.data:
                file_url_path = f.get('file_url')
                if file_url_path:
                    if file_url_path.startswith('http'):
                        f['public_url'] = file_url_path
                    else:
                        # Fallback for old Supabase files
                        f['public_url'] = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                else:
                    f['public_url'] = '#'
                # 상태가 없으면 대기중으로 표시
                if not f.get('status'):
                    f['status'] = '대기중'
                files.append(f)
                
        except Exception as e:
            print(f"Master detail error: {e}")
            
    if not company_info:
        return redirect(url_for('master_page'))
        
    return render_template('master_detail.html', company_info=company_info, files=files)

@app.route('/update-status', methods=['POST'])
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
            print(f"Update status error: {e}")
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Supabase not configured'}), 500

@app.route('/submit-request', methods=['POST'])
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
        'tb_current': '시산표(당연도)',
        'tb_prior': '시산표(전년도)',
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
        
        # 외부조회
        'finance_inquiry': '외부조회(금융기관)',
        'partner_inquiry': '외부조회(거래처)',
        
        # P-File (회사기본사항)
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
    
    import datetime
    current_year = datetime.datetime.now().year
    prior_year = current_year - 1

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
    
            # 폴더 저장 규칙 반영
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
                # DB entry only
                uploaded_files_data.append((field_name, label, None, status, year_folder))
        
        # 폼 종류 확인 (pfile 인지 기본감사자료 인지)
    form_type = request.form.get('form_type', '')
    
    if not help_text and not uploaded_files_data:
        return jsonify({'error': '업로드할 파일을 선택하거나 문의 사항을 작성해 주세요.'}), 400
    for field_name, label, file, status, year_folder in uploaded_files_data:
        if status == '제출' and file:
            from werkzeug.utils import secure_filename
            import time
            original_filename = secure_filename(file.filename)
            if not original_filename:
                original_filename = "unnamed_file"
                
            db_filename = f"[{label}] {original_filename}"
            timestamp = int(time.time() * 1000) # Use ms to prevent conflicts for multiple files
            
            # 회사명/연도/파일명 구조로 변경
            file_path = f"{company}/{year_folder}/{timestamp}_{field_name}_{original_filename}"
            
            file_bytes = file.read()
            file_url = None
            
            if s3_client:
                try:
                    bucket_name = 'company-uploads'
                    # Ensure bucket exists (in production, bucket should be pre-created)
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=file_path,
                        Body=file_bytes,
                        ContentType=file.content_type
                    )
                    file_url = f"{minio_endpoint}/{bucket_name}/{file_path}"
                except Exception as e:
                    print(f"MinIO upload error for {field_name}: {e}")
            
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
                    print(f"DB insert error for {field_name}: {e}")
        else:
            # 미제출 / 해당사항없음
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
                    print(f"DB insert error for text-only request: {e}")
 
    return redirect(url_for('company_page', company_name=session['company'], success='true'))

@app.route('/master/audit-analyze/<string:company_name>', methods=['POST'])
def audit_analyze(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 1. 해당 회사가 올린 모든 파일 메타데이터 조회
        file_res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=True).execute()
        if not file_res.data:
            return jsonify({'error': '해당 회사가 업로드한 파일이 없습니다.'}), 404
            
        files_list = file_res.data
        df_list = []
        parsed_filenames = []
        
        # 2. 모든 파일 바이너리를 다운로드 및 순차 파싱
        for f_info in files_list:
            file_url = f_info.get('file_url')
            file_name = f_info.get('file_name', 'simulated.csv')
            
            file_bytes = None
            if file_url:
                try:
                    if file_url.startswith('http'):
                        # It's a MinIO URL, download via requests
                        import requests
                        res = requests.get(file_url)
                        if res.status_code == 200:
                            file_bytes = res.content
                        else:
                            raise Exception(f"Failed to fetch from MinIO, status: {res.status_code}")
                    else:
                        file_bytes = supabase.storage.from_('company-uploads').download(file_url)
                    
                    # 성공적으로 다운로드 한 경우에만 파싱
                    df_tb = parse_tb_file(file_bytes, file_name)
                    df_list.append(df_tb)
                    parsed_filenames.append(file_name)
                except Exception as download_err:
                    print(f"Storage download failed for {file_url}: {download_err}. Skipping this file.")
                    
        # 만약 실제 다운로드되어 파싱된 파일이 없을 경우 Fallback으로 모의 데이터 세팅
        if not df_list:
            df_tb = parse_tb_file(None, "fallback_simulated.csv")
            df_list.append(df_tb)
            parsed_filenames.append("Fallback Simulated T/B")
            
        # 3. 다중 T/B 데이터프레임 병합 및 취합
        from audit_engine import merge_multiple_tb_dfs
        df_integrated = merge_multiple_tb_dfs(df_list)
        
        # 4. 중요성 기준 및 변동성 분석 수행
        analysis_res = run_variance_analysis(df_integrated, performance_materiality=50000000.0)
        
        # 5. K-GAAP RAG 기준서 매칭 (리스크 신호 검색)
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
            
        # 6. 종합 감사조서(Working Paper) 마크다운 생성
        working_paper_md = generate_working_paper(company_name, analysis_res, combined_standards)
        
        # 7. 분석 결과를 구조화된 JSON으로 반환
        return jsonify({
            'success': True,
            'company_name': company_name,
            'analyzed_files': parsed_filenames,
            'performance_materiality': analysis_res['PerformanceMateriality'],
            'total_assets': analysis_res['TotalAssets'],
            'total_sales': analysis_res['TotalSales'],
            'outliers': analysis_res['Outliers'],
            'risk_signals': analysis_res['RiskSignals'],
            'matched_standards': combined_standards,
            'working_paper_md': working_paper_md
        })
        
    except Exception as e:
        print(f"Audit analysis api error: {e}")
        return jsonify({'error': f'종합 분석 수행 중 에러 발생: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ==========================================
# AI 회계기준 FAQ (RAG) 엔드포인트
# ==========================================
@app.route('/api/faq/ask', methods=['POST'])
def faq_ask():
    global openai_client, supabase
    
    # AI 설정 지연 로딩 방어 (환경변수 재확인)
    if not openai_client:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            
    if not supabase:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if url and key and url != "YOUR_SUPABASE_PROJECT_URL_HERE":
            from supabase import create_client
            supabase = create_client(url, key)

    if not openai_client or not supabase:
        missing = []
        if not openai_client: missing.append("openai")
        if not supabase: missing.append("supabase")
        return jsonify({'error': f'서버의 AI 설정이 올바르지 않습니다. (Missing: {", ".join(missing)})'}), 500

    data = request.get_json() or {}
    question = data.get('question', '').strip()
    category = data.get('category', '전체')

    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    try:
        conversation_id = data.get('conversation_id', '').strip()
        
        # --- 일상어/금칙어 사전 필터링 (Fast Cut-off) ---
        import json
        from flask import Response, stream_with_context
        
        clean_q = question.replace(" ", "").lower()
        trivial_keywords = ["안녕", "반가워", "고마워", "수고", "감사", "안뇽", "하이", "hello"]
        swear_keywords = ["시발", "씨발", "개새끼", "미친", "존나", "좆", "병신"]
        
        # 욕설 체크
        if any(w in clean_q for w in swear_keywords):
            def generate_trivial():
                msg = "올바른 언어를 사용해주세요. 저는 회계감사 기준에 대해 답변해 드리는 AI입니다."
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id})}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
            
        # 단순 인사 체크 (질문 길이가 짧은 경우에만 적용하여 정상적인 회계 질문이 필터링되지 않게 방어)
        if len(clean_q) <= 10 and any(w in clean_q for w in trivial_keywords):
            def generate_trivial():
                msg = "안녕하세요! 혜안 파트너스 회계감사 AI 어시스턴트입니다. 회계 기준이나 감사 기준에 대해 무엇이든 물어보세요!"
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id})}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
        # -----------------------------------------------
        
        logger.info(f"[FAQ Ask] Received question: {question}, category: {category}, conv_id: {conversation_id}")
        
        dify_api_key = os.environ.get("DIFY_API_KEY", "app-mIeCNphyBVBn6diJpnybnzdS")
        
        payload = {
            "inputs": {"category": category},
            "query": question,
            "response_mode": "streaming",
            "user": session.get("user_id", "web-user")
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        headers = {
            "Authorization": f"Bearer {dify_api_key}",
            "Content-Type": "application/json"
        }
        
        import requests
        from flask import Response, stream_with_context
        logger.info("[FAQ Ask] Forwarding streaming request to Dify API...")
        
        dify_response = requests.post("https://api.dify.ai/v1/chat-messages", json=payload, headers=headers, stream=True)
        
        if dify_response.status_code != 200:
            logger.error(f"[FAQ Ask] Dify API returned status {dify_response.status_code}: {dify_response.text}")
            return jsonify({'error': 'Dify AI 챗봇 연동 중 오류가 발생했습니다.'}), 500

        def generate():
            for line in dify_response.iter_lines():
                if line:
                    yield line + b'\n\n'
                    
        return Response(stream_with_context(generate()), content_type='text/event-stream')

    except Exception as e:
        logger.error(f"FAQ Ask error: {e}", exc_info=True)
        return jsonify({'error': '질의 처리 중 오류가 발생했습니다.'}), 500

# ==========================================
# Dify External Data Tool Retrieval API
# ==========================================
@app.route('/api/dify/retrieval', methods=['POST'])
def dify_retrieval():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    
    logger.info(f"[Dify Retrieval] Received query: {query}")
    
    if not query:
        logger.warning("[Dify Retrieval] Empty query received.")
        return jsonify({"records": []}), 200
        
    try:
        # 1. 임베딩
        logger.info("[Dify Retrieval] Generating embeddings for query...")
        embed_response = openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-large",
            dimensions=1536
        )
        query_embedding = embed_response.data[0].embedding
        logger.info("[Dify Retrieval] Embedding generated successfully.")
        
        # 2. ChromaDB 검색
        import chromadb
        host = os.environ.get("CHROMA_SERVER_HOST", "localhost")
        port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
        logger.info(f"[Dify Retrieval] Connecting to ChromaDB at {host}:{port}...")
        
        chroma_client = chromadb.HttpClient(host=host, port=port)
        collection = chroma_client.get_collection(name="document_chunks")
        
        # 넉넉하게 상위 30개를 추출
        n_results_target = 30
        logger.info(f"[Dify Retrieval] Querying top {n_results_target} results from collection...")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results_target
        )
        
        initial_records = []
        documents_for_rerank = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                distance = results['distances'][0][i]
                sim = 1.0 - distance
                
                if sim >= 0.10:
                    doc_name = metadata.get("document_name", "알수없음")
                    cat = metadata.get("category", "기타")
                    art_name = metadata.get("article_name", "")
                    
                    content = f"[{cat}] {doc_name} ({art_name})\n{document}"
                    initial_records.append({
                        "content": content,
                        "score": float(sim)
                    })
                    documents_for_rerank.append(content)
                    
            logger.info(f"[Dify Retrieval] Successfully retrieved {len(initial_records)} chunks for reranking.")
        else:
            logger.info("[Dify Retrieval] No matching results found in ChromaDB.")
            
        final_records = []
        if documents_for_rerank:
            import cohere
            cohere_api_key = os.environ.get("COHERE_API_KEY")
            if cohere_api_key:
                logger.info("[Dify Retrieval] Reranking results with Cohere...")
                try:
                    co_client = cohere.Client(cohere_api_key)
                    rerank_response = co_client.rerank(
                        model="rerank-multilingual-v3.0",
                        query=query,
                        documents=documents_for_rerank,
                        top_n=5
                    )
                    
                    for r_result in rerank_response.results:
                        idx = r_result.index
                        if r_result.relevance_score >= 0.3:
                            initial_records[idx]["score"] = r_result.relevance_score
                            final_records.append(initial_records[idx])
                            
                    logger.info(f"[Dify Retrieval] Reranking complete. Selected {len(final_records)} records.")
                except Exception as ce:
                    logger.error(f"[Dify Retrieval] Cohere Rerank failed: {ce}")
                    initial_records.sort(key=lambda x: x["score"], reverse=True)
                    final_records = initial_records[:5]
            else:
                logger.warning("[Dify Retrieval] No COHERE_API_KEY found, skipping rerank.")
                initial_records.sort(key=lambda x: x["score"], reverse=True)
                final_records = initial_records[:5]
            
        logger.info(f"[Dify Retrieval] Returning {len(final_records)} records.")
        return jsonify({"records": final_records}), 200
        
    except Exception as e:
        logger.error(f"[Dify Retrieval] Error: {e}", exc_info=True)
        return jsonify({"records": []}), 500

# ==========================================
# 금융기관 조회업무 신청 시스템 (External Inquiry API)
# ==========================================
import datetime

@app.route('/api/financial_institutions', methods=['GET'])
def get_financial_institutions():
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        res = supabase.table('financial_institutions').select('*').eq('is_active', True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inquiry/new', methods=['POST'])
def new_inquiry_request():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    client_id = session.get('email')
    company_name = data.get('company_name')
    fiscal_year = data.get('fiscal_year')
    institution_id = data.get('institution_id')
    inquiry_type = data.get('inquiry_type') # 'online' or 'paper'
    
    if not all([company_name, fiscal_year, institution_id, inquiry_type]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 1. 기관 정보 재조회 및 규칙 검증
        inst_res = supabase.table('financial_institutions').select('*').eq('id', institution_id).execute()
        if not inst_res.data:
            return jsonify({'error': 'Invalid institution_id'}), 400
        
        inst_data = inst_res.data[0]
        # 규칙 1: 온라인/서면 구분 강제화
        if inst_data['inquiry_type'] == 'online' and inquiry_type == 'paper':
            return jsonify({'error': 'This institution only supports online inquiry.'}), 400
            
        # 규칙 3: 신청번호 자동 생성 (INQ-YYYYMM-XXXX)
        now = datetime.datetime.now()
        prefix = f"INQ-{now.strftime('%Y%m')}-"
        # 가장 최근 번호 조회
        latest_res = supabase.table('inquiry_requests').select('request_no').ilike('request_no', f"{prefix}%").order('request_no', desc=True).limit(1).execute()
        
        new_seq = 1
        if latest_res.data:
            latest_no = latest_res.data[0]['request_no']
            new_seq = int(latest_no.split('-')[2]) + 1
            
        request_no = f"{prefix}{new_seq:04d}"
        
        # Insert request
        insert_data = {
            'request_no': request_no,
            'client_id': client_id,
            'company_name': company_name,
            'fiscal_year': int(fiscal_year),
            'institution_id': institution_id,
            'inquiry_type': inquiry_type,
            'status': 'submitted'
        }
        
        insert_res = supabase.table('inquiry_requests').insert(insert_data).execute()
        
        if not insert_res.data:
            return jsonify({'error': 'Failed to insert request'}), 500
            
        new_request_id = insert_res.data[0]['id']
        
        # Add to logs
        supabase.table('inquiry_status_logs').insert({
            'request_id': new_request_id,
            'status_from': 'draft',
            'status_to': 'submitted',
            'changed_by': client_id,
            'memo': '신청서 작성 완료'
        }).execute()
        
        # TODO: 규칙 5: 이메일 알림 자동 발송 (모의)
        print(f"[EMAIL MOCK] 신청 완료 메일 발송 -> 고객: {client_id}, 담당자: {MASTER_EMAIL}")
        
        return jsonify({'success': True, 'request_no': request_no})
        
    except Exception as e:
        print(f"New inquiry error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inquiry/status', methods=['GET'])
def get_inquiry_status():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 본인 회사(또는 email) 신청건 조회
        # 요구사항에는 client_id(FK)로 저장되지만 화면상 회사가 보임
        email = session.get('email')
        res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').eq('client_id', email).order('created_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inquiry/download_form/<int:request_id>', methods=['GET'])
def download_inquiry_form(request_id):
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 요청 정보 조회
        req_res = supabase.table('inquiry_requests').select('*, financial_institutions(form_type)').eq('id', request_id).execute()
        if not req_res.data:
            return jsonify({'error': 'Request not found'}), 404
            
        req_data = req_res.data[0]
        
        # 권한 확인 (본인 혹은 마스터)
        if session.get('email') != req_data['client_id'] and session.get('email') != MASTER_EMAIL:
            return jsonify({'error': 'Unauthorized'}), 401
            
        form_type = req_data['financial_institutions']['form_type']
        
        # 상태 업데이트 및 로그 남기기 (form_downloaded_at)
        now_str = datetime.datetime.now().isoformat()
        supabase.table('inquiry_requests').update({
            'form_downloaded_at': now_str
        }).eq('id', request_id).execute()
        
        # 로컬 파일 전달 (app/static/forms 경로 내)
        from flask import send_from_directory
        forms_dir = os.path.join(app.root_path, 'static', 'forms')
        
        # 폴더가 없으면 생성하고 빈 파일 만들기 (테스트용)
        if not os.path.exists(forms_dir):
            os.makedirs(forms_dir)
            
        # form_type에 따라 다른 파일 제공
        filename_map = {
            'bank': '금융기관조회서_은행용.docx',
            'insurance': '금융기관조회서_보험용.docx',
            'securities': '금융기관조회서_증권용.docx',
            'card': '금융기관조회서_카드용.docx',
            'other': '금융기관조회서_기타.docx'
        }
        
        filename = filename_map.get(form_type, '금융기관조회서_기타.docx')
        filepath = os.path.join(forms_dir, filename)
        
        # 빈 파일이 없으면 깡통 파일 생성
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write("이 파일은 양식 다운로드 테스트용 빈 파일입니다.")
        
        return send_from_directory(forms_dir, filename, as_attachment=True)
        
    except Exception as e:
        print(f"Download form error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/inquiry', methods=['GET'])
def get_all_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').order('created_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/inquiry/update_status', methods=['POST'])
def update_inquiry_status():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    request_id = data.get('request_id')
    new_status = data.get('status')
    mail_tracking_no = data.get('mail_tracking_no')
    notes = data.get('notes')
    
    if not request_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 기존 상태 조회
        req_res = supabase.table('inquiry_requests').select('*').eq('id', request_id).execute()
        if not req_res.data:
            return jsonify({'error': 'Request not found'}), 404
            
        old_status = req_res.data[0]['status']
        
        # 규칙 4: 상태 전환 순서 강제 (역방향 불가, cancelled 예외)
        status_order = {
            'draft': 0, 'submitted': 1, 'fee_pending': 2, 'fee_paid': 3,
            'form_downloaded': 4, 'mail_sent': 5, 'received': 6, 'completed': 7, 'cancelled': 99
        }
        
        if new_status != 'cancelled' and status_order.get(new_status, 0) < status_order.get(old_status, 0):
            return jsonify({'error': '역방향 상태 전환은 불가합니다.'}), 400
            
        update_data = {'status': new_status}
        now_str = datetime.datetime.now().isoformat()
        
        if new_status == 'fee_paid':
            update_data['fee_paid_at'] = now_str
        elif new_status == 'mail_sent':
            update_data['mail_sent_at'] = now_str
        elif new_status == 'received':
            update_data['received_at'] = now_str
        elif new_status == 'completed':
            update_data['completed_at'] = now_str
            
        if mail_tracking_no is not None:
            update_data['mail_tracking_no'] = mail_tracking_no
        if notes is not None:
            update_data['notes'] = notes
            
        supabase.table('inquiry_requests').update(update_data).eq('id', request_id).execute()
        
        # 이력 로그 생성
        supabase.table('inquiry_status_logs').insert({
            'request_id': request_id,
            'status_from': old_status,
            'status_to': new_status,
            'changed_by': session.get('email'),
            'memo': f"상태가 {new_status}로 변경되었습니다."
        }).execute()
        
        # TODO: 규칙 5: 상태 변경 시 고객 이메일 발송 (모의)
        print(f"[EMAIL MOCK] 상태 변경 알림 메일 발송 -> 고객: {req_res.data[0]['client_id']}, 변경상태: {new_status}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update inquiry status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/inquiry/logs/<int:request_id>', methods=['GET'])
def get_inquiry_logs(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        res = supabase.table('inquiry_status_logs').select('*').eq('request_id', request_id).order('changed_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 추가 라우트 ---
@app.route('/api/admin/inquiry/detail/<int:request_id>', methods=['PUT'])
def admin_update_inquiry_detail(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
    
    req_data = request.json
    updates = {}
    if 'mail_tracking_no' in req_data:
        updates['mail_tracking_no'] = req_data['mail_tracking_no']
    if 'notes' in req_data:
        updates['notes'] = req_data['notes']
        
    if updates:
        try:
            supabase.table('inquiry_requests').update(updates).eq('id', request_id).execute()
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    return jsonify({'success': True})

# --- ߰ :   ---
@app.route('/api/admin/inquiry/export', methods=['GET'])
def admin_export_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return "Unauthorized", 401
    
    res = supabase.table('inquiry_requests').select('request_no, company_name, fiscal_year, inquiry_type, status, fee_amount, mail_tracking_no, created_at, financial_institutions(institution_name)').execute()
    data = res.data
    
    import csv
    from io import StringIO
    from flask import Response
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ûȣ', 'ȸ', 'ؿ', '', 'ȸ', '', 'ȣ', 'û'])
    for d in data:
        bank_name = d['financial_institutions']['institution_name'] if d.get('financial_institutions') else ''
        cw.writerow([
            d.get('request_no'), d.get('company_name'), d.get('fiscal_year'),
            bank_name, d.get('inquiry_type'), d.get('status'),
            d.get('mail_tracking_no'), d.get('created_at')
        ])
    
    output = '\ufeff' + si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inquiry_export.csv"}
    )

# ==========================================
# 수수료 및 청구 관리 (문서 자동화) API
# ==========================================
@app.route('/api/billing/docs', methods=['GET'])
def get_billing_docs():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        res = supabase.table('documents').select('*').order('created_at', desc=True).execute()
        return jsonify({'data': res.data})
    except Exception as e:
        logger.error(f"Error fetching docs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/billing/docs', methods=['POST'])
def create_billing_doc():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        data = request.json
        doc_type = data.get('type')
        doc_number = data.get('doc_number')
        client_name = data.get('client_name')
        title = data.get('title')
        items = data.get('items', [])
        
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        # 총 금액 계산
        total_amount = sum(float(item.get('total_price', 0)) for item in items)
        
        # 문서 삽입
        doc_res = supabase.table('documents').insert({
            'type': doc_type,
            'doc_number': doc_number,
            'client_name': client_name,
            'title': title,
            'author_email': session['email'],
            'total_amount': total_amount,
            'status': 'draft'
        }).execute()
        
        if not doc_res.data:
            return jsonify({'error': 'Failed to insert document'}), 500
            
        doc_id = doc_res.data[0]['id']
        
        # 품목 삽입
        if items:
            for item in items:
                item['document_id'] = doc_id
                if 'id' in item:
                    del item['id']
            supabase.table('document_items').insert(items).execute()
            
        return jsonify({'success': True, 'doc_id': doc_id})
        
    except Exception as e:
        logger.error(f"Error creating doc: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/billing/docs/<doc_id>', methods=['GET'])
def get_billing_doc_detail(doc_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        doc_res = supabase.table('documents').select('*').eq('id', doc_id).execute()
        if not doc_res.data:
            return jsonify({'error': 'Document not found'}), 404
            
        doc = doc_res.data[0]
        items_res = supabase.table('document_items').select('*').eq('document_id', doc_id).execute()
        doc['items'] = items_res.data
        
        return jsonify({'data': doc})
    except Exception as e:
        logger.error(f"Error fetching doc detail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/billing/docs/<doc_id>', methods=['DELETE'])
def delete_billing_doc(doc_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        # document_items는 document의 FK CASCADE가 걸려있다면 자동 삭제되겠지만
        # 안전하게 수동으로 먼저 지워준다.
        supabase.table('document_items').delete().eq('document_id', doc_id).execute()
        res = supabase.table('documents').delete().eq('id', doc_id).execute()
        
        return jsonify({'success': True, 'deleted': res.data})
    except Exception as e:
        logger.error(f"Error deleting doc: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/print/docs/<doc_type>', methods=['GET'])
def print_document(doc_type):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return "Unauthorized", 403
        
    doc_id = request.args.get('id')
    if not doc_id:
        return "문서 ID가 없습니다.", 400
        
    try:
        if not supabase:
            return "Supabase not initialized", 500
            
        # 문서 기본 정보 가져오기
        doc_res = supabase.table('documents').select('*').eq('id', doc_id).execute()
        if not doc_res.data:
            return "문서를 찾을 수 없습니다.", 404
        doc_data = doc_res.data[0]
        
        # 문서 항목 리스트 가져오기
        items_res = supabase.table('document_items').select('*').eq('document_id', doc_id).execute()
        items_data = items_res.data
        
        # 템플릿 파일 매핑
        template_map = {
            'quote': 'doc_quote.html',
            'proposal': 'doc_proposal.html',
            'invoice': 'doc_invoice.html'
        }
        
        template_name = template_map.get(doc_type)
        if not template_name:
            return "잘못된 문서 종류입니다.", 400
            
        return render_template(template_name, doc=doc_data, items=items_data)
    except Exception as e:
        logger.error(f"Error rendering print doc: {e}")
        return str(e), 500

if __name__ == '__main__':
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    app.run(debug=True, host='0.0.0.0', port=5000)
