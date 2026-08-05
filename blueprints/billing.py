# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, session, jsonify
from extensions import supabase, MASTER_EMAIL, logger

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/api/billing/docs', methods=['GET'])
def get_billing_docs():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        res = supabase.table('documents').select('*').order('created_at', desc=True).execute()
        return jsonify({'data': res.data})
    except Exception as e:
        logger.exception("Error fetching docs: %s", e)
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/api/billing/docs', methods=['POST'])
def create_billing_doc():
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        data = request.json
        doc_type = data.get('type')
        doc_number = data.get('doc_number')
        client_name = data.get('client_name')
        title = data.get('title')
        items = data.get('items', [])
        
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        total_amount = sum(float(item.get('total_price', 0)) for item in items)
        
        doc_res = supabase.table('documents').insert({
            'type': doc_type,
            'doc_number': doc_number,
            'client_name': client_name,
            'title': title,
            'author_email': session['email'],
            'total_amount': total_amount,
            'status': 'draft'
        }).execute()
        
        if not doc_res.data:
            return jsonify({'error': 'Failed to insert document'}), 500
            
        doc_id = doc_res.data[0]['id']
        
        if items:
            for item in items:
                item['document_id'] = doc_id
                if 'id' in item:
                    del item['id']
            supabase.table('document_items').insert(items).execute()
            
        return jsonify({'success': True, 'doc_id': doc_id})
        
    except Exception as e:
        logger.exception("Error creating doc: %s", e)
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/api/billing/docs/<doc_id>', methods=['GET'])
def get_billing_doc_detail(doc_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        doc_res = supabase.table('documents').select('*').eq('id', doc_id).execute()
        if not doc_res.data:
            return jsonify({'error': 'Document not found'}), 404
            
        doc = doc_res.data[0]
        items_res = supabase.table('document_items').select('*').eq('document_id', doc_id).execute()
        doc['items'] = items_res.data
        
        return jsonify({'data': doc})
    except Exception as e:
        logger.exception("Error fetching doc detail: %s", e)
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/api/billing/docs/<doc_id>', methods=['DELETE'])
def delete_billing_doc(doc_id):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not initialized'}), 500
            
        supabase.table('document_items').delete().eq('document_id', doc_id).execute()
        res = supabase.table('documents').delete().eq('id', doc_id).execute()
        
        return jsonify({'success': True, 'deleted': res.data})
    except Exception as e:
        logger.exception("Error deleting doc: %s", e)
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/print/docs/<doc_type>', methods=['GET'])
def print_document(doc_type):
    if 'email' not in session or session['email'] != MASTER_EMAIL:
        return "Unauthorized", 403
        
    doc_id = request.args.get('id')
    if not doc_id:
        return "문서 ID가 없습니다.", 400
        
    try:
        if not supabase:
            return "Supabase not initialized", 500
            
        doc_res = supabase.table('documents').select('*').eq('id', doc_id).execute()
        if not doc_res.data:
            return "문서를 찾을 수 없습니다.", 404
        doc_data = doc_res.data[0]
        
        items_res = supabase.table('document_items').select('*').eq('document_id', doc_id).execute()
        items_data = items_res.data
        
        template_map = {
            'quote': 'doc_quote.html',
            'proposal': 'doc_proposal.html',
            'invoice': 'doc_invoice.html'
        }
        
        template_name = template_map.get(doc_type)
        if not template_name:
            return "잘못된 문서 종류입니다.", 400
            
        return render_template(template_name, doc=doc_data, items=items_data)
    except Exception as e:
        logger.exception("Error rendering print doc: %s", e)
        return str(e), 500
