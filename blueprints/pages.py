# -*- coding: utf-8 -*-
import re
from flask import Blueprint, render_template, session, redirect, url_for, request
from core.extensions import supabase, MASTER_EMAIL, logger

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    if 'email' in session:
        if session['email'] == MASTER_EMAIL:
            return redirect(url_for('master.master_page'))
        return redirect(url_for('pages.company_page', company_name=session['company']))
    
    return render_template('intro.html')

@pages_bp.route('/intro')
def intro():
    return render_template('intro.html')

@pages_bp.route('/profile')
def profile():
    return render_template('profile.html')

@pages_bp.route('/company/<company_name>')
def company_page(company_name):
    if 'email' not in session:
        return redirect(url_for('auth.login_page'))
        
    # 마스터 계정 처리
    if session['email'] == MASTER_EMAIL:
        pass # Allow access
    elif session['company'] != company_name:
        return redirect(url_for('auth.login_page'))
        
    success = request.args.get('success', 'false') == 'true'
    
    document_labels = {
        'tb_current': '합계잔액시산표(당연도)',
        'tb_prior': '합계잔액시산표(전년도)',
        'bs_current': '재무상태표(당연도)',
        'bs_prior': '재무상태표(전년도)',
        'is_current': '손익계산서(당연도)',
        'is_prior': '손익계산서(전년도)',
        'je_current': '분개장(당연도)',
        'je_prior': '분개장(전년도)',
        'gl_current': '계정별원장(당연도)',
        'gl_prior': '계정별원장(전년도)',
        'fa_current': '유형자산명세서(당연도)',
        'fa_prior': '유형자산명세서(전년도)',
        'vat_current': '부가가치세신고서(당연도)',
        'vat_prior': '부가가치세신고서(전년도)',
        'payroll_current': '급여대장(당연도)',
        'payroll_prior': '급여대장(전년도)',
        'withholding_current': '원천징수이행상황신고서(당연도)',
        'withholding_prior': '원천징수이행상황신고서(전년도)',
        'severance_current': '퇴직금추계액명세서(당연도)',
        'severance_prior': '퇴직금추계액명세서(전년도)',
        'inv_current': '재고자산수불부(당연도)',
        'inv_prior': '재고자산수불부(전년도)',
        'pinv_current': '재물조사 결과표(당연도)',
        'pinv_prior': '재물조사 결과표(전년도)',
        'fina_current': '금융자산명세서(당연도)',
        'fina_prior': '금융자산명세서(전년도)',
        'borr_current': '차입금명세서(당연도)',
        'borr_prior': '차입금명세서(전년도)',
        'risk_current': '위험관리보고서(당연도)',
        'risk_prior': '위험관리보고서(전년도)',
        'inta_current': '무형자산명세서(당연도)',
        'inta_prior': '무형자산명세서(전년도)',
        'proj_current': '프로젝트 진행률 명세(당연도)',
        'proj_prior': '프로젝트 진행률 명세(전년도)',
        'conc_current': '공사원가명세서(당연도)',
        'conc_prior': '공사원가명세서(전년도)',
        'cont_current': '도급계약서 및 진행률 산정표(당연도)',
        'cont_prior': '도급계약서 및 진행률 산정표(전년도)',
        'other_current': '기타 증빙(당연도)',
        'other_prior': '기타 증빙(전년도)',
        'finance_inquiry': '외부조회(금융기관)',
        'partner_inquiry': '외부조회(거래처)',
        'pfile_01': '최신 정관 (신·구 대비표)',
        'pfile_02': '법인 등기부등본 (말소포함)',
        'pfile_03': '주주명부 및 특수관계자 지분 구조도',
        'pfile_04': '과거 3개년 주주총회 및 이사회 의사록 일체',
        'pfile_05': '전사 조직도 및 직무 권한·업무분장표',
        'pfile_06': '내부회계관리제도 설계 및 운영 기술서',
        'pfile_07': '주요 사규 및 위임전결 규정집',
        'pfile_08': 'ERP 및 회계 프로그램 시스템 사양서',
        'pfile_09': '장기 차입금 및 사채 발행 계약서 총괄표',
        'pfile_10': '주요 자산 리스 계약서 및 스케줄표',
        'pfile_11': '부동산 등기부등본 및 관련 계약서',
        'pfile_12': '국책과제 협약서 및 기술 이전 계약서',
        'pfile_13': '주주간 계약서 및 금융기관 담보·보증 제공 내역서',
        'pfile_14': '최근 3개년 법인세 신고서 및 세무조정계산서 일체',
        'pfile_15': '이월결손금 및 세액공제 이력 관리대장',
        'pfile_16': '과거 세무조사 결과통지서 및 조치 결과 보고서',
        'pfile_17': '최근 3개년 외부감사보고서'
    }
    
    fiscal_year = request.args.get('fiscal_year') or request.args.get('year') or '2025'
    
    history_files = []
    missing_items = []
    progress = {'total': len(document_labels), 'submitted': 0, 'percent': 0}
    
    if supabase:
        try:
            res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=True).execute()
            raw_files = res.data or []
            
            # 우분투 서버(MinIO/스토리지) 실존 파일 및 해당 감사연도 파일만 선별
            from blueprints.api import check_storage_file_exists
            valid_files = []
            for f in raw_files:
                file_url_path = f.get('file_url')
                if not file_url_path:
                    continue
                try:
                    if not check_storage_file_exists(file_url_path):
                        continue
                except Exception:
                    pass

                fn = f.get('file_name', '')
                ht = f.get('help_text', '')

                # P-File (영구문서) 여부 확인
                is_pfile = ('P-File' in file_url_path) or ('pfile_' in file_url_path) or any(lbl in fn or lbl in ht for k, lbl in document_labels.items() if k.startswith('pfile_'))

                # 해당 연도 파일 여부 확인
                year_tag = f"[{fiscal_year}년도]"
                year_path = f"/{fiscal_year}/"
                is_this_year = (year_path in file_url_path) or (year_tag in ht)
                
                # 과거 연도 태그가 없던 레코드는 2025년도 기본 귀속
                if not is_this_year and not is_pfile:
                    has_other_year = any(f"/{y}/" in file_url_path or f"[{y}년도]" in ht for y in ['2023', '2024', '2026', '2027', '2028', '2029', '2030'])
                    if not has_other_year and fiscal_year == '2025':
                        is_this_year = True

                if is_pfile or is_this_year:
                    valid_files.append(f)

            history_files = valid_files
            
            label_status = {}
            for f in history_files:
                fn = f.get('file_name', '')
                ht = f.get('help_text', '')
                if ht:
                    m = re.search(r'\[(.*?)\] 상태: (.*)', ht)
                    if m:
                        label = m.group(1).strip()
                        status = m.group(2).split('\n')[0].strip()
                        label_status[label] = status
                if fn and '[' in fn and ']' in fn:
                    lbl = fn.split('[')[1].split(']')[0].strip()
                    if lbl and lbl not in label_status:
                        label_status[lbl] = '제출'
                for doc_key, doc_lbl in document_labels.items():
                    if doc_lbl in fn or (ht and doc_lbl in ht):
                        label_status[doc_lbl] = '제출'
            
            for key, label in document_labels.items():
                status = label_status.get(label, '미제출')
                if status in ['제출', '해당사항없음']:
                    progress['submitted'] += 1
                else:
                    cat = '기타'
                    if key.startswith('pfile_'): cat = 'P-File'
                    elif 'finance' in key or 'partner' in key: cat = '외부조회'
                    elif 'current' in key: cat = '서면(당기)'
                    elif 'prior' in key: cat = '서면(전기)'
                    missing_items.append({'category': cat, 'label': label})
                    
            if progress['total'] > 0:
                progress['percent'] = int((progress['submitted'] / progress['total']) * 100)
                
            for f in history_files:
                if f.get('file_name'):
                    f['file_name'] = re.sub(r'\[PBC-P-\d+\]\s*', '', f['file_name'])
                file_url_path = f.get('file_url')
                if file_url_path:
                    if file_url_path.startswith('http'):
                        f['public_url'] = file_url_path
                    else:
                        f['public_url'] = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                else:
                    f['public_url'] = '#'
                if not f.get('status'):
                    f['status'] = '접수완료'
                    
        except Exception as e:
            logger.exception("Company page history error: %s", e)
    
    return render_template('company.html', 
                           company_name=company_name,
                           fiscal_year=fiscal_year,
                           success=success,
                           history_files=history_files,
                           missing_items=missing_items,
                           progress=progress)
