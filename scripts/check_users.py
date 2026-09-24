# -*- coding: utf-8 -*-
"""
scripts/check_users.py
사용자 계정 목록 조회, 권한(role) 진단, 라우팅 목적지 시뮬레이션 및 권한 일괄/개별 보정 CLI 도구
"""

import sys
import os
import argparse
from typing import List, Dict, Any

# 상위 폴더 경로 추가 (프로젝트 모듈 임포트 가능하도록)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.extensions import supabase, MASTER_EMAIL, logger


if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def determine_routing_target(user: Dict[str, Any]) -> str:
    """사용자 정보를 기반으로 로그인 시 실제 라우팅되는 페이지 경로를 반환합니다."""
    email = user.get('email', '')
    role = user.get('role', 'client')
    company = user.get('company', '')

    if email == MASTER_EMAIL or role == 'master':
        return "[마스터] /master (마스터 분석 허브)"
    elif role in ['cpa', 'auditor']:
        return "[감사포털] /audit (회계감사 전용 포털)"
    else:
        return f"[고객사] /company/{company} (고객사 포털)"


def list_users() -> List[Dict[str, Any]]:
    """Supabase users 테이블에서 전체 유저 목록을 조회합니다."""
    if not supabase:
        print("❌ Supabase 연결이 설정되어 있지 않습니다.")
        return []

    try:
        response = supabase.table('users').select('*').order('created_at', desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"유저 목록 조회 중 오류 발생: {e}", exc_info=True)
        print(f"❌ DB 조회 실패: {e}")
        return []


def print_users_table(users: List[Dict[str, Any]]) -> None:
    """유저 목록을 가독성 높은 테이블 형식으로 콘솔에 출력합니다."""
    if not users:
        print("\n등록된 사용자가 없습니다.")
        return

    print("\n" + "=" * 105)
    print("                     [ HEYAN 사용자 권한 및 로그인 라우팅 진단 센터 ]")
    print("=" * 105)
    
    header = f"{'번호':<4} | {'이메일':<26} | {'회사명':<16} | {'담당자':<10} | {'업무유형':<10} | {'Role':<8} | {'최종 진입 페이지'}"
    print(header)
    print("-" * 105)

    for idx, u in enumerate(users, 1):
        email = u.get('email', '-')[:25]
        company = u.get('company', '-')[:15]
        username = u.get('username', '-')[:8]
        task_type = u.get('task_type', '-')[:8]
        role = u.get('role', 'client')
        target = determine_routing_target(u)

        row = f"{idx:<4} | {email:<26} | {company:<16} | {username:<10} | {task_type:<10} | {role:<8} | {target}"
        print(row)

    print("=" * 105)
    print(f"총 {len(users)}명의 사용자가 등록되어 있습니다.\n")


def set_user_role(email: str, new_role: str) -> bool:
    """특정 사용자의 role을 변경합니다."""
    if not supabase:
        print("[ERROR] Supabase 연결이 설정되어 있지 않습니다.")
        return False

    valid_roles = ['master', 'cpa', 'auditor', 'client']
    if new_role not in valid_roles:
        print(f"[ERROR] 올바르지 않은 role 값입니다. 가능한 값: {', '.join(valid_roles)}")
        return False

    try:
        response = supabase.table('users').update({'role': new_role}).eq('email', email).execute()
        if response.data:
            print(f"[OK] [{email}] 사용자의 권한이 '{new_role}'(으)로 성공적으로 변경되었습니다.")
            return True
        else:
            print(f"[WARN] [{email}] 계정을 찾을 수 없습니다.")
            return False
    except Exception as e:
        logger.error(f"권한 변경 실패 ({email}): {e}", exc_info=True)
        print(f"[ERROR] 권한 변경 중 오류 발생: {e}")
        return False


def fix_client_roles() -> None:
    """마스터 및 혜안 소속 회계사를 제외한 일반 고객사 계정 중 cpa로 잘못 지정된 role을 client로 일괄 보정합니다."""
    if not supabase:
        print("[ERROR] Supabase 연결이 설정되어 있지 않습니다.")
        return

    users = list_users()
    fixed_count = 0

    print("\n[INFO] 일반 고객사 권한 검사 및 보정 시작...")
    for u in users:
        email = u.get('email', '')
        company = u.get('company', '')
        role = u.get('role', 'client')

        # 마스터 계정이 아니고, 회사명이 '회계법인 혜안'이 아닌데 role이 cpa인 경우
        if email != MASTER_EMAIL and '혜안' not in company and role in ['cpa', 'auditor']:
            print(f"  -> 보정 대상 발견: {email} (회사: {company}, 현재 Role: {role} -> 변경: client)")
            try:
                supabase.table('users').update({'role': 'client'}).eq('email', email).execute()
                fixed_count += 1
            except Exception as e:
                print(f"[ERROR] {email} 보정 실패: {e}")

    if fixed_count > 0:
        print(f"\n[OK] 총 {fixed_count}건의 고객사 계정 권한이 'client'로 안전하게 보정되었습니다!")
    else:
        print("\n[OK] 이미 모든 고객사 계정의 권한이 정상('client')입니다.")


def main():
    parser = argparse.ArgumentParser(description="HEYAN 사용자 권한 및 로그인 라우팅 진단 CLI")
    parser.add_argument('--list', action='store_true', help="전체 유저 목록 및 라우팅 목적지 출력 (기본값)")
    parser.add_argument('--fix-clients', action='store_true', help="일반 고객사 계정 중 잘못 지정된 cpa 권한을 client로 일괄 보정")
    parser.add_argument('--set-role', nargs=2, metavar=('EMAIL', 'ROLE'), help="특정 유저의 Role 변경 (예: --set-role user@test.com client)")

    args = parser.parse_args()

    if args.fix_clients:
        fix_client_roles()
        users = list_users()
        print_users_table(users)
    elif args.set_role:
        email, new_role = args.set_role
        if set_user_role(email, new_role):
            users = list_users()
            print_users_table(users)
    else:
        users = list_users()
        print_users_table(users)


if __name__ == '__main__':
    main()
