import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = 'database.db'

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
    if 'company' in session:
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
        
    return redirect(url_for('company_page', company_name=session['company']))

@app.route('/company/<company_name>')
def company_page(company_name):
    if 'company' not in session or session['company'] != company_name:
        return redirect(url_for('index'))
        
    # 전체 파트너사 목록 조회 (요청 업무 포함)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT company, username, task_type, created_at FROM users ORDER BY id DESC')
    partners = cursor.fetchall()
    conn.close()
    
    return render_template('company.html', 
                           company_name=company_name, 
                           username=session.get('username'), 
                           email=session.get('email'),
                           task_type=session.get('task_type'),
                           partners=partners)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
