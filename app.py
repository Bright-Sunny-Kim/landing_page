import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
# 세션 처리를 위한 비밀키 설정
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    # 이미 로그인 세션이 존재하면 해당 회사 페이지로 리다이렉트
    if 'company' in session:
        return redirect(url_for('company_page', company_name=session['company']))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    company = request.form.get('company')
    username = request.form.get('username')
    
    # 간단한 유효성 검사 (본인인증 생략)
    if email and company and username:
        session['email'] = email
        session['company'] = company.strip()
        session['username'] = username
        return redirect(url_for('company_page', company_name=session['company']))
    
    return redirect(url_for('index'))

@app.route('/company/<company_name>')
def company_page(company_name):
    # 로그인 세션이 없거나, 세션의 회사명과 경로의 회사명이 다르면 로그인 페이지로 리다이렉트
    if 'company' not in session or session['company'] != company_name:
        return redirect(url_for('index'))
        
    return render_template('company.html', 
                           company_name=company_name, 
                           username=session.get('username'), 
                           email=session.get('email'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
