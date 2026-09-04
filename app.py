# -*- coding: utf-8 -*-
import os
from datetime import timedelta
from flask import Flask
from core.extensions import logger

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

# ==========================================
# Blueprint Registrations (모듈화)
# ==========================================
from blueprints.pages import pages_bp
from blueprints.auth import auth_bp
from blueprints.master import master_bp
from blueprints.api import api_bp
from blueprints.billing import billing_bp
from blueprints.audit import audit_bp

app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(master_bp)
app.register_blueprint(api_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(audit_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
