from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_page')
def login_page():
    if 'email' in session:
        return redirect(url_for('pages.index'))
    error = request.args.get('error', '')
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('pages.index'))
