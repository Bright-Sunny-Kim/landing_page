from flask import Blueprint, render_template, session, redirect, url_for, request

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('intro.html')

@pages_bp.route('/intro')
def intro():
    return render_template('intro.html')

@pages_bp.route('/profile')
def profile():
    return render_template('profile.html')
