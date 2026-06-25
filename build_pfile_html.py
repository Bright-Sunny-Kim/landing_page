import re

pfile_items = [
    ('1. 법적 증빙 및 지배구조 (Corporate Governance)', [
        ('pfile_01', '[PBC-P-01] 최신 정관 (신·구 조문 대비표 포함)'),
        ('pfile_02', '[PBC-P-02] 법인 등기부등본 (말소사항 포함 전량)'),
        ('pfile_03', '[PBC-P-03] 주주명부 및 특수관계자 지분 구조도'),
        ('pfile_04', '[PBC-P-04] 과거 3개년 주주총회 및 이사회 의사록 일체')
    ]),
    ('2. 내부통제 및 회계 시스템 (Internal Control & Accounting System)', [
        ('pfile_05', '[PBC-P-05] 전사 조직도 및 직무 권한·업무분장표'),
        ('pfile_06', '[PBC-P-06] 내부회계관리제도 설계 및 운영 기술서 (Flowchart 및 RCM 포함)'),
        ('pfile_07', '[PBC-P-07] 주요 사규 및 위임전결 규정집 (자금관리규정, 급여 등)'),
        ('pfile_08', '[PBC-P-08] ERP 및 회계 프로그램 시스템 사양서 (계정과목 연동표 포함)')
    ]),
    ('3. 장기 계약 및 재무적 의무 (Long-term Contracts & Commitments)', [
        ('pfile_09', '[PBC-P-09] 장기 차입금 및 사채 발행 계약서 총괄표 (약정 조건 포함)'),
        ('pfile_10', '[PBC-P-10] 주요 자산 리스(금융/운용) 계약서 및 리스료 스케줄표'),
        ('pfile_11', '[PBC-P-11] 부동산 등기부등본 및 토지·건물 매매/임대차 계약서'),
        ('pfile_12', '[PBC-P-12] 국책과제 협약서 및 기술 이전/라이선스 장기 계약서'),
        ('pfile_13', '[PBC-P-13] 주주간 계약서 및 금융기관 담보·보증 제공 내역서')
    ]),
    ('4. 세무 및 역사적 재무 데이터 (Tax & Historical Financial Data)', [
        ('pfile_14', '[PBC-P-14] 최근 3개년 법인세 신고서 및 세무조정계산서 일체'),
        ('pfile_15', '[PBC-P-15] 이월결손금 및 세액공제(감면) 이력 관리대장'),
        ('pfile_16', '[PBC-P-16] 과거 세무조사 결과통지서 및 조치 결과 보고서'),
        ('pfile_17', '[PBC-P-17] 최근 3개년 외부감사보고서 및 미수정왜곡표시 요약표(정정 내역)')
    ])
]

html = """
            <!-- P-File 뷰 -->
            <div class="glass-card dashboard-card master-card" id="partner-pfile-view" style="display: none;">
                <header class="dashboard-header">
                    <div class="status-badge" style="background: rgba(99, 102, 241, 0.2); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.4);">
                        <span class="pulse-dot" style="background: #a78bfa;"></span>
                        <span>P-File (영구조서)</span>
                    </div>
                    <h1 id="dashboard-heading">🏢 회사기본사항 제출</h1>
                    <p style="color: var(--text-secondary); margin-top: 10px; font-size: 0.95rem;">외부회계감사 영구조서(P-File) 구성을 위한 회사 기본 자료를 업로드해 주세요.</p>
                </header>

                <form action="{{ url_for('submit_request') }}" method="POST" enctype="multipart/form-data" class="request-form">
                    <input type="hidden" name="form_type" value="pfile">
                    <div class="audit-checklist-section">
                        <div class="audit-table-wrapper">
"""

for category, items in pfile_items:
    html += f"""
                            <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 1.1rem; color: #e2e8f0; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">{category}</h3>
                            <table class="audit-upload-table" style="margin-bottom: 20px;">
                                <thead>
                                    <tr>
                                        <th style="width: 60%;">제출 서류 항목</th>
                                        <th style="width: 40%;">파일 첨부</th>
                                    </tr>
                                </thead>
                                <tbody>
"""
    for code, name in items:
        html += f"""
                                    <tr class="doc-row doc-common">
                                        <td class="doc-info">
                                            <span class="doc-icon">📄</span>
                                            <div class="doc-text-wrapper">
                                                <span class="doc-name">{name}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div class="status-options" style="margin-bottom: 8px; font-size: 0.85rem; display: flex; gap: 8px; justify-content: center;">
                                                <label><input type="radio" name="{code}_status" value="제출" checked onchange="toggleUploadBox('{code}', this.value)"> 제출</label>
                                                <label><input type="radio" name="{code}_status" value="미제출" onchange="toggleUploadBox('{code}', this.value)"> 미제출</label>
                                                <label><input type="radio" name="{code}_status" value="해당사항없음" onchange="toggleUploadBox('{code}', this.value)"> 해당없음</label>
                                            </div>
                                            <div class="mini-upload-box" id="box_{code}">
                                                <input type="file" id="{code}" name="{code}" class="mini-file-input" multiple>
                                                <label for="{code}" class="mini-upload-label" id="label-{code}">
                                                    <span class="upload-icon">↑</span>
                                                    <span class="file-text">파일 선택</span>
                                                </label>
                                            </div>
                                        </td>
                                    </tr>
"""
    html += """
                                </tbody>
                            </table>
"""

html += """
                        </div>
                    </div>
                    
                    <button type="submit" class="btn-submit" style="margin-top: 20px;">
                        <span>P-File 일괄 제출하기</span>
                        <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </form>
            </div>
"""

with open('templates/company.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert sidebar tab
sidebar_html = """
                <li class="master-menu-item" data-menu="partner-pfile">
                    <a href="#partner-pfile">
                        <svg class="master-menu-icon" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                        <span>회사기본사항 (P-File)</span>
                    </a>
                </li>
"""
content = content.replace(
    '<li class="master-menu-item" data-menu="partner-history">',
    sidebar_html + '                <li class="master-menu-item" data-menu="partner-history">'
)

# Insert the view placeholder
content = content.replace(
    '<!-- 기타 뷰 플레이스홀더 -->',
    html + '\n            <!-- 기타 뷰 플레이스홀더 -->'
)

with open('templates/company.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('company.html updated successfully!')
