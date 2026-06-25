import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_route = """@app.route('/company/<company_name>')
def company_page(company_name):
    if 'email' not in session:
        return redirect(url_for('login_page'))
        
    # 마스터 계정 처리
    if session['email'] == MASTER_EMAIL:
        pass # Allow access
    elif session['company'] != company_name:
        return redirect(url_for('login_page'))
        
    success = request.args.get('success', 'false') == 'true'
    
    document_labels = {
        'tb_current': '시산표(당연도)',
        'tb_prior': '시산표(전년도)',
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
        'pfile_01': '[PBC-P-01] 최신 정관',
        'pfile_02': '[PBC-P-02] 법인 등기부등본',
        'pfile_03': '[PBC-P-03] 주주명부 및 특수관계자 지분 구조도',
        'pfile_04': '[PBC-P-04] 과거 3개년 주주총회 및 이사회 의사록 일체',
        'pfile_05': '[PBC-P-05] 전사 조직도 및 직무 권한·업무분장표',
        'pfile_06': '[PBC-P-06] 내부회계관리제도 설계 및 운영 기술서',
        'pfile_07': '[PBC-P-07] 주요 사규 및 위임전결 규정집',
        'pfile_08': '[PBC-P-08] ERP 및 회계 프로그램 시스템 사양서',
        'pfile_09': '[PBC-P-09] 장기 차입금 및 사채 발행 계약서 총괄표',
        'pfile_10': '[PBC-P-10] 주요 자산 리스 계약서 및 스케줄표',
        'pfile_11': '[PBC-P-11] 부동산 등기부등본 및 관련 계약서',
        'pfile_12': '[PBC-P-12] 국책과제 협약서 및 기술 이전 계약서',
        'pfile_13': '[PBC-P-13] 주주간 계약서 및 금융기관 담보·보증 제공 내역서',
        'pfile_14': '[PBC-P-14] 최근 3개년 법인세 신고서 및 세무조정계산서 일체',
        'pfile_15': '[PBC-P-15] 이월결손금 및 세액공제 이력 관리대장',
        'pfile_16': '[PBC-P-16] 과거 세무조사 결과통지서 및 조치 결과 보고서',
        'pfile_17': '[PBC-P-17] 최근 3개년 외부감사보고서'
    }
    
    history_files = []
    missing_items = []
    progress = {'total': len(document_labels), 'submitted': 0, 'percent': 0}
    
    if supabase:
        try:
            res = supabase.table('company_files').select('*').eq('company_name', company_name).order('created_at', desc=False).execute()
            history_files = res.data
            
            # Extract latest status for each label (iterating ascending so latest overrides)
            label_status = {}
            for f in history_files:
                help_text = f.get('help_text', '')
                if not help_text: continue
                import re as regex
                m = regex.search(r'\[(.*?)\] 상태: (.*)', help_text)
                if m:
                    label = m.group(1).strip()
                    status = m.group(2).split('\\n')[0].strip()
                    label_status[label] = status
            
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
                
            # Re-order history files to descending for display
            history_files.reverse()
            for f in history_files:
                file_url_path = f.get('file_url')
                if file_url_path:
                    if file_url_path.startswith('http'):
                        f['public_url'] = file_url_path
                    else:
                        f['public_url'] = supabase.storage.from_('company-uploads').get_public_url(file_url_path)
                else:
                    f['public_url'] = '#'
                if not f.get('status'):
                    f['status'] = '대기중'
                    
        except Exception as e:
            print(f"History error: {e}")
    
    return render_template('company.html', 
                           company_name=company_name,
                           success=success,
                           history_files=history_files,
                           missing_items=missing_items,
                           progress=progress)

@app.route('/master')"""

pattern = r"@app.route\('/company/<company_name>'\).*?@app.route\('/master'\)"
content = re.sub(pattern, new_route, content, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('app.py updated successfully!')
