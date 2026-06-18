import os
import re
import time
from datetime import timedelta
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
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

# UPLOAD_FOLDER = 'uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 마스터 관리자 이메일 상수 정의
MASTER_EMAIL = 'cpaeastsun@gmail.com'

# 환경 변수 로드 (.env)
load_dotenv()

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
            if not (company and username and task_type and password):
                return redirect(url_for('login_page', error='missing_fields'))
                
            hashed = generate_password_hash(password)
            supabase.table('users').insert({
                'email': email,
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
            if company and username and task_type:
                oauth_pwd = f"OAUTH:{provider}"
                supabase.table('users').insert({
                    'email': email,
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
        
    # 마스터 계정은 튕겨나가지 않고 모든 파트너사의 포털을 다 볼 수 있도록 허용
    if session['email'] == MASTER_EMAIL:
        success = request.args.get('success', 'false') == 'true'
        return render_template('company.html', 
                               company_name=company_name,
                               success=success)
        
    # 일반 파트너는 자기 회사 페이지가 아니면 첫 화면으로 튕김
    if session['company'] != company_name:
        return redirect(url_for('login_page'))
        
    success = request.args.get('success', 'false') == 'true'
    
    return render_template('company.html', 
                           company_name=company_name,
                           success=success)

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
                    # Public URL 생성 (문자열 반환)
                    public_url = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                    f['public_url'] = public_url
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
    help_text = request.form.get('help_text', '').strip()
    
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
        'other_current': '기타 증빙(당연도)',
        'other_prior': '기타 증빙(전년도)'
    }
    
    import datetime
    current_year = datetime.datetime.now().year
    prior_year = current_year - 1

    uploaded_files_data = []
    
    for field_name, label in document_labels.items():
        status = request.form.get(f'{field_name}_status', '제출')
        files = request.files.getlist(field_name)

        # Determine the year folder
        if 'current' in field_name:
            year_folder = str(current_year)
        else:
            year_folder = str(prior_year)

        if status == '제출' and len(files) > 0 and files[0].filename != '':
            for file in files:
                if file.filename != '':
                    uploaded_files_data.append((field_name, label, file, status, year_folder))
        elif status in ['미제출', '해당사항없음']:
            # DB entry only
            uploaded_files_data.append((field_name, label, None, status, year_folder))
    if not help_text and not uploaded_files_data:
        return jsonify({'error': '문의 사항을 작성하거나 1개 이상의 감사 증빙을 처리해주세요.'}), 400
        
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
            
            if supabase:
                try:
                    supabase.storage.from_('company-uploads').upload(
                        file_path, 
                        file_bytes,
                        file_options={"content-type": file.content_type}
                    )
                    file_url = file_path
                except Exception as e:
                    print(f"Storage upload error for {field_name}: {e}")
            
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
        return jsonify({'error': '서버의 AI 설정이 올바르지 않습니다.'}), 500

    data = request.get_json() or {}
    question = data.get('question', '').strip()
    category = data.get('category', '전체')

    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    try:
        # 1. 질문 임베딩 생성 (text-embedding-3-large, 1536 dims)
        embed_response = openai_client.embeddings.create(
            input=question,
            model="text-embedding-3-large",
            dimensions=1536
        )
        query_embedding = embed_response.data[0].embedding

        # 2. Supabase에서 유사 조항 검색 (HNSW)
        rpc_params = {
            'query_embedding': query_embedding,
            'match_threshold': 0.3,
            'match_count': 5,
            'filter_category': None
        }
        
        # '전체'가 아닌 특정 카테고리가 선택되었다면 필터 파라미터 추가
        if category and category != '전체':
            rpc_params['filter_category'] = category

        search_res = supabase.rpc('match_document_chunks', rpc_params).execute()
        chunks = search_res.data if search_res.data else []

        # 3. 컨텍스트 구성
        if not chunks:
            context_text = "관련된 회계기준/감사기준을 찾을 수 없습니다."
            sources = []
        else:
            context_pieces = []
            sources = []
            for idx, c in enumerate(chunks):
                doc_id = c.get('document_id', '알수없음')
                art_name = c.get('article_name', '')
                chunk_txt = c.get('chunk_text', '')
                cat = c.get('category', '')
                
                source_label = f"[{cat}] {doc_id} {art_name}"
                if source_label not in sources:
                    sources.append(source_label)
                
                context_pieces.append(f"[{idx+1}] {source_label}\n{chunk_txt}")
            
            context_text = "\n\n".join(context_pieces)

        # 4. OpenAI ChatCompletion 호출
        system_prompt = (
            "당신은 '회계법인 혜안'의 최고 수준 공인회계사(CPA)이자 친절한 AI 회계감사 어시스턴트입니다.\n"
            "사용자의 질문에 대해 주어진 [참조 기준서 조항]을 바탕으로 전문가적이고 이해하기 쉽게 설명해 주세요.\n"
            "단순히 조문을 복사하는 것에 그치지 않고, 그 조항의 의미와 실무적 적용 방법을 풀어서 해석해 주어야 합니다.\n"
            "답변 작성 시 반드시 다음 포맷(마크다운 형식)을 사용하여 시각적으로 명확하게 구분해 주세요:\n\n"
            "### [결론]\n(여기에 질문에 대한 명확한 핵심 답변을 요약)\n\n"
            "### [상세 설명]\n(여기에 결론에 대한 구체적인 이유, 실무적 적용 방법, 해석 등을 상세히 작성)\n\n"
            "### [관련 근거(조항)]\n(여기에 참조한 기준서 카테고리, 문서명, 조항 번호 및 주요 원문 요약)\n\n"
            "만약 참조 기준서에 관련된 내용이 전혀 없다면, '제공된 기준서 내에서는 정확한 규정을 찾을 수 없습니다.'라고 솔직히 안내하세요."
        )

        user_prompt = (
            f"[사용자 질문]\n{question}\n\n"
            f"[참조 기준서 조항 (RAG Context)]\n{context_text}"
        )

        chat_resp = openai_client.chat.completions.create(
            model="gpt-4o-mini", # 비용 효율적인 빠른 모델 사용
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4
        )

        answer = chat_resp.choices[0].message.content

        return jsonify({
            'answer': answer,
            'sources': sources
        })

    except Exception as e:
        print(f"FAQ Ask error: {e}")
        return jsonify({'error': '질의 처리 중 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    app.run(debug=True, host='0.0.0.0', port=5000)