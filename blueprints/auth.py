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
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master.master_page'))
        return redirect(url_for('pages.company_page', company_name=session['company']))
    
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
    remember = request.form.get('remember') == 'on'
    
    if not email or not supabase:
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
                            return redirect(url_for('auth.login_page', error='invalid_password'))
                    else:
                        if user_password != password:
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
            else:
                if not password:
                    return redirect(url_for('auth.login_page', error='missing_password'))
                hashed = _generate_password_hash(password)
                supabase.table('users').insert({
                    'email': MASTER_EMAIL, 
                    'company': '회계법인 혜안', 
                    'username': '마스터관리자', 
                    'task_type': '기타',
                    'password': hashed
                }).execute()
                
                session['email'] = MASTER_EMAIL
                session['company'] = '회계법인 혜안'
                session['username'] = '마스터관리자'
                session['task_type'] = '기타'
                
            return redirect(url_for('master.master_page'))
            
        response = supabase.table('users').select('*').eq('email', email).execute()
        user = response.data[0] if response.data else None
        
        if user:
            user_password = user.get('password')
            if user_password:
                if user_password.startswith('OAUTH:'):
                    provider = user_password.split(':')[1].capitalize()
                    return redirect(url_for('auth.login_page', error=f'social_only_{provider}'))
                    
                is_hashed = any(user_password.startswith(p) for p in ['pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'])
                if is_hashed:
                    if not _check_password_hash_compatible(user_password, password):
                        return redirect(url_for('auth.login_page', error='invalid_password'))
                else:
                    if user_password != password:
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
        else:
            if not (corporate_number and company and username and task_type and password):
                return redirect(url_for('auth.login_page', error='missing_fields'))
                
            if not re.match(r'^\d{6}-\d{7}$', corporate_number):
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
            supabase.table('users').insert({
                'email': email,
                'corporate_number': corporate_number,
                'company': company,
                'username': username,
                'task_type': task_type,
                'password': hashed
            }).execute()
            
            session['email'] = email
            session['company'] = company
            session['username'] = username
            session['task_type'] = task_type
            
    except Exception:
        logger.exception('Login processing failed for email=%s', email)
        return redirect(url_for('auth.login_page', error='db_error'))
        
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
    remember = data.get('remember') == True
    
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
            
            if email == MASTER_EMAIL:
                return jsonify({'success': True, 'redirect': url_for('master.master_page')})
                
            return jsonify({'success': True, 'redirect': url_for('pages.company_page', company_name=session['company'])})
        else:
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
                supabase.table('users').insert({
                    'email': email,
                    'corporate_number': corporate_number,
                    'company': company,
                    'username': username,
                    'task_type': task_type,
                    'password': oauth_pwd
                }).execute()
                
                session['email'] = email
                session['company'] = company
                session['username'] = username
                session['task_type'] = task_type
                
                return jsonify({'success': True, 'redirect': url_for('pages.company_page', company_name=session['company'])})
            else:
                return jsonify({'need_registration': True, 'email': email})
                
    except Exception as e:
        logger.exception("Social login database error: %s", e)
        return jsonify({'error': f'소셜 로그인 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('pages.index'))
