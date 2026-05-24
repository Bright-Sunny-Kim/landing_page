import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    # 결과를 dict 형태로 가져올 수 있도록 설정
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # 데이터베이스 파일 및 테이블이 존재하지 않으면 초기 생성
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 앱 구동 시 데이터베이스 초기화
init_db()

@app.route('/')
def index():
    if 'company' in session:
        return redirect(url_for('company_page', company_name=session['company']))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email').strip()
    company = request.form.get('company').strip()
    username = request.form.get('username').strip()
    
    if not (email and company and username):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 이메일로 기존 회원 여부 확인
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user is None:
            # 이메일이 없는 경우 자동 회원가입 진행
            cursor.execute('''
                INSERT INTO users (email, company, username) 
                VALUES (?, ?, ?)
            ''', (email, company, username))
            conn.commit()
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
        else:
            # 기존 회원인 경우 정보 업데이트 후 로그인 (유연한 대처)
            cursor.execute('''
                UPDATE users SET company = ?, username = ? 
                WHERE email = ?
            ''', (company, username, email))
            conn.commit()
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return redirect(url_for('index'))
    finally:
        conn.close()
        
    return redirect(url_for('company_page', company_name=session['company']))

@app.route('/company/<company_name>')
def company_page(company_name):
    if 'company' not in session or session['company'] != company_name:
        return redirect(url_for('index'))
        
    # 전체 파트너사 목록 조회
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT company, username, created_at FROM users ORDER BY id DESC')
    partners = cursor.fetchall()
    conn.close()
    
    return render_template('company.html', 
                           company_name=company_name, 
                           username=session.get('username'), 
                           email=session.get('email'),
                           partners=partners)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
