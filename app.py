import os
import re
import time
from datetime import timedelta
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
from dotenv import load_dotenv
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

@app.route('/')
def index():
    if 'email' in session:
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master_page'))
        return redirect(url_for('company_page', company_name=session['company']))
    
    error = request.args.get('error', '')
    return render_template('login.html', error=error)

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
        return redirect(url_for('index', error='missing_fields'))
        
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
                            return redirect(url_for('index', error='invalid_password'))
                    else:
                        # 평문 비밀번호 검증 (예: '0000')
                        if user_password != password:
                            return redirect(url_for('index', error='invalid_password'))
                        # 로그인 성공 시 보안을 위해 해시로 자동 마이그레이션
                        try:
                            hashed = generate_password_hash(password)
                            supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                        except Exception as migration_err:
                            print(f"Failed to migrate master password to hash: {migration_err}")
                else:
                    # 마스터 비밀번호 등록이 없는 경우 첫 로그인 시 자동 생성
                    if not password:
                        return redirect(url_for('index', error='missing_password'))
                    hashed = generate_password_hash(password)
                    supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
                session['email'] = user['email']
                session['company'] = user.get('company', '회계법인 혜안')
                session['username'] = user.get('username', '마스터관리자')
                session['task_type'] = user.get('task_type', '기타')
            else:
                # 최초 가동 등으로 DB에 마스터 계정이 없을 시 자동 등록
                if not password:
                    return redirect(url_for('index', error='missing_password'))
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
                    return redirect(url_for('index', error=f'social_only_{provider}'))
                    
                # 비밀번호 해시 형태 확인
                is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                if is_hashed:
                    if not check_password_hash(user_password, password):
                        return redirect(url_for('index', error='invalid_password'))
                else:
                    # 평문 비밀번호 검증 (예: 사용자가 DB에 직접 텍스트로 넣은 경우)
                    if user_password != password:
                        return redirect(url_for('index', error='invalid_password'))
                    # 성공 시 해시 자동 마이그레이션
                    try:
                        hashed = generate_password_hash(password)
                        supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                    except Exception as migration_err:
                        print(f"Failed to migrate user password to hash: {migration_err}")
            else:
                # 기존 회원 중 비밀번호가 아직 없는 유저: 이번에 입력한 비밀번호로 최초 등록(마이그레이션)
                if not password:
                    return redirect(url_for('index', error='missing_password'))
                hashed = generate_password_hash(password)
                supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
        else:
            # 2) 신규 회원 등록 및 로그인
            if not (company and username and task_type and password):
                return redirect(url_for('index', error='missing_fields'))
                
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
        return redirect(url_for('index', error='db_error'))
        
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
        return redirect(url_for('index'))
        
    # 마스터 계정은 튕겨나가지 않고 모든 파트너사의 포털을 다 볼 수 있도록 허용
    if session['email'] == MASTER_EMAIL:
        success = request.args.get('success', 'false') == 'true'
        return render_template('company.html', 
                               company_name=company_name,
                               success=success)
        
    # 일반 파트너는 자기 회사 페이지가 아니면 첫 화면으로 튕김
    if session['company'] != company_name:
        return redirect(url_for('index'))
        
    success = request.args.get('success', 'false') == 'true'
    
    return render_template('company.html', 
                           company_name=company_name,
                           success=success)

@app.route('/master')
def master_page():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('index'))
    
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
            files_response = supabase.table('company_files').select('status').execute()
            all_files = files_response.data
            stats['total_files'] = len(all_files)
            stats['pending_tasks'] = sum(1 for f in all_files if f.get('status') == '대기중' or not f.get('status'))
            
        except Exception as e:
            print(f"Master page error: {e}")
            
    return render_template('master.html', partners=partners, stats=stats)

@app.route('/master/<company_name>')
def master_detail(company_name):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('index'))
        
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
        return jsonify({'error': '세션이 만료되었습니다. 다시 로그인해 주세요.'}), 401
        
    email = session.get('email')
    company = session.get('company')
    help_text = request.form.get('help_text', '').strip()
    file = request.files.get('file')
    
    is_file_empty = not file or file.filename == ''
    if not help_text and is_file_empty:
        return jsonify({'error': '문의 사항을 작성하거나 파일을 첨부해 주세요.'}), 400
        
    file_url = None
    filename_saved = None
    if not is_file_empty:
        # 파일명 생성 및 업로드 준비
        original_filename = secure_filename(file.filename)
        if not original_filename:
            original_filename = "unnamed_file"
        
        timestamp = int(time.time())
        # 폴더명에 한글이 들어가면 Supabase API(InvalidKey) 에러가 발생할 수 있으므로,
        # 항상 영문/숫자인 email을 안전하게 변환하여 폴더명으로 사용합니다.
        safe_email_folder = re.sub(r'[^a-zA-Z0-9]', '_', email)
        file_path = f"{safe_email_folder}/{timestamp}_{original_filename}"
        
        # 파일 내용을 바이트로 읽기
        file_bytes = file.read()
        
        if supabase:
            try:
                # 1. Supabase Storage에 파일 원본 업로드
                supabase.storage.from_('company-uploads').upload(
                    file_path, 
                    file_bytes,
                    file_options={"content-type": file.content_type}
                )
                file_url = file_path
                filename_saved = original_filename
            except Exception as e:
                print(f"Storage upload error: {e}")
        else:
            print("Supabase client is not configured. Storage upload skipped.")
            
    # 2. DB 테이블 (company_files)에 메타데이터 기록
    if supabase:
        try:
            supabase.table('company_files').insert({
                'company_name': company,
                'uploaded_by': email,
                'file_name': filename_saved,
                'file_url': file_url,
                'help_text': help_text
            }).execute()
        except Exception as e:
            print(f"DB insert error: {e}")

    return redirect(url_for('company_page', company_name=session['company'], success='true'))

@app.route('/master/audit-analyze/<int:file_id>', methods=['POST'])
def audit_analyze(file_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        # 1. 파일 메타데이터 조회
        file_res = supabase.table('company_files').select('*').eq('id', file_id).execute()
        if not file_res.data:
            return jsonify({'error': '해당 파일을 찾을 수 없습니다.'}), 404
            
        file_info = file_res.data[0]
        company_name = file_info.get('company_name', '알수없음')
        file_url = file_info.get('file_url')
        file_name = file_info.get('file_name', 'simulated.csv')
        
        file_bytes = None
        # 2. Supabase Storage에서 실제 파일 다운로드 시도
        if file_url:
            try:
                file_bytes = supabase.storage.from_('company-uploads').download(file_url)
            except Exception as download_err:
                print(f"Storage download failed for {file_url}: {download_err}. Proceeding with fallback simulated data.")
                
        # 3. 데이터 파싱
        df_tb = parse_tb_file(file_bytes, file_name)
        
        # 4. 중요성 기준 및 변동성 분석 수행
        # 기본 중요성은 자산총계에 따라 동적으로 설정(여기선 50,000,000원 기본값)
        analysis_res = run_variance_analysis(df_tb, performance_materiality=50000000.0)
        
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
            # 기본 매칭 제공
            combined_standards = retrieve_k_gaap("기본 기준", limit=2, supabase_client=supabase)
            
        # 6. 감사조서(Working Paper) 마크다운 생성
        working_paper_md = generate_working_paper(company_name, analysis_res, combined_standards)
        
        # 7. 분석 결과를 구조화된 JSON으로 반환
        return jsonify({
            'success': True,
            'company_name': company_name,
            'file_name': file_name,
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
        return jsonify({'error': f'분석 수행 중 에러 발생: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
