# -*- coding: utf-8 -*-
import os
import csv
import json
import datetime
import requests
from io import StringIO
from flask import Blueprint, request, jsonify, session, Response, stream_with_context, send_from_directory, current_app
from core.extensions import (
    supabase, openai_client, MASTER_EMAIL, logger
)

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/faq/ask', methods=['POST'])
def faq_ask():
    global openai_client, supabase
    
    if not openai_client:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            
    if not supabase:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if url and key and url != "YOUR_SUPABASE_PROJECT_URL_HERE":
            from supabase import create_client
            supabase = create_client(url, key)

    if not openai_client or not supabase:
        missing = []
        if not openai_client: missing.append("openai")
        if not supabase: missing.append("supabase")
        return jsonify({'error': f'서버의 AI 설정이 올바르지 않습니다. (Missing: {", ".join(missing)})'}), 500

    data = request.get_json() or {}
    question = data.get('question', '').strip()
    category = data.get('category', '전체')

    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    try:
        conversation_id = data.get('conversation_id', '').strip()
        
        clean_q = question.replace(" ", "").lower()
        trivial_keywords = ["안녕", "반가워", "고마워", "수고", "감사", "안뇽", "하이", "hello"]
        swear_keywords = ["시발", "씨발", "개새끼", "미친", "존나", "좆", "병신"]
        
        if any(w in clean_q for w in swear_keywords):
            def generate_trivial():
                msg = "올바른 언어를 사용해주세요. 저는 회계감사 기준에 대해 답변해 드리는 AI입니다."
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id})}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
            
        if len(clean_q) <= 10 and any(w in clean_q for w in trivial_keywords):
            def generate_trivial():
                msg = "안녕하세요! 혜안 파트너스 회계감사 AI 어시스턴트입니다. 회계 기준이나 감사 기준에 대해 무엇이든 물어보세요!"
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id})}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
        
        logger.info("[FAQ Ask] Received question: %s, category: %s, conv_id: %s", question, category, conversation_id)
        
        dify_api_key = os.environ.get("DIFY_API_KEY", "app-mIeCNphyBVBn6diJpnybnzdS")
        
        payload = {
            "inputs": {"category": category},
            "query": question,
            "response_mode": "streaming",
            "user": session.get("user_id", "web-user")
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        headers = {
            "Authorization": f"Bearer {dify_api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("[FAQ Ask] Forwarding streaming request to Dify API...")
        
        dify_api_base_url = os.environ.get("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
        dify_response = requests.post(f"{dify_api_base_url}/chat-messages", json=payload, headers=headers, stream=True)
        
        if dify_response.status_code != 200:
            logger.error("[FAQ Ask] Dify API returned status %s: %s", dify_response.status_code, dify_response.text)
            return jsonify({'error': 'Dify AI 챗봇 연동 중 오류가 발생했습니다.'}), 500

        def generate():
            for line in dify_response.iter_lines():
                if line:
                    yield line + b'\n\n'
                    
        return Response(stream_with_context(generate()), content_type='text/event-stream')

    except Exception as e:
        logger.exception("FAQ Ask error: %s", e)
        return jsonify({'error': '질의 처리 중 오류가 발생했습니다.'}), 500


@api_bp.route('/api/dify/retrieval', methods=['POST'])
def dify_retrieval():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    
    logger.info("[Dify Retrieval] Received query: %s", query)
    
    if not query:
        logger.warning("[Dify Retrieval] Empty query received.")
        return jsonify({"records": []}), 200
        
    try:
        logger.info("[Dify Retrieval] Generating embeddings for query...")
        embed_response = openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-large",
            dimensions=1536
        )
        query_embedding = embed_response.data[0].embedding
        logger.info("[Dify Retrieval] Embedding generated successfully.")
        
        import chromadb
        host = os.environ.get("CHROMA_SERVER_HOST", "localhost")
        port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
        logger.info("[Dify Retrieval] Connecting to ChromaDB at %s:%d...", host, port)
        
        chroma_client = chromadb.HttpClient(host=host, port=port)
        collection = chroma_client.get_collection(name="document_chunks")
        
        n_results_target = 30
        logger.info("[Dify Retrieval] Querying top %d results from collection...", n_results_target)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results_target
        )
        
        initial_records = []
        documents_for_rerank = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                distance = results['distances'][0][i]
                sim = 1.0 - distance
                
                if sim >= 0.10:
                    doc_name = metadata.get("document_name", "알수없음")
                    cat = metadata.get("category", "기타")
                    art_name = metadata.get("article_name", "")
                    
                    content = f"[{cat}] {doc_name} ({art_name})\n{document}"
                    initial_records.append({
                        "content": content,
                        "score": float(sim)
                    })
                    documents_for_rerank.append(content)
                    
            logger.info("[Dify Retrieval] Successfully retrieved %d chunks for reranking.", len(initial_records))
        else:
            logger.info("[Dify Retrieval] No matching results found in ChromaDB.")
            
        final_records = []
        if documents_for_rerank:
            import cohere
            cohere_api_key = os.environ.get("COHERE_API_KEY")
            if cohere_api_key:
                logger.info("[Dify Retrieval] Reranking results with Cohere...")
                try:
                    co_client = cohere.Client(cohere_api_key)
                    rerank_response = co_client.rerank(
                        model="rerank-multilingual-v3.0",
                        query=query,
                        documents=documents_for_rerank,
                        top_n=5
                    )
                    
                    for r_result in rerank_response.results:
                        idx = r_result.index
                        if r_result.relevance_score >= 0.3:
                            initial_records[idx]["score"] = r_result.relevance_score
                            final_records.append(initial_records[idx])
                            
                    logger.info("[Dify Retrieval] Reranking complete. Selected %d records.", len(final_records))
                except Exception as ce:
                    logger.exception("[Dify Retrieval] Cohere Rerank failed: %s", ce)
                    initial_records.sort(key=lambda x: x["score"], reverse=True)
                    final_records = initial_records[:5]
            else:
                logger.warning("[Dify Retrieval] No COHERE_API_KEY found, skipping rerank.")
                initial_records.sort(key=lambda x: x["score"], reverse=True)
                final_records = initial_records[:5]
            
        logger.info("[Dify Retrieval] Returning %d records.", len(final_records))
        return jsonify({"records": final_records}), 200
        
    except Exception as e:
        logger.exception("[Dify Retrieval] Error: %s", e)
        return jsonify({"records": []}), 500


@api_bp.route('/api/financial_institutions', methods=['GET'])
def get_financial_institutions():
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        res = supabase.table('financial_institutions').select('*').eq('is_active', True).execute()
        return jsonify(res.data)
    except Exception as e:
        logger.exception("get_financial_institutions error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/inquiry/new', methods=['POST'])
def new_inquiry_request():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    client_id = session.get('email')
    company_name = data.get('company_name')
    fiscal_year = data.get('fiscal_year')
    institution_id = data.get('institution_id')
    inquiry_type = data.get('inquiry_type')
    
    if not all([company_name, fiscal_year, institution_id, inquiry_type]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        inst_res = supabase.table('financial_institutions').select('*').eq('id', institution_id).execute()
        if not inst_res.data:
            return jsonify({'error': 'Invalid institution_id'}), 400
        
        inst_data = inst_res.data[0]
        if inst_data['inquiry_type'] == 'online' and inquiry_type == 'paper':
            return jsonify({'error': 'This institution only supports online inquiry.'}), 400
            
        now = datetime.datetime.now()
        prefix = f"INQ-{now.strftime('%Y%m')}-"
        latest_res = supabase.table('inquiry_requests').select('request_no').ilike('request_no', f"{prefix}%").order('request_no', desc=True).limit(1).execute()
        
        new_seq = 1
        if latest_res.data:
            latest_no = latest_res.data[0]['request_no']
            new_seq = int(latest_no.split('-')[2]) + 1
            
        request_no = f"{prefix}{new_seq:04d}"
        
        insert_data = {
            'request_no': request_no,
            'client_id': client_id,
            'company_name': company_name,
            'fiscal_year': int(fiscal_year),
            'institution_id': institution_id,
            'inquiry_type': inquiry_type,
            'status': 'submitted'
        }
        
        insert_res = supabase.table('inquiry_requests').insert(insert_data).execute()
        
        if not insert_res.data:
            return jsonify({'error': 'Failed to insert request'}), 500
            
        new_request_id = insert_res.data[0]['id']
        
        supabase.table('inquiry_status_logs').insert({
            'request_id': new_request_id,
            'status_from': 'draft',
            'status_to': 'submitted',
            'changed_by': client_id,
            'memo': '신청서 작성 완료'
        }).execute()
        
        logger.info("[EMAIL MOCK] 신청 완료 메일 발송 -> 고객: %s, 담당자: %s", client_id, MASTER_EMAIL)
        
        return jsonify({'success': True, 'request_no': request_no})
        
    except Exception as e:
        logger.exception("New inquiry error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/inquiry/status', methods=['GET'])
def get_inquiry_status():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        email = session.get('email')
        res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').eq('client_id', email).order('created_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        logger.exception("get_inquiry_status error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/inquiry/download_form/<int:request_id>', methods=['GET'])
def download_inquiry_form(request_id):
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        req_res = supabase.table('inquiry_requests').select('*, financial_institutions(form_type)').eq('id', request_id).execute()
        if not req_res.data:
            return jsonify({'error': 'Request not found'}), 404
            
        req_data = req_res.data[0]
        
        if session.get('email') != req_data['client_id'] and session.get('email') != MASTER_EMAIL:
            return jsonify({'error': 'Unauthorized'}), 401
            
        form_type = req_data['financial_institutions']['form_type']
        
        now_str = datetime.datetime.now().isoformat()
        supabase.table('inquiry_requests').update({
            'form_downloaded_at': now_str
        }).eq('id', request_id).execute()
        
        forms_dir = os.path.join(current_app.root_path, 'static', 'forms')
        
        if not os.path.exists(forms_dir):
            os.makedirs(forms_dir)
            
        filename_map = {
            'bank': '금융기관조회서_은행용.docx',
            'insurance': '금융기관조회서_보험용.docx',
            'securities': '금융기관조회서_증권용.docx',
            'card': '금융기관조회서_카드용.docx',
            'other': '금융기관조회서_기타.docx'
        }
        
        filename = filename_map.get(form_type, '금융기관조회서_기타.docx')
        filepath = os.path.join(forms_dir, filename)
        
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("이 파일은 양식 다운로드 테스트용 빈 파일입니다.")
        
        return send_from_directory(forms_dir, filename, as_attachment=True)
        
    except Exception as e:
        logger.exception("Download form error: %s", e)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/admin/inquiry', methods=['GET'])
def get_all_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').order('created_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        logger.exception("get_all_inquiries error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/admin/inquiry/update_status', methods=['POST'])
def update_inquiry_status():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    request_id = data.get('request_id')
    new_status = data.get('status')
    mail_tracking_no = data.get('mail_tracking_no')
    notes = data.get('notes')
    
    if not request_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        req_res = supabase.table('inquiry_requests').select('*').eq('id', request_id).execute()
        if not req_res.data:
            return jsonify({'error': 'Request not found'}), 404
            
        old_status = req_res.data[0]['status']
        
        status_order = {
            'draft': 0, 'submitted': 1, 'fee_pending': 2, 'fee_paid': 3,
            'form_downloaded': 4, 'mail_sent': 5, 'received': 6, 'completed': 7, 'cancelled': 99
        }
        
        if new_status != 'cancelled' and status_order.get(new_status, 0) < status_order.get(old_status, 0):
            return jsonify({'error': '역방향 상태 전환은 불가합니다.'}), 400
            
        update_data = {'status': new_status}
        now_str = datetime.datetime.now().isoformat()
        
        if new_status == 'fee_paid':
            update_data['fee_paid_at'] = now_str
        elif new_status == 'mail_sent':
            update_data['mail_sent_at'] = now_str
        elif new_status == 'received':
            update_data['received_at'] = now_str
        elif new_status == 'completed':
            update_data['completed_at'] = now_str
            
        if mail_tracking_no is not None:
            update_data['mail_tracking_no'] = mail_tracking_no
        if notes is not None:
            update_data['notes'] = notes
            
        supabase.table('inquiry_requests').update(update_data).eq('id', request_id).execute()
        
        supabase.table('inquiry_status_logs').insert({
            'request_id': request_id,
            'status_from': old_status,
            'status_to': new_status,
            'changed_by': session.get('email'),
            'memo': f"상태가 {new_status}로 변경되었습니다."
        }).execute()
        
        logger.info("[EMAIL MOCK] 상태 변경 알림 메일 발송 -> 고객: %s, 변경상태: %s", req_res.data[0]['client_id'], new_status)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.exception("Update inquiry status error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/admin/inquiry/logs/<int:request_id>', methods=['GET'])
def get_inquiry_logs(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
        
    try:
        res = supabase.table('inquiry_status_logs').select('*').eq('request_id', request_id).order('changed_at', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        logger.exception("get_inquiry_logs error: %s", e)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/admin/inquiry/detail/<int:request_id>', methods=['PUT'])
def admin_update_inquiry_detail(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
    
    req_data = request.json
    updates = {}
    if 'mail_tracking_no' in req_data:
        updates['mail_tracking_no'] = req_data['mail_tracking_no']
    if 'notes' in req_data:
        updates['notes'] = req_data['notes']
        
    if updates:
        try:
            supabase.table('inquiry_requests').update(updates).eq('id', request_id).execute()
        except Exception as e:
            logger.exception("admin_update_inquiry_detail error: %s", e)
            return jsonify({'error': str(e)}), 500
        
    return jsonify({'success': True})

@api_bp.route('/api/admin/inquiry/export', methods=['GET'])
def admin_export_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return "Unauthorized", 401
    
    res = supabase.table('inquiry_requests').select('request_no, company_name, fiscal_year, inquiry_type, status, fee_amount, mail_tracking_no, created_at, financial_institutions(institution_name)').execute()
    data = res.data
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['신청번호', '회사명', '대상연도', '금융기관명', '조회방식', '상태', '등기추적번호', '신청일시'])
    for d in data:
        bank_name = d['financial_institutions']['institution_name'] if d.get('financial_institutions') else ''
        cw.writerow([
            d.get('request_no'), d.get('company_name'), d.get('fiscal_year'),
            bank_name, d.get('inquiry_type'), d.get('status'),
            d.get('mail_tracking_no'), d.get('created_at')
        ])
    
    output = '\ufeff' + si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inquiry_export.csv"}
    )
