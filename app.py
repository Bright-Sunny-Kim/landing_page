import os
import re
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

def get_safe_path_name(name):
    # 경로 위험 문자를 제거하되, 한글/영문/숫자 문자는 보존
    cleaned = re.sub(r'[\x00\\/:*?"<>|]', '', name).strip()
    return cleaned if cleaned else "unknown"

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = 'database.db'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 마스터 관리자 이메일 상수 정의
MASTER_EMAIL = 'cpaeastsun@gmail.com'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL,
            username TEXT NOT NULL,
            task_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 앱 구동 시 데이터베이스 초기화
init_db()

@app.route('/')
def index():
    if 'email' in session:
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master_page'))
        return redirect(url_for('company_page', company_name=session['company']))
    return render_template('login.html')

# 비동기 이메일 체크 API
@app.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'exists': False})
        
    # 마스터 이메일인 경우 무조건 가입된 것으로 판단하여 패스시킴
    if email == MASTER_EMAIL:
        return jsonify({'exists': True})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({'exists': True})
    return jsonify({'exists': False})

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    company = request.form.get('company', '').strip()
    username = request.form.get('username', '').strip()
    task_type = request.form.get('task_type', '')
    
    if not email:
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 마스터 계정은 예외 처리
        if email == MASTER_EMAIL:
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if user:
                session['email'] = user['email']
                session['company'] = user['company']
                session['username'] = user['username']
                session['task_type'] = user['task_type']
            else:
                # 최초 가동 등으로 DB에 마스터 계정이 없을 시 자동 더미 등록 처리
                cursor.execute('''
                    INSERT INTO users (email, company, username, task_type) 
                    VALUES (?, ?, ?, ?)
                ''', (MASTER_EMAIL, '회계법인 혜안', '마스터관리자', '기타'))
                conn.commit()
                
                session['email'] = MASTER_EMAIL
                session['company'] = '회계법인 혜안'
                session['username'] = '마스터관리자'
                session['task_type'] = '기타'
                
            conn.close()
            return redirect(url_for('master_page'))
            
        # 일반 계정 처리
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user:
            # 1) 기존 회원: 이메일만으로 로그인 처리 가능 (DB 데이터 세션 주입)
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
        else:
            # 2) 신규 회원: 회사명, 담당자이름, 해당업무가 다 작성되어야 가입 가능
            if not (company and username and task_type):
                return redirect(url_for('index'))
                
            cursor.execute('''
                INSERT INTO users (email, company, username, task_type) 
                VALUES (?, ?, ?, ?)
            ''', (email, company, username, task_type))
            conn.commit()
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
            session['task_type'] = task_type
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return redirect(url_for('index'))
    finally:
        # 혹시 위에서 닫히지 않은 경우를 대비하여 close 처리
        try:
            conn.close()
        except sqlite3.ProgrammingError:
            pass
        
    return redirect(url_for('company_page', company_name=session['company']))

@app.route('/company/<company_name>')
def company_page(company_name):
    if 'email' not in session:
        return redirect(url_for('index'))
        
    if session['email'] == MASTER_EMAIL:
        return redirect(url_for('master_page'))
        
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
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT company, username, task_type, created_at FROM users ORDER BY id DESC')
    partners = cursor.fetchall()
    conn.close()
    
    return render_template('master.html', partners=partners)

@app.route('/submit-request', methods=['POST'])
def submit_request():
    if 'email' not in session:
        return jsonify({'error': '세션이 만료되었습니다. 다시 로그인해 주세요.'}), 401
        
    username = session.get('username')
    help_text = request.form.get('help_text', '').strip()
    file = request.files.get('file')
    
    is_file_empty = not file or file.filename == ''
    if not help_text and is_file_empty:
        return jsonify({'error': '문의 사항을 작성하거나 파일을 첨부해 주세요.'}), 400
        
    if not is_file_empty:
        safe_username = get_safe_path_name(username)
        user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], safe_username)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        filename = get_safe_path_name(file.filename)
        file.save(os.path.join(user_upload_dir, filename))
        
    return redirect(url_for('company_page', company_name=session['company'], success='true'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
