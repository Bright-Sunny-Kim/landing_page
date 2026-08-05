# -*- coding: utf-8 -*-
import os
import re
import logging
import hashlib
import hmac
from datetime import timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
from openai import OpenAI
import boto3

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 마스터 관리자 이메일 상수 정의
MASTER_EMAIL = 'cpaeastsun@gmail.com'

# PBKDF2 비밀번호 해시 방식
PASSWORD_HASH_METHOD = 'pbkdf2:sha256:600000'

NOTION_API_BASE_URL = 'https://api.notion.com/v1'
NOTION_API_VERSION = '2022-06-28'
NOTION_TODO_DATABASE_ID = '1e9c14d9973a80bb8c3dc39aacdc1580'

# 환경 변수 로드 (.env)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Supabase 초기화
url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_KEY", "")

if url and key and url != "YOUR_SUPABASE_PROJECT_URL_HERE":
    supabase: Client = create_client(url, key)
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY is missing in .env")
    supabase = None

# OpenAI 초기화
openai_api_key = os.getenv("OPENAI_API_KEY", "")
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)
else:
    logger.warning("OPENAI_API_KEY is missing in .env")
    openai_client = None

# Boto3 MinIO 초기화
minio_endpoint = os.getenv("MINIO_ENDPOINT", "https://s3.hyean-dskim.com")
minio_access_key = os.getenv("MINIO_ACCESS_KEY", "")
minio_secret_key = os.getenv("MINIO_SECRET_KEY", "")

if minio_access_key and minio_secret_key:
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        region_name='us-east-1'
    )
else:
    logger.warning("MINIO credentials missing in .env")
    s3_client = None


def get_safe_path_name(name):
    cleaned = re.sub(r'[\x00\\/:*?"<>|]', '', name).strip()
    return cleaned if cleaned else "unknown"


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
