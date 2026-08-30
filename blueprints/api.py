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

def _generate_fallback_cpa_stream(question: str, category: str, conversation_id: str):
    """우분투 서버 RAG/Dify 통신 장애 시 클라이언트에 무중단 회계기준 답변을 제공하는 로컬/LLM Fallback 스트리밍 생성기"""
    global openai_client
    logger.info("[FAQ Fallback] Activating local/LLM fallback stream for question: %s (Category: %s)", question, category)
    
    # 1. 로컬 RAG 검색 시도
    rag_context = ""
    sources_summary = []
    try:
        from core.audit_engine import query_k_gaap_rag
        matched_docs = query_k_gaap_rag(question, limit=3)
        if matched_docs:
            context_blocks = []
            for doc in matched_docs:
                src_label = f"{doc.get('standard_no', '')} {doc.get('paragraph_no', '')} ({doc.get('title', '')})".strip()
                sources_summary.append(src_label)
                context_blocks.append(f"[{src_label}]\n{doc.get('content', '')}")
            rag_context = "\n\n".join(context_blocks)
            logger.info("[FAQ Fallback] Retrieved %d fallback reference docs: %s", len(matched_docs), sources_summary)
    except Exception as re_err:
        logger.warning("[FAQ Fallback] Fallback local RAG query warning: %s", re_err)

    # 2. OpenAI 클라이언트 확보
    if not openai_client:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)

    # 3. OpenAI 직접 질의 스트리밍 시도
    if openai_client:
        try:
            system_prompt = (
                f"당신은 대한민국 공인회계사 및 회계감사 전문 AI 어시스턴트입니다.\n"
                f"사용자가 질문한 회계/세무/감사 기준({category})에 대해 명확하고 논리정연하게 답변해 주세요.\n"
                f"답변 형식: 1) 핵심 결론 요약, 2) 상세 규정 및 실무 적용 가이드, 3) 관련 기준서 조항 근거\n"
            )
            if rag_context:
                system_prompt += f"\n[참고 기준서 발췌 데이터]\n{rag_context}\n"

            logger.info("[FAQ Fallback] Calling OpenAI ChatCompletion stream...")
            completion = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                stream=True,
                temperature=0.2
            )

            for chunk in completion:
                delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
                if delta:
                    event_data = {
                        "event": "message",
                        "answer": delta,
                        "conversation_id": conversation_id
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n".encode('utf-8')

            # 출처 안내가 있을 경우 마무리 전송
            if sources_summary:
                src_text = "\n\n---\n**📚 관련 참고 기준서 근거:**\n" + "\n".join([f"- {s}" for s in sources_summary])
                yield f"data: {json.dumps({'event': 'message', 'answer': src_text, 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n".encode('utf-8')
            
            logger.info("[FAQ Fallback] OpenAI fallback stream completed successfully.")
            return
        except Exception as oai_err:
            logger.error("[FAQ Fallback] OpenAI API call failed: %s", oai_err, exc_info=True)

    # 4. LLM API까지 모두 불가할 때 최종 룰베이스 응답
    logger.warning("[FAQ Fallback] Returning rule-based fallback response.")
    base_msg = f"안녕하세요. 현재 외부 RAG 연동 서버 점검 중으로 내장 회계기준 검색 결과를 안내해 드립니다.\n\n"
    if rag_context:
        base_msg += f"**[관련 회계기준 발췌 조항]**\n{rag_context}\n\n상세한 자문은 1:1 담당 회계사 상담실을 이용해 주시기 바랍니다."
    else:
        base_msg += f"질문하신 '{question}'과 관련된 회계/감사 기준 적용에 대해서는 담당 공인회계사 1:1 자문 상담 창구를 통해 신속히 답변해 드리겠습니다."

    yield f"data: {json.dumps({'event': 'message', 'answer': base_msg, 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n".encode('utf-8')


@api_bp.route('/api/faq/ask', methods=['POST'])
def faq_ask():
    global openai_client, supabase
    
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    category = data.get('category', '전체')
    conversation_id = data.get('conversation_id', '').strip()

    logger.info("[API_REQ] POST /api/faq/ask - question: '%s', category: '%s', conv_id: '%s'", question, category, conversation_id)

    if not question:
        logger.warning("[API_RES] POST /api/faq/ask - Empty question provided.")
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    try:
        clean_q = question.replace(" ", "").lower()
        trivial_keywords = ["안녕", "반가워", "고마워", "수고", "감사", "안뇽", "하이", "hello"]
        swear_keywords = ["시발", "씨발", "개새끼", "미친", "존나", "좆", "병신"]
        
        if any(w in clean_q for w in swear_keywords):
            def generate_trivial():
                msg = "올바른 언어를 사용해주세요. 저는 회계감사 기준에 대해 답변해 드리는 AI입니다."
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id}, ensure_ascii=False)}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
            
        if len(clean_q) <= 10 and any(w in clean_q for w in trivial_keywords):
            def generate_trivial():
                msg = "안녕하세요! 혜안 파트너스 회계감사 AI 어시스턴트입니다. 회계 기준이나 감사 기준에 대해 무엇이든 물어보세요!"
                yield f'data: {json.dumps({"event": "message", "answer": msg, "conversation_id": conversation_id}, ensure_ascii=False)}\n\n'.encode('utf-8')
            return Response(stream_with_context(generate_trivial()), content_type='text/event-stream')
        
        dify_api_key = os.environ.get("DIFY_API_KEY", "app-mIeCNphyBVBn6diJpnybnzdS")
        dify_api_base_url = os.environ.get("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
        
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
        
        logger.info("[FAQ Ask] Requesting Dify API (%s)...", dify_api_base_url)
        dify_succeeded = False
        try:
            dify_response = requests.post(f"{dify_api_base_url}/chat-messages", json=payload, headers=headers, stream=True, timeout=8)
            if dify_response.status_code == 200:
                dify_succeeded = True
                logger.info("[API_RES] POST /api/faq/ask - Dify streaming response established.")
                def generate():
                    for line in dify_response.iter_lines():
                        if line:
                            yield line + b'\n\n'
                return Response(stream_with_context(generate()), content_type='text/event-stream')
            else:
                logger.warning("[FAQ Ask] Dify API returned status %s: %s", dify_response.status_code, dify_response.text)
        except Exception as dify_err:
            logger.warning("[FAQ Ask] Dify connection error or timeout: %s", dify_err)

        # Dify 실패 시 무중단 Fallback 스트림 활성화
        logger.info("[FAQ Ask] Initiating zero-downtime fallback stream...")
        return Response(stream_with_context(_generate_fallback_cpa_stream(question, category, conversation_id)), content_type='text/event-stream')

    except Exception as e:
        logger.error("[ERROR] POST /api/faq/ask exception: %s", e, exc_info=True)
        # 최종 예외 상황에서도 Fallback 스트림으로 안전하게 응답
        return Response(stream_with_context(_generate_fallback_cpa_stream(question, category, conversation_id)), content_type='text/event-stream')


@api_bp.route('/api/dify/retrieval', methods=['POST'])
def dify_retrieval():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    
    logger.info("[API_REQ] POST /api/dify/retrieval - Received query: %s", query)
    
    if not query:
        logger.warning("[API_RES] POST /api/dify/retrieval - Empty query received.")
        return jsonify({"records": []}), 200
        
    try:
        global openai_client
        if not openai_client:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                from openai import OpenAI
                openai_client = OpenAI(api_key=api_key)

        query_embedding = None
        if openai_client:
            try:
                embed_response = openai_client.embeddings.create(
                    input=query,
                    model="text-embedding-3-large",
                    dimensions=1536
                )
                query_embedding = embed_response.data[0].embedding
                logger.info("[Dify Retrieval] OpenAI embedding generated successfully.")
            except Exception as emb_e:
                logger.warning("[Dify Retrieval] OpenAI embedding error: %s", emb_e)

        initial_records = []
        documents_for_rerank = []

        # 1. Ubuntu ChromaDB 검색 시도
        if query_embedding:
            try:
                import chromadb
                host = os.environ.get("CHROMA_SERVER_HOST", "localhost")
                port = int(os.environ.get("CHROMA_SERVER_PORT", "8000"))
                logger.info("[Dify Retrieval] Connecting to ChromaDB at %s:%d...", host, port)
                
                chroma_client = chromadb.HttpClient(host=host, port=port)
                collection = chroma_client.get_collection(name="document_chunks")
                
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=20
                )
                
                if results and results.get('ids') and len(results['ids'][0]) > 0:
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
                    logger.info("[Dify Retrieval] Retrieved %d chunks from ChromaDB.", len(initial_records))
            except Exception as chroma_err:
                logger.warning("[Dify Retrieval] ChromaDB connection failed, trying fallback: %s", chroma_err)

        # 2. ChromaDB 결과가 없을 때 로컬 RAG Fallback 검색
        if not initial_records:
            logger.info("[Dify Retrieval] Fallback to core.audit_engine K-GAAP RAG...")
            try:
                from core.audit_engine import query_k_gaap_rag
                fallback_docs = query_k_gaap_rag(query, limit=5)
                for doc in fallback_docs:
                    content = f"[{doc.get('standard_no', 'K-GAAP')}] {doc.get('title', '')}\n{doc.get('content', '')}"
                    initial_records.append({
                        "content": content,
                        "score": float(doc.get("score", 0.5))
                    })
                    documents_for_rerank.append(content)
                logger.info("[Dify Retrieval] Local RAG retrieved %d records.", len(initial_records))
            except Exception as fb_err:
                logger.error("[Dify Retrieval] Fallback RAG search failed: %s", fb_err)

        final_records = []
        if documents_for_rerank:
            cohere_api_key = os.environ.get("COHERE_API_KEY")
            if cohere_api_key:
                try:
                    import cohere
                    logger.info("[Dify Retrieval] Reranking results with Cohere...")
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
                except Exception as ce:
                    logger.warning("[Dify Retrieval] Cohere Rerank failed: %s", ce)
                    initial_records.sort(key=lambda x: x["score"], reverse=True)
                    final_records = initial_records[:5]
            else:
                initial_records.sort(key=lambda x: x["score"], reverse=True)
                final_records = initial_records[:5]
        else:
            final_records = initial_records[:5]
            
        logger.info("[API_RES] POST /api/dify/retrieval - Returning %d records.", len(final_records))
        return jsonify({"records": final_records}), 200
        
    except Exception as e:
        logger.error("[ERROR] POST /api/dify/retrieval exception: %s", e, exc_info=True)
        return jsonify({"records": []}), 200


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
