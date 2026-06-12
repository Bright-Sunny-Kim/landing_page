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
            response = supabase.table('users').select('*').neq('email', MASTER_EMAIL).order('created_at', desc=True).execute()
            partners = response.data
            stats['total_partners'] = len(partners)
            
            # 전체 파일 가져오기
            files_response = supabase.table('company_files').select('company_name, file_url, file_name, status').execute()
            all_files = files_response.data
            stats['total_files'] = len(all_files)
            stats['pending_tasks'] = sum(1 for f in all_files if f.get('status') == '대기중' or not f.get('status'))
            
            # 파트너별 업로드율 계산
            for p in partners:
                p_company = p.get('company')
                # 해당 회사의 파일 중 제출(url 있음) 또는 해당사항없음인 경우 카운트
                p_files = [f for f in all_files if f.get('company_name') == p_company]
                
                # 중복 제출을 고려하여, 최근 제출 기준으로 세려면 복잡하므로 
                # 단순히 완료/해당없음 건수를 16으로 나누어 비율 산정 (최대 100%)
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
        status = request.form.get(f'{field_name}_status', '미제출')
        file = request.files.get(field_name)
        
        # Determine the year folder
        if 'current' in field_name:
            year_folder = str(current_year)
        else:
            year_folder = str(prior_year)
            
        if status == '제출' and file and file.filename != '':
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
            timestamp = int(time.time())
            
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
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
