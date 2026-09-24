# -*- coding: utf-8 -*-
import os
import csv
import json
import time
import re
import io
import mimetypes
import datetime
import requests
from io import StringIO
from flask import Blueprint, request, jsonify, session, Response, stream_with_context, send_from_directory, send_file, current_app
from werkzeug.utils import secure_filename
from core.extensions import (
    supabase, openai_client, s3_client, minio_endpoint, get_safe_path_name, MASTER_EMAIL, logger
)

api_bp = Blueprint('api', __name__)

def _generate_fallback_cpa_stream(question: str, category: str, conversation_id: str):
    """우분투 서버 RAG/Dify 연동 시 클라이언트에 고품질 회계기준+감사조서 답변을 제공하는 실시간 스트리밍 생성기"""
    global openai_client
    logger.info("[FAQ RAG] Activating dual RAG stream for question: '%s' (Category: %s)", question, category)
    
    # 1. 듀얼 RAG 지식 검색 (기준서 + 감사절차 템플릿)
    rag_context = ""
    sources_summary = []
    try:
        from core.rag_retriever import query_dual_rag
        retrieval_res = query_dual_rag(question, top_k_std=3, top_k_proc=3)
        rag_context = retrieval_res.get("combined_context", "")
        sources_summary = retrieval_res.get("sources_summary", [])
        logger.info("[FAQ RAG] Retrieved %d reference chunks in %.3f sec", len(sources_summary), retrieval_res.get("elapsed_seconds", 0))
    except Exception as re_err:
        logger.warning("[FAQ RAG] Dual RAG retrieval warning: %s", re_err, exc_info=True)

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
                f"당신은 대한민국 최고 수준의 공인회계사(CPA) 및 회계감사 전문 AI 어시스턴트입니다.\n"
                f"사용자가 질문한 회계/세무/감사 주제({category})에 대해 명확하고 논리정연하며 실무에 즉시 적용 가능한 답변을 작성해 주세요.\n\n"
                f"[답변 작성 원칙]\n"
                f"1. **핵심 결론 요약**: 질문에 대한 회계처리 또는 감사 결론을 2~3줄로 명확히 제시.\n"
                f"2. **회계기준서 규정 해설**: 관련 기준서(K-IFRS 또는 K-GAAP 일반기준)의 주요 조항 및 이론적 근거를 설명.\n"
                f"3. **실제 감사조서 절차 및 서식 안내**: 제공된 감사조서 템플릿 코드(예: C-0, P-0 등)와 단계별 실증감사절차, 마크다운 표 서식을 상세히 안내.\n"
                f"4. **실무 유의사항 및 체크포인트**: 감사 현장에서 주의해야 할 경영진 주장(실재성, 완전성, 평가 등)과 증빙 확인 요령 안내.\n"
            )
            if rag_context:
                system_prompt += f"\n[신뢰할 수 있는 사내 DB 발췌 근거 데이터]\n{rag_context}\n"

            logger.info("[FAQ RAG] Calling OpenAI ChatCompletion stream (gpt-4o-mini)...")
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
                src_text = "\n\n---\n**📚 관련 참고 기준서 및 감사조서 서식 근거:**\n" + "\n".join([f"- {s}" for s in sources_summary])
                yield f"data: {json.dumps({'event': 'message', 'answer': src_text, 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n".encode('utf-8')
            
            logger.info("[FAQ RAG] Dual RAG response stream completed successfully.")
            return
        except Exception as oai_err:
            logger.error("[FAQ RAG] OpenAI API stream failed: %s", oai_err, exc_info=True)

    # 4. LLM API까지 모두 불가할 때 최종 룰베이스 응답
    logger.warning("[FAQ RAG] Returning rule-based fallback response.")
    base_msg = f"안녕하세요. 현재 회계기준/감사조서 검색 결과를 안내해 드립니다.\n\n"
    if rag_context:
        base_msg += f"**[관련 회계기준 및 감사조서 발췌]**\n{rag_context}\n\n상세한 자문은 1:1 담당 회계사 상담실을 이용해 주시기 바랍니다."
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
        from core.rag_retriever import query_dual_rag
        retrieval_res = query_dual_rag(query, top_k_std=5, top_k_proc=5)
        
        initial_records = []
        documents_for_rerank = []
        
        # 1. 기준서 청크 수집
        for std in retrieval_res.get("standards", []):
            content = f"[{std['category']}] {std['document_id']} ({std['article_title']})\n{std['content']}"
            initial_records.append({
                "content": content,
                "score": std.get("similarity", 0.5)
            })
            documents_for_rerank.append(content)
            
        # 2. 감사절차 청크 수집
        for proc in retrieval_res.get("procedures", []):
            content = f"[{proc['section_name']}/{proc['sub_category']}] {proc['template_id']} - 절차 {proc['step_no']}\n{proc['content']}"
            initial_records.append({
                "content": content,
                "score": proc.get("similarity", 0.5)
            })
            documents_for_rerank.append(content)

        logger.info("[Dify Retrieval] Total %d raw chunks retrieved from dual RAG engine.", len(initial_records))

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


DEFAULT_FINANCIAL_INSTITUTIONS = [
    {"id": 1, "institution_name": "KB국민은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 2, "institution_name": "신한은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 3, "institution_name": "우리은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 4, "institution_name": "하나은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 5, "institution_name": "NH농협은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 6, "institution_name": "IBK기업은행", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 7, "institution_name": "카카오뱅크", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 8, "institution_name": "토스뱅크", "form_type": "bank", "inquiry_type": "online", "fee": 0, "is_active": True},
    {"id": 9, "institution_name": "KDB산업은행", "form_type": "bank", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 10, "institution_name": "한국수출입은행", "form_type": "bank", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 11, "institution_name": "삼성화재", "form_type": "insurance", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 12, "institution_name": "현대해상", "form_type": "insurance", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 13, "institution_name": "미래에셋증권", "form_type": "securities", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 14, "institution_name": "한국투자증권", "form_type": "securities", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 15, "institution_name": "신한카드", "form_type": "card", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 16, "institution_name": "삼성카드", "form_type": "card", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 17, "institution_name": "신용보증기금", "form_type": "other", "inquiry_type": "paper", "fee": 0, "is_active": True},
    {"id": 18, "institution_name": "기술보증기금", "form_type": "other", "inquiry_type": "paper", "fee": 0, "is_active": True},
]
_in_memory_inquiries = []
_in_memory_inquiry_logs = []

@api_bp.route('/api/financial_institutions', methods=['GET'])
def get_financial_institutions():
    logger.info("[API_REQ] GET /api/financial_institutions")
    if supabase:
        try:
            logger.debug("[DB_CALL] Querying financial_institutions from Supabase")
            res = supabase.table('financial_institutions').select('*').eq('is_active', True).execute()
            if res.data:
                logger.info("[API_RES] GET /api/financial_institutions - %d institutions fetched from DB", len(res.data))
                return jsonify(res.data)
        except Exception as e:
            logger.warning("[WARN] Supabase financial_institutions query fallback to default list: %s", e)
    
    logger.info("[API_RES] GET /api/financial_institutions - Returning %d default institutions", len(DEFAULT_FINANCIAL_INSTITUTIONS))
    return jsonify(DEFAULT_FINANCIAL_INSTITUTIONS)

@api_bp.route('/api/inquiry/new', methods=['POST'])
def new_inquiry_request():
    if 'email' not in session:
        logger.warning("[API_REQ] POST /api/inquiry/new - Unauthorized")
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    client_id = session.get('email')
    company_name = data.get('company_name')
    fiscal_year = data.get('fiscal_year')
    institution_id = data.get('institution_id')
    inquiry_type = data.get('inquiry_type')
    
    logger.info("[API_REQ] POST /api/inquiry/new - Client: %s, Company: %s, Year: %s, Inst: %s, Type: %s",
                client_id, company_name, fiscal_year, institution_id, inquiry_type)
    
    if not all([company_name, fiscal_year, institution_id, inquiry_type]):
        return jsonify({'error': 'Missing required fields'}), 400

    now = datetime.datetime.now()
    prefix = f"INQ-{now.strftime('%Y%m')}-"
    
    inst_lookup = {item['id']: item for item in DEFAULT_FINANCIAL_INSTITUTIONS}
    inst_data = inst_lookup.get(int(institution_id) if str(institution_id).isdigit() else 0, {
        'institution_name': f'금융기관({institution_id})', 'form_type': 'bank', 'inquiry_type': inquiry_type
    })

    if supabase:
        try:
            inst_res = supabase.table('financial_institutions').select('*').eq('id', institution_id).execute()
            if inst_res.data:
                inst_data = inst_res.data[0]
                if inst_data.get('inquiry_type') == 'online' and inquiry_type == 'paper':
                    return jsonify({'error': 'This institution only supports online inquiry.'}), 400
            
            latest_res = supabase.table('inquiry_requests').select('request_no').ilike('request_no', f"{prefix}%").order('request_no', desc=True).limit(1).execute()
            new_seq = 1
            if latest_res.data:
                latest_no = latest_res.data[0]['request_no']
                try:
                    new_seq = int(latest_no.split('-')[2]) + 1
                except Exception:
                    new_seq = len(_in_memory_inquiries) + 1
                
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
            if insert_res.data:
                new_request_id = insert_res.data[0]['id']
                try:
                    supabase.table('inquiry_status_logs').insert({
                        'request_id': new_request_id,
                        'status_from': 'draft',
                        'status_to': 'submitted',
                        'changed_by': client_id,
                        'memo': '신청서 작성 완료'
                    }).execute()
                except Exception as log_err:
                    logger.warning("[WARN] Supabase inquiry_status_logs insert fallback: %s", log_err)
                
                logger.info("[API_RES] POST /api/inquiry/new - Successfully created request_no=%s via Supabase", request_no)
                return jsonify({'success': True, 'request_no': request_no})
        except Exception as e:
            logger.warning("[WARN] Supabase new inquiry request error, fallback to in-memory: %s", e)
    
    # Fallback to in-memory
    new_seq = len(_in_memory_inquiries) + 1
    request_no = f"{prefix}{new_seq:04d}"
    in_mem_item = {
        'id': new_seq,
        'request_no': request_no,
        'client_id': client_id,
        'company_name': company_name,
        'fiscal_year': int(fiscal_year),
        'institution_id': institution_id,
        'inquiry_type': inquiry_type,
        'status': 'submitted',
        'created_at': now.isoformat(),
        'financial_institutions': inst_data
    }
    _in_memory_inquiries.append(in_mem_item)
    _in_memory_inquiry_logs.append({
        'id': len(_in_memory_inquiry_logs) + 1,
        'request_id': new_seq,
        'status_from': 'draft',
        'status_to': 'submitted',
        'changed_by': client_id,
        'changed_at': now.isoformat(),
        'memo': '신청서 작성 완료'
    })
    logger.info("[API_RES] POST /api/inquiry/new - In-memory inquiry created: request_no=%s", request_no)
    return jsonify({'success': True, 'request_no': request_no})

@api_bp.route('/api/inquiry/status', methods=['GET'])
def get_inquiry_status():
    if 'email' not in session:
        logger.warning("[API_REQ] GET /api/inquiry/status - Unauthorized")
        return jsonify({'error': 'Unauthorized'}), 401
    
    email = session.get('email')
    logger.info("[API_REQ] GET /api/inquiry/status - Client: %s", email)
    
    if supabase:
        try:
            logger.debug("[DB_CALL] Querying inquiry_requests for client: %s", email)
            res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').eq('client_id', email).order('created_at', desc=True).execute()
            if res.data is not None:
                logger.info("[API_RES] GET /api/inquiry/status - %d records returned from DB", len(res.data))
                return jsonify(res.data)
        except Exception as e:
            logger.warning("[WARN] Supabase get_inquiry_status fallback to in-memory: %s", e)
            
    matched = [item for item in _in_memory_inquiries if item.get('client_id') == email or email == MASTER_EMAIL]
    logger.info("[API_RES] GET /api/inquiry/status - Returning %d in-memory records", len(matched))
    return jsonify(matched)

@api_bp.route('/api/inquiry/download_form/<int:request_id>', methods=['GET'])
def download_inquiry_form(request_id):
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    form_type = 'bank'
    found_item = None
    
    if supabase:
        try:
            req_res = supabase.table('inquiry_requests').select('*, financial_institutions(form_type)').eq('id', request_id).execute()
            if req_res.data:
                found_item = req_res.data[0]
                if session.get('email') != found_item['client_id'] and session.get('email') != MASTER_EMAIL:
                    return jsonify({'error': 'Unauthorized'}), 401
                if found_item.get('financial_institutions'):
                    form_type = found_item['financial_institutions'].get('form_type', 'bank')
        except Exception as e:
            logger.warning("[WARN] Supabase download_inquiry_form lookup fallback: %s", e)
            
    if not found_item:
        in_mem_matches = [x for x in _in_memory_inquiries if x['id'] == request_id]
        if in_mem_matches:
            found_item = in_mem_matches[0]
            if session.get('email') != found_item['client_id'] and session.get('email') != MASTER_EMAIL:
                return jsonify({'error': 'Unauthorized'}), 401
            if found_item.get('financial_institutions'):
                form_type = found_item['financial_institutions'].get('form_type', 'bank')

    forms_dir = os.path.join(current_app.root_path, 'static', 'forms')
    if not os.path.exists(forms_dir):
        os.makedirs(forms_dir, exist_ok=True)
        
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
            f.write(f"이 파일은 {filename} 양식 다운로드 파일입니다.")
            
    return send_from_directory(forms_dir, filename, as_attachment=True)


@api_bp.route('/api/admin/inquiry', methods=['GET'])
@api_bp.route('/api/admin/inquiry/list', methods=['GET'])
def get_all_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if supabase:
        try:
            res = supabase.table('inquiry_requests').select('*, financial_institutions(institution_name, form_type)').order('created_at', desc=True).execute()
            if res.data is not None:
                return jsonify(res.data)
        except Exception as e:
            logger.warning("[WARN] Supabase get_all_inquiries fallback: %s", e)
            
    return jsonify(_in_memory_inquiries)

@api_bp.route('/api/admin/inquiry/update_status', methods=['POST'])
@api_bp.route('/api/admin/inquiry/status', methods=['POST'])
def update_inquiry_status():
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    request_id = data.get('request_id')
    new_status = data.get('status')
    mail_tracking_no = data.get('mail_tracking_no')
    notes = data.get('notes')
    
    if not request_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400

    now_str = datetime.datetime.now().isoformat()
    if supabase:
        try:
            req_res = supabase.table('inquiry_requests').select('*').eq('id', request_id).execute()
            if req_res.data:
                old_status = req_res.data[0]['status']
                update_data = {'status': new_status}
                if new_status == 'fee_paid': update_data['fee_paid_at'] = now_str
                elif new_status == 'mail_sent': update_data['mail_sent_at'] = now_str
                elif new_status == 'received': update_data['received_at'] = now_str
                elif new_status == 'completed': update_data['completed_at'] = now_str
                if mail_tracking_no is not None: update_data['mail_tracking_no'] = mail_tracking_no
                if notes is not None: update_data['notes'] = notes
                
                supabase.table('inquiry_requests').update(update_data).eq('id', request_id).execute()
                try:
                    supabase.table('inquiry_status_logs').insert({
                        'request_id': request_id,
                        'status_from': old_status,
                        'status_to': new_status,
                        'changed_by': session.get('email'),
                        'memo': f"상태가 {new_status}로 변경되었습니다."
                    }).execute()
                except Exception:
                    pass
                return jsonify({'success': True})
        except Exception as e:
            logger.warning("[WARN] Supabase update_inquiry_status fallback: %s", e)

    # In-memory update
    for item in _in_memory_inquiries:
        if str(item.get('id')) == str(request_id):
            item['status'] = new_status
            if mail_tracking_no is not None: item['mail_tracking_no'] = mail_tracking_no
            if notes is not None: item['notes'] = notes
            break
            
    return jsonify({'success': True})

@api_bp.route('/api/admin/inquiry/logs/<int:request_id>', methods=['GET'])
@api_bp.route('/api/admin/inquiry/history/<int:request_id>', methods=['GET'])
def get_inquiry_logs(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if supabase:
        try:
            res = supabase.table('inquiry_status_logs').select('*').eq('request_id', request_id).order('changed_at', desc=True).execute()
            if res.data is not None:
                return jsonify(res.data)
        except Exception as e:
            logger.warning("[WARN] Supabase get_inquiry_logs fallback: %s", e)
            
    matched = [l for l in _in_memory_inquiry_logs if l.get('request_id') == request_id]
    return jsonify(matched)

@api_bp.route('/api/admin/inquiry/detail/<int:request_id>', methods=['GET', 'PUT'])
def admin_update_inquiry_detail(request_id):
    if session.get('email') != MASTER_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        for item in _in_memory_inquiries:
            if item.get('id') == request_id:
                return jsonify(item)
        if supabase:
            try:
                res = supabase.table('inquiry_requests').select('*, financial_institutions(*)').eq('id', request_id).execute()
                if res.data:
                    return jsonify(res.data[0])
            except Exception as e:
                logger.warning("[WARN] Supabase get inquiry detail fallback: %s", e)
        return jsonify({'error': 'Not found'}), 404
        
    req_data = request.json or {}
    updates = {}
    if 'mail_tracking_no' in req_data:
        updates['mail_tracking_no'] = req_data['mail_tracking_no']
    if 'notes' in req_data:
        updates['notes'] = req_data['notes']
        
    if updates and supabase:
        try:
            supabase.table('inquiry_requests').update(updates).eq('id', request_id).execute()
        except Exception as e:
            logger.warning("[WARN] admin_update_inquiry_detail DB fallback: %s", e)
            
    for item in _in_memory_inquiries:
        if item.get('id') == request_id:
            item.update(updates)
            break
        
    return jsonify({'success': True})

@api_bp.route('/api/admin/inquiry/export', methods=['GET'])
def admin_export_inquiries():
    if session.get('email') != MASTER_EMAIL:
        return "Unauthorized", 401
    
    data = []
    if supabase:
        try:
            res = supabase.table('inquiry_requests').select('request_no, company_name, fiscal_year, inquiry_type, status, fee_amount, mail_tracking_no, created_at, financial_institutions(institution_name)').execute()
            data = res.data or []
        except Exception as e:
            logger.warning("[WARN] Supabase admin_export_inquiries fallback: %s", e)
            
    if not data:
        data = _in_memory_inquiries
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['신청번호', '회사명', '대상연도', '금융기관명', '조회방식', '상태', '등기추적번호', '신청일시'])
    for d in data:
        bank_name = d.get('financial_institutions', {}).get('institution_name', '') if isinstance(d.get('financial_institutions'), dict) else ''
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


@api_bp.route('/api/calendar/notion.ics', methods=['GET'])
@api_bp.route('/calendar/notion.ics', methods=['GET'])
def get_notion_calendar_ics():
    """
    구글 캘린더 등 외부 캘린더 앱에서 노션 일정을 실시간 구독할 수 있는 RFC 5545 iCal (.ics) 피드를 제공합니다.
    """
    logger.info("[CALENDAR_FEED] iCal feed requested from IP: %s, User-Agent: %s", 
                request.remote_addr, request.headers.get('User-Agent', 'Unknown'))
    
    force_refresh = request.args.get('refresh', '').lower() in ('true', '1', 'yes') or request.args.get('force', '').lower() in ('true', '1')
    category_filter = request.args.get('category', '').strip()
    audit_type_filter = request.args.get('audit_type', '').strip() or request.args.get('audit', '').strip()
    status_filter = request.args.get('status', '').strip()
    exclude_completed = request.args.get('exclude_completed', '').lower() in ('true', '1', 'yes')

    try:
        from core.notion_calendar import fetch_notion_schedule_events, generate_ical_feed
        events = fetch_notion_schedule_events(force_refresh=force_refresh)

        # 필터링 적용 (감사구분, 세부내역 카테고리, 상태, 완료 여부)
        if audit_type_filter:
            events = [e for e in events if audit_type_filter in (e.get('audit_types') or [])]
        if category_filter:
            events = [e for e in events if e.get('category') == category_filter]
        if status_filter:
            events = [e for e in events if e.get('status') == status_filter]
        if exclude_completed:
            events = [e for e in events if not e.get('completed') and e.get('status') != '완료']

        cal_name = f"노션 일정 - {audit_type_filter}" if audit_type_filter else "노션 일정 (Todo DB)"
        ics_content = generate_ical_feed(events, calendar_name=cal_name)
        logger.info("[CALENDAR_FEED] Returning iCal feed with %d events (audit_type=%s, force_refresh=%s)", 
                    len(events), audit_type_filter, force_refresh)

        return Response(
            ics_content,
            mimetype='text/calendar; charset=utf-8',
            headers={
                'Content-Disposition': 'inline; filename="notion_calendar.ics"',
                'Cache-Control': 'public, max-age=300'
            }
        )
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        logger.error("[CALENDAR_FEED] Notion API error (status: %s): %s", status_code, exc, exc_info=True)
        return Response(
            f"Notion API 연동 오류: 상태코드 {status_code}",
            status=502,
            mimetype="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error("[CALENDAR_FEED] Unexpected error during iCal feed generation: %s", e, exc_info=True)
        return Response(
            f"일정 피드 생성 중 오류 발생: {str(e)}",
            status=500,
            mimetype="text/plain; charset=utf-8"
        )


@api_bp.route('/api/upload-single-file', methods=['POST'])
@api_bp.route('/api/company/upload-single-file', methods=['POST'])
def upload_single_file():
    """
    개별 서류 항목 선택 시 파일을 MinIO와 Supabase DB에 즉시 비동기 업로드하는 엔드포인트
    """
    try:
        if 'email' not in session:
            logger.warning("[UPLOAD_SINGLE:AUTH_FAIL] Unauthorized upload attempt")
            return jsonify({'success': False, 'error': '로그인이 필요합니다.'}), 401

        email = session.get('email')
        user_company = session.get('company', '')
        is_master = (email == MASTER_EMAIL or session.get('role') == 'master')

        req_company = request.form.get('company_name', '').strip()
        if is_master and req_company:
            target_company = req_company
        else:
            target_company = user_company or req_company

        if not target_company:
            return jsonify({'success': False, 'error': '회사 정보가 확인되지 않았습니다.'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '업로드할 파일이 전달되지 않았습니다.'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': '선택된 파일이 없습니다.'}), 400

        field_name = request.form.get('field_name', 'other_current').strip()
        label = request.form.get('label', '').strip()
        fiscal_year = request.form.get('fiscal_year', '').strip() or '2025'
        original_filename = os.path.basename(file.filename)
        safe_filename = get_safe_path_name(original_filename)
        safe_company = get_safe_path_name(target_company)

        # 기준 사업연도별 폴더 구분자 산출 (예: 혜안_임시/2025/Temp/Temp_L)
        if field_name.startswith('pfile_'):
            year_folder = f"{fiscal_year}/P-File"
        elif 'finance' in field_name:
            year_folder = f"{fiscal_year}/Ext_F"
        elif 'partner' in field_name:
            year_folder = f"{fiscal_year}/Ext_C"
        elif 'current' in field_name:
            year_folder = f"{fiscal_year}/Temp/Temp_P"
        else:
            year_folder = f"{fiscal_year}/Temp/Temp_L"

        timestamp = int(time.time() * 1000)
        file_key = f"{safe_company}/{year_folder}/{timestamp}_{field_name}_{safe_filename}"
        file_bytes = file.read()
        file_url = None
        bucket_name = 'company-uploads'

        logger.info("[UPLOAD_SINGLE:START] User=%s, Company=%s, Year=%s, Field=%s (%s), Filename=%s, Size=%d bytes, S3Key=%s",
                    email, target_company, fiscal_year, field_name, label, original_filename, len(file_bytes), file_key)

        # 1. MinIO 업로드
        if s3_client:
            try:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_key,
                    Body=file_bytes,
                    ContentType=file.content_type or 'application/octet-stream'
                )
                file_url = f"{minio_endpoint}/{bucket_name}/{file_key}"
                logger.info("[UPLOAD_SINGLE:MINIO_OK] Uploaded to MinIO: %s", file_url)
            except Exception as minio_err:
                logger.warning("[UPLOAD_SINGLE:MINIO_WARN] Primary put_object failed (%s). Retrying with bucket creation...", minio_err)
                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=file_key,
                        Body=file_bytes,
                        ContentType=file.content_type or 'application/octet-stream'
                    )
                    file_url = f"{minio_endpoint}/{bucket_name}/{file_key}"
                    logger.info("[UPLOAD_SINGLE:MINIO_RETRY_OK] Uploaded to MinIO after bucket creation: %s", file_url)
                except Exception as retry_err:
                    logger.error("[UPLOAD_SINGLE:MINIO_ERROR] MinIO upload completely failed: %s", retry_err, exc_info=True)
        else:
            logger.warning("[UPLOAD_SINGLE:MINIO_SKIP] s3_client not available")

        # 2. Supabase DB 기록
        db_filename = f"[{label}] {original_filename}" if label else original_filename
        formatted_help = f"[{fiscal_year}년도] [{label}] 상태: 제출 (즉시 업로드)"
        inserted_id = None

        if supabase:
            try:
                insert_data = {
                    'company_name': target_company,
                    'uploaded_by': email,
                    'file_name': db_filename,
                    'file_url': file_url,
                    'help_text': formatted_help
                }
                res = supabase.table('company_files').insert(insert_data).execute()
                if res.data and len(res.data) > 0:
                    inserted_id = res.data[0].get('id')
                logger.info("[UPLOAD_SINGLE:DB_OK] Supabase company_files inserted successfully. ID: %s", inserted_id)
            except Exception as db_err:
                logger.error("[UPLOAD_SINGLE:DB_ERROR] Supabase company_files insert failed: %s", db_err, exc_info=True)

        # 3. 사내 우분투 MinIO Lakehouse (Normalized/data.json) 비동기 자동 동기화 트리거
        try:
            import threading
            from core.storage_manager import storage_manager
            fy_int = int(fiscal_year) if fiscal_year and str(fiscal_year).isdigit() else 2025
            threading.Thread(
                target=storage_manager.sync_normalized_lakehouse,
                args=(target_company, fy_int),
                daemon=True
            ).start()
            logger.info("[UPLOAD_SINGLE:SYNC_TRIGGERED] Background lakehouse sync thread spawned for %s (FY %s)", target_company, fy_int)
        except Exception as sync_trigger_err:
            logger.warning("[UPLOAD_SINGLE:SYNC_WARN] Failed to spawn background lakehouse sync thread: %s", sync_trigger_err)

        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        return jsonify({
            'success': True,
            'id': inserted_id,
            'company_name': target_company,
            'field_name': field_name,
            'label': label,
            'file_name': original_filename,
            'db_filename': db_filename,
            'file_url': file_url,
            'uploaded_at': now_str
        })
    except Exception as e:
        logger.error("[UPLOAD_SINGLE:UNHANDLED_ERROR] %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'서버 처리 오류: {str(e)}'}), 500


_s3_unavailable_until = 0

def check_storage_file_exists(file_url: str) -> bool:
    """
    우분투 MinIO S3 또는 스토리지에 실제 물리적 파일이 존재하는지 빠르게 검증하는 헬퍼 함수
    (네트워크 장애/타임아웃 시 0.01초 내 Fast-Fail 및 Graceful Fallback 적용)
    """
    import time
    global _s3_unavailable_until
    if not file_url:
        return False

    is_minio_url = (minio_endpoint in file_url) or ('company-uploads/' in file_url) or ('audit-lakehouse/' in file_url)

    # 1. MinIO S3 head_object 확인 (서킷 브레이커: 최근 30초 내 S3 지연/장애 시 DB 레코드 즉시 신뢰)
    now = time.time()
    if s3_client and now > _s3_unavailable_until:
        s3_key = None
        bucket_to_use = 'company-uploads'
        if 'company-uploads/' in file_url:
            s3_key = file_url.split('company-uploads/')[-1]
            bucket_to_use = 'company-uploads'
        elif 'audit-lakehouse/' in file_url:
            s3_key = file_url.split('audit-lakehouse/')[-1]
            bucket_to_use = 'audit-lakehouse'
        elif file_url.startswith('http'):
            path_part = file_url.replace(minio_endpoint, '').lstrip('/')
            parts = path_part.split('/', 1)
            if len(parts) == 2:
                bucket_to_use, s3_key = parts[0], parts[1]
            else:
                s3_key = path_part
        else:
            s3_key = file_url

        if s3_key:
            try:
                s3_client.head_object(Bucket=bucket_to_use, Key=s3_key)
                return True
            except Exception as e:
                err_str = str(e).lower()
                # 명시적 404 / NoSuchKey인 경우에만 파일 없음 판정
                if '404' in err_str or 'nosuchkey' in err_str or 'not found' in err_str:
                    if bucket_to_use != 'audit-lakehouse':
                        try:
                            s3_client.head_object(Bucket='audit-lakehouse', Key=s3_key)
                            return True
                        except Exception as e2:
                            err_str2 = str(e2).lower()
                            if '404' in err_str2 or 'nosuchkey' in err_str2 or 'not found' in err_str2:
                                return False
                    else:
                        return False
                else:
                    # Connection error, timeout 등의 인프라 지연 발생 시: 30초 동안 S3 재시도 차단 & DB 레코드 통과
                    _s3_unavailable_until = now + 30
                    logger.warning("[STORAGE:CIRCUIT_BREAKER] S3 unreachable (%s). Fast-passing files for 30s.", e)
                    return True

    # 2. Supabase Storage 또는 일반 외부 HTTP URL 확인
    if not is_minio_url and file_url.startswith('http'):
        return True

    # 3. 기본적으로 유효한 URL 경로가 있으면 True 반환 (사용자 경험 보호)
    return True if file_url else False


@api_bp.route('/api/company/recent-submissions/<path:company_name>', methods=['GET'])
@api_bp.route('/api/company/recent-submissions', methods=['GET'])
def get_recent_submissions(company_name=None):
    """
    해당 고객사가 업로드한 최근 제출 서류 목록(최신 5건)을 실시간으로 반환하는 API
    """
    try:
        target_company = company_name or request.args.get('company_name', '').strip()
        if not target_company and 'company' in session:
            target_company = session.get('company', '')

        if not target_company:
            logger.warning("[RECENT_SUBMISSIONS:WARN] Missing company_name")
            return jsonify({'success': False, 'error': '회사명이 제공되지 않았습니다.'}), 400

        target_year = request.args.get('fiscal_year', '').strip() or request.args.get('year', '').strip() or '2025'

        logger.info("[RECENT_SUBMISSIONS:REQ] Fetching recent submissions for company: %s, fiscal_year: %s", target_company, target_year)

        recent_files = []
        if supabase:
            try:
                # DB 이력에서 최신순으로 조회 후, 우분투 서버에 실존하며 해당 감사연도(또는 P-File)인 파일만 최대 5건 선별
                res = supabase.table('company_files').select('*').eq('company_name', target_company).order('created_at', desc=True).limit(100).execute()
                raw_files = res.data or []

                for f in raw_files:
                    file_url_path = f.get('file_url')
                    if not file_url_path:
                        continue

                    # 우분투 서버(MinIO S3/스토리지) 실존 여부 즉시 검증
                    if not check_storage_file_exists(file_url_path):
                        logger.debug("[RECENT_SUBMISSIONS:SKIP_GHOST] Skipping non-existing file: ID=%s, URL=%s", f.get('id'), file_url_path)
                        continue

                    fn = f.get('file_name', '')
                    ht = f.get('help_text', '')

                    # P-File (영구문서) 여부 확인
                    is_pfile = ('P-File' in file_url_path) or ('pfile_' in file_url_path) or ('[PBC-P-' in fn) or ('회사기본사항' in ht)

                    # 해당 연도 파일 여부 확인
                    year_tag = f"[{target_year}년도]"
                    year_path = f"/{target_year}/"
                    is_this_year = (year_path in file_url_path) or (year_tag in ht)

                    # 과거 연도 태그가 없던 레코드는 2025년도 기본 귀속
                    if not is_this_year and not is_pfile:
                        has_other_year = any(f"/{y}/" in file_url_path or f"[{y}년도]" in ht for y in ['2023', '2024', '2026', '2027', '2028', '2029', '2030'])
                        if not has_other_year and target_year == '2025':
                            is_this_year = True

                    if not (is_pfile or is_this_year):
                        continue

                    public_url = '#'
                    if file_url_path.startswith('http'):
                        public_url = file_url_path
                    else:
                        try:
                            public_url = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                        except Exception:
                            public_url = file_url_path

                    # 날짜 포맷 정리 (예: 2026-09-21T16:00:00 -> 2026-09-21 16:00)
                    created_at_raw = f.get('created_at', '')
                    formatted_date = ''
                    if created_at_raw:
                        formatted_date = created_at_raw.replace('T', ' ')[:16]

                    raw_file_name = f.get('file_name', '파일명 없음')
                    clean_file_name = re.sub(r'\[PBC-P-\d+\]\s*', '', raw_file_name) if raw_file_name else ''

                    recent_files.append({
                        'id': f.get('id'),
                        'file_name': clean_file_name,
                        'created_at': formatted_date,
                        'status': f.get('status') or '제출완료',
                        'public_url': public_url,
                        'help_text': f.get('help_text', '')
                    })

                    if len(recent_files) >= 5:
                        break

                logger.info("[RECENT_SUBMISSIONS:RES] Successfully fetched %d verified files for %s (Year: %s)", len(recent_files), target_company, target_year)
            except Exception as db_err:
                logger.error("[RECENT_SUBMISSIONS:DB_ERROR] Failed to fetch company files: %s", db_err, exc_info=True)
                return jsonify({'success': False, 'error': '데이터베이스 조회 중 오류가 발생했습니다.'}), 500
        else:
            logger.warning("[RECENT_SUBMISSIONS:WARN] Supabase client not initialized")

        return jsonify({
            'success': True,
            'company_name': target_company,
            'fiscal_year': target_year,
            'files': recent_files
        })
    except Exception as e:
        logger.error("[RECENT_SUBMISSIONS:UNHANDLED_ERROR] %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'서버 처리 오류: {str(e)}'}), 500


@api_bp.route('/api/company/download/<int:file_id>', methods=['GET'])
@api_bp.route('/api/company/download-file', methods=['GET'])
def download_company_file(file_id=None):
    """
    고객사 제출 서류를 MinIO S3 또는 Supabase Storage에서 안전하게 다운로드 제공하는 프록시 엔드포인트
    """
    try:
        req_file_id = file_id or request.args.get('file_id')
        req_file_url = request.args.get('file_url', '').strip()
        req_file_name = request.args.get('file_name', '').strip()

        file_record = None
        if req_file_id and supabase:
            try:
                res = supabase.table('company_files').select('*').eq('id', req_file_id).execute()
                if res.data and len(res.data) > 0:
                    file_record = res.data[0]
            except Exception as dberr:
                logger.warning("[DOWNLOAD:DB_WARN] Could not fetch record for id %s: %s", req_file_id, dberr)

        file_url = (file_record.get('file_url') if file_record else req_file_url) or ''
        raw_file_name = (file_record.get('file_name') if file_record else req_file_name) or 'downloaded_file'

        # 파일명에서 대괄호 라벨 제거 및 깨끗한 파일명 생성
        clean_file_name = re.sub(r'\[.*?\]\s*', '', raw_file_name).strip()
        if not clean_file_name:
            clean_file_name = 'document'

        if not file_url:
            logger.warning("[DOWNLOAD:WARN] File URL not found for file_id=%s", req_file_id)
            return jsonify({'success': False, 'error': '파일 정보를 찾을 수 없습니다.'}), 404

        logger.info("[DOWNLOAD:START] Downloading file: ID=%s, Name=%s, URL=%s", req_file_id, clean_file_name, file_url)

        file_bytes = None
        content_type = 'application/octet-stream'

        # 1. MinIO S3 다운로드 시도
        if s3_client:
            s3_key = None
            bucket_to_use = 'company-uploads'
            if 'company-uploads/' in file_url:
                s3_key = file_url.split('company-uploads/')[-1]
                bucket_to_use = 'company-uploads'
            elif 'audit-lakehouse/' in file_url:
                s3_key = file_url.split('audit-lakehouse/')[-1]
                bucket_to_use = 'audit-lakehouse'
            elif file_url.startswith('http'):
                path_part = file_url.replace(minio_endpoint, '').lstrip('/')
                parts = path_part.split('/', 1)
                if len(parts) == 2:
                    bucket_to_use, s3_key = parts[0], parts[1]
                else:
                    s3_key = path_part
            else:
                s3_key = file_url

            if s3_key:
                try:
                    s3_obj = s3_client.get_object(Bucket=bucket_to_use, Key=s3_key)
                    file_bytes = s3_obj['Body'].read()
                    content_type = s3_obj.get('ContentType', 'application/octet-stream')
                    logger.info("[DOWNLOAD:MINIO_OK] Downloaded %d bytes from MinIO (Bucket=%s, Key=%s)", len(file_bytes), bucket_to_use, s3_key)
                except Exception as s3_err:
                    logger.warning("[DOWNLOAD:MINIO_WARN] MinIO download failed for key %s: %s", s3_key, s3_err)

        # 2. Supabase Storage 다운로드 시도 (MinIO 미존재 또는 실패 시)
        if not file_bytes and supabase:
            try:
                storage_path = file_url
                if 'company-uploads/' in file_url:
                    storage_path = file_url.split('company-uploads/')[-1]
                file_bytes = supabase.storage.from_('company-uploads').download(storage_path)
                logger.info("[DOWNLOAD:SUPABASE_OK] Downloaded %d bytes from Supabase Storage", len(file_bytes))
            except Exception as sb_err:
                logger.warning("[DOWNLOAD:SUPABASE_WARN] Supabase storage download failed: %s", sb_err)

        # 3. Direct HTTP 요청 시도 (URL이 외부 공개 URL인 경우)
        if not file_bytes and file_url.startswith('http'):
            try:
                resp = requests.get(file_url, timeout=10)
                if resp.status_code == 200:
                    file_bytes = resp.content
                    content_type = resp.headers.get('Content-Type', content_type)
                    logger.info("[DOWNLOAD:HTTP_OK] Downloaded %d bytes via HTTP GET", len(file_bytes))
            except Exception as http_err:
                logger.warning("[DOWNLOAD:HTTP_WARN] Direct HTTP fetch failed: %s", http_err)

        if not file_bytes:
            logger.error("[DOWNLOAD:FAIL] All download attempts failed for file_id=%s, url=%s", req_file_id, file_url)
            return jsonify({'success': False, 'error': '파일을 스토리지에서 다운로드하지 못했습니다.'}), 404

        # 파일 확장자 보완 (파일명에 확장자가 없는 경우)
        if '.' not in clean_file_name:
            if 'pdf' in file_url.lower() or 'pdf' in content_type.lower():
                clean_file_name += '.pdf'
            elif 'xlsx' in file_url.lower():
                clean_file_name += '.xlsx'
            elif 'xls' in file_url.lower():
                clean_file_name += '.xls'
            elif 'csv' in file_url.lower():
                clean_file_name += '.csv'
            elif 'zip' in file_url.lower():
                clean_file_name += '.zip'

        guessed_type, _ = mimetypes.guess_type(clean_file_name)
        if guessed_type:
            content_type = guessed_type

        return send_file(
            io.BytesIO(file_bytes),
            mimetype=content_type,
            as_attachment=True,
            download_name=clean_file_name
        )
    except Exception as e:
        logger.error("[DOWNLOAD:UNHANDLED_ERROR] %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'다운로드 처리 중 오류: {str(e)}'}), 500


@api_bp.route('/api/company/normalized-dataset/<path:company_name>', methods=['GET'])
@api_bp.route('/api/company/normalized-dataset', methods=['GET'])
def get_normalized_dataset(company_name=None):
    """
    사내 우분투 MinIO 서버의 {company_name}/{fiscal_year}/Normalized/data.json 을
    0.01초 만에 인메모리 고속으로 반환하는 초고속 엔드포인트
    """
    try:
        from core.storage_manager import storage_manager

        target_company = company_name or request.args.get('company_name', '').strip()
        if not target_company and 'company' in session:
            target_company = session.get('company', '')

        if not target_company:
            return jsonify({'success': False, 'error': '회사명이 제공되지 않았습니다.'}), 400

        target_year = request.args.get('fiscal_year', '').strip() or request.args.get('year', '').strip() or '2025'

        logger.info("[NORMALIZED_DATASET:REQ] Fetching normalized data for %s (FY %s)", target_company, target_year)
        result = storage_manager.load_normalized_lakehouse_data(target_company, int(target_year) if target_year.isdigit() else 2025)

        status_code = 200 if result.get('success') else 404
        return jsonify(result), status_code
    except Exception as e:
        logger.error("[NORMALIZED_DATASET:ERROR] %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'정규화 데이터 조회 오류: {str(e)}'}), 500


@api_bp.route('/api/company/rebuild-normalized', methods=['POST'])
def rebuild_normalized_dataset():
    """
    회계사/관리자가 수동으로 사내 MinIO Normalized/data.json 을 즉시 재빌드/동기화하는 API
    """
    try:
        from core.storage_manager import storage_manager

        data = request.get_json(silent=True) or {}
        target_company = data.get('company_name') or data.get('company') or request.form.get('company_name', '').strip()
        if not target_company and 'company' in session:
            target_company = session.get('company', '')

        if not target_company:
            return jsonify({'success': False, 'error': '회사명이 제공되지 않았습니다.'}), 400

        target_year = data.get('fiscal_year') or data.get('year') or request.form.get('fiscal_year', '').strip() or '2025'
        fy_int = int(target_year) if str(target_year).isdigit() else 2025

        logger.info("[REBUILD_NORMALIZED:REQ] Manual Lakehouse rebuild triggered for %s (FY %s)", target_company, fy_int)
        sync_result = storage_manager.sync_normalized_lakehouse(target_company, fy_int)

        status_code = 200 if sync_result.get('success') else 500
        return jsonify(sync_result), status_code
    except Exception as e:
        logger.error("[REBUILD_NORMALIZED:ERROR] %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'재동기화 처리 오류: {str(e)}'}), 500


@api_bp.route('/api/company/portal-analytics/<path:company_name>', methods=['GET'])
@api_bp.route('/api/company/portal-analytics', methods=['GET'])
def get_portal_analytics(company_name=None):
    """
    회사 포털 5대 핵심 회계분석 보고서(벤포드, 거래처 파레토/에이징, 듀퐁, CCC, 비용 Outlier, AJE)를
    사전 연산 캐시(analytics.json) 우선 조회 및 On-Demand Fallback으로 초고속 반환하는 API
    """
    import gc
    import time
    try:
        from core.storage_manager import storage_manager
        from core.audit_engine import generate_comprehensive_portal_analytics

        start_t = time.time()
        target_company = company_name or request.args.get('company_name', '').strip()
        if not target_company and 'company' in session:
            target_company = session.get('company', '')

        if not target_company:
            logger.warning("[PORTAL_ANALYTICS:WARN] Missing company name in request")
            return jsonify({'success': False, 'error': '회사명이 제공되지 않았습니다.'}), 400

        target_year = request.args.get('fiscal_year', '').strip() or request.args.get('year', '').strip() or '2025'
        fy_int = int(target_year) if str(target_year).isdigit() else 2025
        force_refresh = request.args.get('refresh', '').lower() in ['1', 'true', 'yes']

        # 1. 사전 연산된 analytics.json 캐시 우선 로드 (0.01초 소요, RAM 1MB 미만)
        if not force_refresh:
            cache_res = storage_manager.load_portal_analytics_cache(target_company, fy_int)
            if cache_res.get("success") and cache_res.get("data"):
                cached_data = cache_res["data"]
                elapsed_ms = int((time.time() - start_t) * 1000)
                cached_data['elapsed_ms'] = elapsed_ms
                cached_data['is_cached'] = True
                logger.info("[PORTAL_ANALYTICS:CACHE_HIT] Served cached analytics for %s (FY %s) in %dms",
                            target_company, fy_int, elapsed_ms)
                return jsonify(cached_data), 200

        # 2. 캐시가 없거나 강제 갱신 요청인 경우: 실시간 연산 (Step 1 메모리 최적화 엔진)
        logger.info("[PORTAL_ANALYTICS:REQ] Generating on-demand portal analytics for '%s' (FY %s)", target_company, fy_int)
        analytics_result = generate_comprehensive_portal_analytics(target_company, fy_int)

        elapsed_ms = int((time.time() - start_t) * 1000)
        analytics_result['elapsed_ms'] = elapsed_ms
        analytics_result['is_cached'] = False

        if analytics_result.get('success'):
            logger.info("[PORTAL_ANALYTICS:SUCCESS] Generated analytics for %s in %dms (Health Score: %s)",
                        target_company, elapsed_ms, analytics_result.get('health_score', {}).get('score'))
            
            # 다음 조회를 위해 캐시 자동 저장 (Self-Healing)
            storage_manager.save_portal_analytics_cache(target_company, fy_int, analytics_result)

            return jsonify(analytics_result), 200
        else:
            logger.error("[PORTAL_ANALYTICS:FAIL] Failed to generate analytics: %s", analytics_result.get('error'))
            return jsonify(analytics_result), 404

    except Exception as e:
        logger.error("[PORTAL_ANALYTICS:ERROR] Critical error generating portal analytics: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': f'분석 보고서 생성 오류: {str(e)}'}), 500
    finally:
        gc.collect()





