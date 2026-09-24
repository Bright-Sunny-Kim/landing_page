# -*- coding: utf-8 -*-
import re
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from core.extensions import (
    supabase, MASTER_EMAIL, _generate_password_hash,
    _check_password_hash_compatible, logger
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_page')
def login_page():
    if 'email' in session:
        user_role = session.get('role', 'client')
        if session['email'] == MASTER_EMAIL or user_role == 'master':
            return redirect(url_for('master.master_page'))
        elif user_role in ['cpa', 'auditor']:
            return redirect(url_for('audit.audit_page'))
        return redirect(url_for('pages.company_page', company_name=session.get('company', '')))
    
    error = request.args.get('error', '')
    return render_template('login.html', error=error)

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'exists': False})
        
    if email == MASTER_EMAIL:
        if supabase:
            try:
                response = supabase.table('users').select('*').eq('email', MASTER_EMAIL).execute()
                user = response.data[0] if response.data else None
                if user:
                    has_password = bool(user.get('password'))
                    return jsonify({'exists': True, 'has_password': has_password})
            except Exception:
                logger.exception('Master check-email database query failed')
        return jsonify({'exists': True, 'has_password': False})
        
    if not supabase:
        return jsonify({'exists': False, 'error': 'Supabase not configured'})

    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            has_password = bool(user.get('password'))
            return jsonify({'exists': True, 'has_password': has_password})
    except Exception:
        logger.exception('Check-email database query failed')
        return jsonify({'exists': False, 'error': 'database_unavailable'}), 503
        
    return jsonify({'exists': False})

@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    corporate_number = request.form.get('corporate_number', '').strip()
    company = request.form.get('company', '').strip()
    username = request.form.get('username', '').strip()
    task_type = request.form.get('task_type', '')
    is_auditor = request.form.get('is_auditor') in ['on', 'true', '1']
    cpa_number = request.form.get('cpa_number', '').strip()
    remember = request.form.get('remember') == 'on'
    
    logger.info("[AUTH_REQ] POST /login - email=%s, is_auditor=%s, remember=%s", email, is_auditor, remember)
    
    if not email or not supabase:
        logger.warning("[AUTH_WARN] Missing email or Supabase unconfigured")
        return redirect(url_for('auth.login_page', error='missing_fields'))
        
    try:
        if remember:
            session.permanent = True
        else:
            session.permanent = False
            
        if email == MASTER_EMAIL:
            response = supabase.table('users').select('*').eq('email', email).execute()
            user = response.data[0] if response.data else None
            
            if user:
                user_password = user.get('password')
                if user_password:
                    is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                    if is_hashed:
                        if not _check_password_hash_compatible(user_password, password):
                            logger.warning("[AUTH_FAIL] Master password mismatch for %s", email)
                            return redirect(url_for('auth.login_page', error='invalid_password'))
                    else:
                        if user_password != password:
                            logger.warning("[AUTH_FAIL] Master plain password mismatch for %s", email)
                            return redirect(url_for('auth.login_page', error='invalid_password'))
                        try:
                            hashed = _generate_password_hash(password)
                            supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                        except Exception:
                            logger.exception('Failed to migrate master password hash')
                else:
                    if not password:
                        return redirect(url_for('auth.login_page', error='missing_password'))
                    hashed = _generate_password_hash(password)
                    supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
                session['email'] = user['email']
                session['company'] = user.get('company', '회계법인 혜안')
                session['username'] = user.get('username', '마스터관리자')
                session['task_type'] = user.get('task_type', '기타')
                session['role'] = 'master'
            else:
                if not password:
                    return redirect(url_for('auth.login_page', error='missing_password'))
                hashed = _generate_password_hash(password)
                supabase.table('users').insert({
                    'email': MASTER_EMAIL, 
                    'company': '회계법인 혜안', 
                    'username': '마스터관리자', 
                    'task_type': '기타',
                    'role': 'master',
                    'password': hashed
                }).execute()
                
                session['email'] = MASTER_EMAIL
                session['company'] = '회계법인 혜안'
                session['username'] = '마스터관리자'
                session['task_type'] = '기타'
                session['role'] = 'master'
                
            logger.info("[AUTH_SUCCESS] Master logged in: %s", email)
            return redirect(url_for('master.master_page'))
            
        response = supabase.table('users').select('*').eq('email', email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            user_password = user.get('password')
            if user_password:
                if user_password.startswith('OAUTH:'):
                    provider = user_password.split(':')[1].capitalize()
                    logger.info("[AUTH_INFO] Account %s is OAuth-only (%s)", email, provider)
                    return redirect(url_for('auth.login_page', error=f'social_only_{provider}'))
                    
                is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                if is_hashed:
                    if not _check_password_hash_compatible(user_password, password):
                        logger.warning("[AUTH_FAIL] Password mismatch for user=%s", email)
                        return redirect(url_for('auth.login_page', error='invalid_password'))
                else:
                    if user_password != password:
                        logger.warning("[AUTH_FAIL] Plain password mismatch for user=%s", email)
                        return redirect(url_for('auth.login_page', error='invalid_password'))
                    try:
                        hashed = _generate_password_hash(password)
                        supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                    except Exception:
                        logger.exception('Failed to migrate user password hash')
            else:
                if not password:
                    return redirect(url_for('auth.login_page', error='missing_password'))
                hashed = _generate_password_hash(password)
                supabase.table('users').update({'password': hashed}).eq('email', email).execute()
                
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
            session['role'] = user.get('role', 'client')
            if user.get('cpa_number'):
                session['cpa_number'] = user['cpa_number']
            logger.info("[AUTH_SUCCESS] User logged in: email=%s, role=%s, company=%s", email, session['role'], session['company'])
        else:
            if is_auditor:
                user_role = 'cpa'
                if not company:
                    company = '회계법인 혜안'
                if not task_type:
                    task_type = '회계감사'
                if not corporate_number:
                    corporate_number = '110111-0000000'
            else:
                user_role = 'client'

            if not (corporate_number and company and username and task_type and password):
                logger.warning("[AUTH_WARN] Missing registration fields for new user=%s", email)
                return redirect(url_for('auth.login_page', error='missing_fields'))
                
            if not re.match(r'^\d{6}-\d{7}$', corporate_number):
                logger.warning("[AUTH_WARN] Invalid corporate number format: %s", corporate_number)
                return redirect(url_for('auth.login_page', error='invalid_corp_num'))
                
            existing_corp = supabase.table('users').select('company').eq('corporate_number', corporate_number).execute()
            if existing_corp.data:
                company = existing_corp.data[0]['company']
            else:
                try:
                    supabase.table('companies').insert({
                        'corporate_number': corporate_number,
                        'company_name': company
                    }).execute()
                except Exception:
                    logger.exception('Failed to synchronize company during login')

            hashed = _generate_password_hash(password)
            user_insert_data = {
                'email': email,
                'corporate_number': corporate_number,
                'company': company,
                'username': username,
                'task_type': task_type,
                'role': user_role,
                'password': hashed
            }
            if cpa_number:
                user_insert_data['cpa_number'] = cpa_number

            try:
                supabase.table('users').insert(user_insert_data).execute()
            except Exception as insert_err:
                if 'cpa_number' in str(insert_err) or 'PGRST204' in str(insert_err):
                    logger.warning("[AUTH_REGISTER_WARN] 'cpa_number' column not found in schema. Retrying insert without cpa_number...")
                    user_insert_data.pop('cpa_number', None)
                    supabase.table('users').insert(user_insert_data).execute()
                else:
                    raise insert_err

            logger.info("[AUTH_REGISTER] New user registered: email=%s, role=%s, cpa_number=%s", email, user_role, cpa_number)
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
            session['task_type'] = task_type
            session['role'] = user_role
            if cpa_number:
                session['cpa_number'] = cpa_number
            
    except Exception:
        logger.exception('Login processing failed for email=%s', email)
        return redirect(url_for('auth.login_page', error='db_error'))
        
    if session.get('role') in ['cpa', 'auditor']:
        logger.info("[AUTH_ROUTING] Direct routing to /audit for %s (role=%s)", email, session.get('role'))
        return redirect(url_for('audit.audit_page'))
    return redirect(url_for('pages.company_page', company_name=session['company']))

@auth_bp.route('/login/social', methods=['POST'])
def login_social():
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    provider = data.get('provider', '').strip()
    corporate_number = data.get('corporate_number', '').strip()
    company = data.get('company', '').strip()
    username = data.get('username', '').strip()
    task_type = data.get('task_type', '').strip()
    is_auditor = data.get('is_auditor') in [True, 'true', 'on', '1']
    cpa_number = data.get('cpa_number', '').strip()
    remember = data.get('remember') == True
    
    logger.info("[AUTH_SOCIAL_REQ] POST /login/social - email=%s, provider=%s, is_auditor=%s", email, provider, is_auditor)
    
    if not email or not provider:
        return jsonify({'error': '이메일과 소셜 제공자 정보가 누락되었습니다.'}), 400
        
    try:
        if remember:
            session.permanent = True
        else:
            session.permanent = False
            
        response = supabase.table('users').select('*').eq('email', email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            session['email'] = user['email']
            session['company'] = user['company']
            session['username'] = user['username']
            session['task_type'] = user['task_type']
            session['role'] = user.get('role', 'client')
            if user.get('cpa_number'):
                session['cpa_number'] = user['cpa_number']
                
            logger.info("[AUTH_SOCIAL_SUCCESS] Existing social user login: email=%s, role=%s", email, session['role'])
            
            if email == MASTER_EMAIL or session.get('role') == 'master':
                return jsonify({'success': True, 'redirect': url_for('master.master_page')})
            elif session.get('role') in ['cpa', 'auditor']:
                return jsonify({'success': True, 'redirect': url_for('audit.audit_page')})
                
            return jsonify({'success': True, 'redirect': url_for('pages.company_page', company_name=session['company'])})
        else:
            if is_auditor:
                user_role = 'cpa'
                if not company:
                    company = '회계법인 혜안'
                if not task_type:
                    task_type = '회계감사'
                if not corporate_number:
                    corporate_number = '110111-0000000'
            else:
                user_role = 'client'

            if corporate_number and company and username and task_type:
                if not re.match(r'^\d{6}-\d{7}$', corporate_number):
                    return jsonify({'error': '법인등록번호는 000000-0000000 형식이어야 합니다.'}), 400
                    
                existing_corp = supabase.table('users').select('company').eq('corporate_number', corporate_number).execute()
                if existing_corp.data:
                    company = existing_corp.data[0]['company']
                else:
                    try:
                        supabase.table('companies').insert({
                            'corporate_number': corporate_number,
                            'company_name': company
                        }).execute()
                    except Exception as company_sync_err:
                        logger.exception("companies sync error: %s", company_sync_err)

                oauth_pwd = f"OAUTH:{provider}"
                user_insert_data = {
                    'email': email,
                    'corporate_number': corporate_number,
                    'company': company,
                    'username': username,
                    'task_type': task_type,
                    'role': user_role,
                    'password': oauth_pwd
                }
                if cpa_number:
                    user_insert_data['cpa_number'] = cpa_number

                try:
                    supabase.table('users').insert(user_insert_data).execute()
                except Exception as insert_err:
                    if 'cpa_number' in str(insert_err) or 'PGRST204' in str(insert_err):
                        logger.warning("[AUTH_SOCIAL_WARN] 'cpa_number' column not found. Retrying insert without cpa_number...")
                        user_insert_data.pop('cpa_number', None)
                        supabase.table('users').insert(user_insert_data).execute()
                    else:
                        raise insert_err

                logger.info("[AUTH_SOCIAL_REGISTER] New social user registered: email=%s, role=%s, cpa_number=%s", email, user_role, cpa_number)
                
                session['email'] = email
                session['company'] = company
                session['username'] = username
                session['task_type'] = task_type
                session['role'] = user_role
                if cpa_number:
                    session['cpa_number'] = cpa_number
                
                if user_role in ['cpa', 'auditor']:
                    return jsonify({'success': True, 'redirect': url_for('audit.audit_page')})
                return jsonify({'success': True, 'redirect': url_for('pages.company_page', company_name=session['company'])})
            else:
                return jsonify({'need_registration': True, 'email': email})
                
    except Exception as e:
        logger.exception("Social login database error: %s", e)
        return jsonify({'error': f'소셜 로그인 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    if 'email' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    email = session['email']
    logger.info("[PROFILE_REQ] GET /api/user/profile - email=%s", email)
    
    if not supabase:
        return jsonify({'error': 'Supabase 연결이 설정되지 않았습니다.'}), 500
        
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if not response.data:
            return jsonify({'error': '사용자 정보를 찾을 수 없습니다.'}), 404
            
        user = response.data[0]
        user_role = user.get('role', 'client')
        is_auditor = user_role in ['cpa', 'auditor']
        
        profile_data = {
            'email': user.get('email', ''),
            'username': user.get('username', ''),
            'company': user.get('company', ''),
            'corporate_number': user.get('corporate_number', ''),
            'task_type': user.get('task_type', ''),
            'role': user_role,
            'is_auditor': is_auditor,
            'cpa_number': user.get('cpa_number', '') or session.get('cpa_number', '') or '',
            'created_at': user.get('created_at', '')
        }
        logger.info("[PROFILE_RES] Profile loaded for %s (role=%s, is_auditor=%s)", email, user_role, is_auditor)
        return jsonify({'success': True, 'profile': profile_data})
    except Exception as e:
        logger.exception("Failed to fetch user profile for %s", email)
        return jsonify({'error': f'프로필 조회 실패: {str(e)}'}), 500


def _log_user_change(user_email: str, changed_by: str, change_type: str, before_data: dict, after_data: dict, ip_address: str = None):
    """사용자 정보 및 권한 변경 이력을 user_change_logs 테이블에 안전하게 기록합니다."""
    if not supabase:
        return
    try:
        supabase.table('user_change_logs').insert({
            'user_email': user_email,
            'changed_by': changed_by,
            'change_type': change_type,
            'before_data': before_data,
            'after_data': after_data,
            'ip_address': ip_address or (request.headers.get('X-Forwarded-For', request.remote_addr) if request else '127.0.0.1')
        }).execute()
        logger.info("[AUDIT_LOG_SUCCESS] User change recorded: email=%s, type=%s, before=%s, after=%s",
                    user_email, change_type, before_data, after_data)
    except Exception as e:
        logger.warning("[AUDIT_LOG_WARN] Failed to insert into user_change_logs (safe ignore): %s", e)


@auth_bp.route('/api/user/profile', methods=['POST'])
def update_user_profile():
    if 'email' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
        
    email = session['email']
    data = request.get_json() or {}
    
    username = data.get('username', '').strip()
    company = data.get('company', '').strip()
    corporate_number = data.get('corporate_number', '').strip()
    task_type = data.get('task_type', '').strip()
    is_auditor = data.get('is_auditor') in [True, 'true', 'on', '1']
    cpa_number = data.get('cpa_number', '').strip()
    password = data.get('password', '').strip()
    
    logger.info("[PROFILE_UPDATE_REQ] POST /api/user/profile - email=%s, is_auditor=%s, username=%s, company=%s",
                email, is_auditor, username, company)
                
    if not supabase:
        return jsonify({'error': 'Supabase 연결이 설정되지 않았습니다.'}), 500
        
    try:
        current_res = supabase.table('users').select('*').eq('email', email).execute()
        if not current_res.data:
            return jsonify({'error': '사용자 계정을 찾을 수 없습니다.'}), 404
            
        current_user = current_res.data[0]
        current_role = current_user.get('role', 'client')
        
        # 마스터 계정의 경우 role을 master로 보존
        if email == MASTER_EMAIL or current_role == 'master':
            new_role = 'master'
        elif is_auditor:
            new_role = 'cpa'
        else:
            new_role = 'client'
            
        update_fields = {
            'role': new_role
        }
        if cpa_number if is_auditor else False:
            update_fields['cpa_number'] = cpa_number
        
        if username:
            update_fields['username'] = username
            session['username'] = username
            
        if company:
            update_fields['company'] = company
            session['company'] = company
            
        if corporate_number:
            if re.match(r'^\d{6}-\d{7}$', corporate_number):
                update_fields['corporate_number'] = corporate_number
            elif not is_auditor:
                return jsonify({'error': '법인등록번호는 000000-0000000 형식이어야 합니다.'}), 400
                
        if task_type:
            update_fields['task_type'] = task_type
            session['task_type'] = task_type
        elif is_auditor and not current_user.get('task_type'):
            update_fields['task_type'] = '회계감사'
            session['task_type'] = '회계감사'
            
        if password:
            hashed = _generate_password_hash(password)
            update_fields['password'] = hashed
            
        try:
            supabase.table('users').update(update_fields).eq('email', email).execute()
        except Exception as update_err:
            if 'cpa_number' in str(update_err) or 'PGRST204' in str(update_err):
                logger.warning("[PROFILE_UPDATE_WARN] 'cpa_number' column not found in schema. Retrying update without cpa_number...")
                update_fields.pop('cpa_number', None)
                supabase.table('users').update(update_fields).eq('email', email).execute()
            else:
                raise update_err
        
        # 변경 전/후 데이터 비교 및 이력(Audit Log) 자동 적재
        before_diff = {}
        after_diff = {}
        for k, v in update_fields.items():
            if k == 'password':
                before_diff['password'] = '(기존 비밀번호)'
                after_diff['password'] = '(새 비밀번호 변경됨)'
            else:
                old_val = current_user.get(k)
                if old_val != v:
                    before_diff[k] = old_val
                    after_diff[k] = v

        if before_diff or after_diff:
            change_type = 'ROLE_CHANGE' if 'role' in after_diff else 'PROFILE_UPDATE'
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            _log_user_change(
                user_email=email,
                changed_by=session.get('email', email),
                change_type=change_type,
                before_data=before_diff,
                after_data=after_diff,
                ip_address=client_ip
            )

        # 세션 갱신
        session['role'] = new_role
        if cpa_number and is_auditor:
            session['cpa_number'] = cpa_number
        elif 'cpa_number' in session and not is_auditor:
            session.pop('cpa_number', None)
            
        logger.info("[PROFILE_UPDATE_SUCCESS] Profile updated for %s: new_role=%s, is_auditor=%s, company=%s",
                    email, new_role, is_auditor, session.get('company'))
                    
        redirect_target = None
        if new_role in ['cpa', 'auditor']:
            redirect_target = url_for('audit.audit_page')
        elif new_role == 'master' or email == MASTER_EMAIL:
            redirect_target = url_for('master.master_page')
        else:
            redirect_target = url_for('pages.company_page', company_name=session.get('company', ''))
            
        return jsonify({
            'success': True,
            'message': '회원 정보가 성공적으로 수정되었습니다.',
            'role': new_role,
            'is_auditor': is_auditor,
            'redirect': redirect_target
        })
    except Exception as e:
        logger.exception("Profile update error for %s", email)
        return jsonify({'error': f'회원 정보 수정 중 오류가 발생했습니다: {str(e)}'}), 500


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('pages.index'))
