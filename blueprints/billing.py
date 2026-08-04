from flask import Blueprint, render_template, request, session, jsonify

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/api/billing/docs', methods=['GET'])
def get_billing_docs():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'data': [], 'message': 'Billing API ready'})
