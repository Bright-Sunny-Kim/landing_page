# -*- coding: utf-8 -*-
import os
import re
import time
import logging
import hashlib
import hmac
import requests
import pandas as pd
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
from audit_engine import (
    parse_tb_file, run_variance_analysis, retrieve_k_gaap, generate_working_paper,
    classify_source_file, parse_trial_balance_structured, parse_financial_statement,
    financial_statement_to_variance_input, build_standard_statements,
)

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

# PBKDF2 avoids OpenSSL/scrypt runtime failures on constrained production hosts
# and remains readable by older Werkzeug releases during rolling deployments.
PASSWORD_HASH_METHOD = 'pbkdf2:sha256:600000'


def _generate_password_hash(password):
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


def _check_password_hash_compatible(stored_hash, password):
    """Verify Werkzeug hashes, including scrypt on older Werkzeug versions."""
    try:
        return check_password_hash(stored_hash, password)
    except (TypeError, ValueError):
        pass

    try:
        method, salt, expected = stored_hash.split('$', 2)
        if not method.startswith('scrypt:'):
            return False
        n, r, p = (int(value) for value in method.split(':')[1:])
        actual = hashlib.scrypt(
            password.encode('utf-8'), salt=salt.encode('utf-8'), n=n, r=r, p=p
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


NOTION_API_BASE_URL = 'https://api.notion.com/v1'
NOTION_API_VERSION = '2022-06-28'
NOTION_TODO_DATABASE_ID = '1e9c14d9973a80bb8c3dc39aacdc1580'

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



# ==========================================
# Blueprint Registrations (모듈화)
# ==========================================
from blueprints.pages import pages_bp
from blueprints.auth import auth_bp
from blueprints.billing import billing_bp

app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(billing_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
