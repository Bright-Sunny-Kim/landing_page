import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

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

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email').strip()
    company = request.form.get('company').strip()
    username = request.form.get('username').strip()
    task_type = request.form.get('task_type')
    
    if not (email and company and username and task_type):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user is None:
            # 신규 가입
            cursor.execute('''
                INSERT INTO users (email, company, username, task_type) 
                VALUES (?, ?, ?, ?)
            ''', (email, company, username, task_type))
            conn.commit()
        else:
            # 기존 정보 업데이트
            cursor.execute('''
                UPDATE users SET company = ?, username = ?, task_type = ? 
                WHERE email = ?
            ''', (company, username, task_type, email))
            conn.commit()
            
        session['email'] = email
        session['company'] = company
        session['username'] = username
        session['task_type'] = task_type
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return redirect(url_for('index'))
    finally:
        conn.close()
        
    if email == MASTER_EMAIL:
        return redirect(url_for('master_page'))
    return redirect(url_for('company_page', company_name=session['company']))

@app.route('/company/<company_name>')
def company_page(company_name):
    # 로그인 세션 확인 및 마스터인 경우 마스터 페이지로 안내
    if 'email' not in session:
        return redirect(url_for('index'))
        
    if session['email'] == MASTER_EMAIL:
        return redirect(url_for('master_page'))
        
    if session['company'] != company_name:
        return redirect(url_for('index'))
        
    # 성공 메시지 여부 획득 (문의 제출 후 리다이렉트 시 사용)
    success = request.args.get('success', 'false') == 'true'
    
    return render_template('company.html', 
                           company_name=company_name,
                           success=success)

@app.route('/master')
def master_page():
    # 보안 권한 검증: 마스터 이메일인지 체크
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return redirect(url_for('index'))
        
    # 전체 파트너사 목록 조회
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
        
    # 문의 및 파일 데이터 받기
    help_text = request.form.get('help_text')
    file = request.files.get('file')
    
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # 로컬 업로드 폴더에 저장
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    # 여기서는 접수 완료 상태로 세션 유지 후 다시 기업 포털로 이동
    # 프로덕션에서는 이 문의를 추가 DB 테이블에 보존할 수 있음
    return redirect(url_for('company_page', company_name=session['company'], success='true'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
