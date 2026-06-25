import codecs
import re

with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    content = f.read()

new_html = '''<div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: none;">
    <header class="dashboard-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px; margin-bottom: 20px;">
        <div class="status-badge" style="background: rgba(99, 102, 241, 0.2); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.4);">
            <span class="pulse-dot" style="background: #a78bfa;"></span>
            <span>대시보드</span>
        </div>
        <h1 id="dashboard-heading">📊 제출내역 조회 및 자료제출</h1>
        <p style="color: var(--text-secondary); margin-top: 10px; font-size: 0.95rem;">제출 진척도를 확인하고 각 항목별로 자료를 제출하세요.</p>
    </header>

    <!-- 진척도 요약 대시보드 -->
    <div class="progress-section" style="background: rgba(255,255,255,0.03); padding: 25px; border-radius: 12px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1);">
        <h3 style="margin-top: 0; margin-bottom: 15px; color: #e2e8f0;">📈 자료 제출 진척도</h3>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span>전체 {{ progress.total }}개 항목 중 <strong>{{ progress.submitted }}</strong>개 완료 (제출 및 해당없음 포함)</span>
            <span style="color: #a78bfa; font-weight: bold; font-size: 1.1rem;">{{ progress.percent }}%</span>
        </div>
        <div style="width: 100%; height: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; overflow: hidden;">
            <div style="width: {{ progress.percent }}%; height: 100%; background: linear-gradient(90deg, #818cf8, #c084fc); transition: width 1s ease-in-out;"></div>
        </div>
    </div>

    <!-- 미제출 내역 한눈에 보기 -->
    <div class="missing-items-section" style="margin-bottom: 30px;">
        <h3 style="margin-bottom: 15px; color: #fca5a5; display: flex; align-items: center; gap: 8px;">
            <span>⚠️</span> 미제출 내역 한눈에 보기
        </h3>
        {% if missing_items %}
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">
            {% for item in missing_items %}
                <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); padding: 15px; border-radius: 8px; display: flex; flex-direction: column; gap: 5px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <span style="font-size: 0.8rem; color: #fca5a5; font-weight: 600; text-transform: uppercase;">[{{ item.category }}]</span>
                    <span style="color: #e2e8f0; font-size: 0.95rem;">{{ item.label }}</span>
                </div>
            {% endfor %}
            </div>
        {% else %}
            <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); padding: 20px; border-radius: 8px; text-align: center; color: #4ade80;">
                🎉 모든 서류 제출(처리)이 완료되었습니다! 훌륭합니다!
            </div>
        {% endif %}
    </div>

    <!-- 제출 폼 및 탭 -->
    <div style="margin-bottom: 30px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 30px;">
        <h3 style="margin-bottom: 15px; color: #e2e8f0; display: flex; align-items: center; gap: 8px;">
            <span>📂</span> 항목별 자료 제출
        </h3>
        <!-- 내부 서브 탭 네비게이션 -->
        <div class="sub-tabs-container" style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
            <button type="button" class="sub-tab-btn active" data-subtab="sub-pfile" onclick="switchSubTab('sub-pfile')" style="padding: 10px 20px; background: rgba(99, 102, 241, 0.2); border: 1px solid #818cf8; border-radius: 8px; color: white; cursor: pointer; font-weight: bold;">🏢 회사기본사항 (P-File)</button>
            <button type="button" class="sub-tab-btn" data-subtab="sub-written" onclick="switchSubTab('sub-written')" style="padding: 10px 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; cursor: pointer;">📝 서면제출자료</button>
            <button type="button" class="sub-tab-btn" data-subtab="sub-finance" onclick="switchSubTab('sub-finance')" style="padding: 10px 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; cursor: pointer;">🏦 외부조회 (금융기관)</button>
            <button type="button" class="sub-tab-btn" data-subtab="sub-partner" onclick="switchSubTab('sub-partner')" style="padding: 10px 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; cursor: pointer;">🤝 외부조회 (거래처)</button>
        </div>

        <form id="history-upload-form" action="/company/{{ company_name }}/upload" method="post" enctype="multipart/form-data">
            <input type="hidden" id="history-category-hidden" name="category" value="P-File">
            <div class="sub-tab-contents">
                
                <!-- 1. P-File -->
                <div id="sub-pfile" class="sub-tab-content" style="display: block;">
                    <div class="form-group-block">
                        <label for="history_pfile_doc" class="field-label">회사기본사항 문서 양식 선택</label>
                        <select id="history_pfile_doc" name="pfile_doc" class="custom-select">
                            <option value="">-- 제출할 항목을 선택하세요 --</option>
                            <option value="pfile_org_chart">[회사기본사항] 항목: 조직도 (부서별 인원 포함)</option>
                            <option value="pfile_biz_plan">[회사기본사항] 항목: 당기 사업계획서</option>
                            <option value="pfile_minutes">[회사기본사항] 항목: 이사회 의사록 (당기~현재)</option>
                            <option value="pfile_auditor_report">[회사기본사항] 항목: 내부감사 보고서</option>
                        </select>
                    </div>
                </div>

                <!-- 2. 서면제출자료 -->
                <div id="sub-written" class="sub-tab-content" style="display: none;">
                    <div class="form-group-block">
                        <label for="history_written_doc" class="field-label">서면제출자료 양식 선택</label>
                        <select id="history_written_doc" name="written_doc" class="custom-select">
                            <option value="">-- 제출할 항목을 선택하세요 --</option>
                            <optgroup label="당기분 (Temp_P)">
                                <option value="current_tb">[당기(결산)] 항목: 기말 합계잔액시산표</option>
                                <option value="current_fs">[당기(결산)] 항목: 기말 재무제표 (BS, IS)</option>
                                <option value="current_sales">[당기(결산)] 항목: 매출처별 원장</option>
                            </optgroup>
                            <optgroup label="전기분 (Temp_L)">
                                <option value="prior_tb">[전기(결산)] 항목: 전기 합계잔액시산표</option>
                                <option value="prior_fs">[전기(결산)] 항목: 전기 재무제표 (BS, IS)</option>
                            </optgroup>
                        </select>
                    </div>
                </div>

                <!-- 3. 외부조회 (금융기관) -->
                <div id="sub-finance" class="sub-tab-content" style="display: none;">
                    <div class="form-group-block">
                        <label for="history_finance_doc" class="field-label">금융기관 외부조회 문서 선택</label>
                        <select id="history_finance_doc" name="finance_doc" class="custom-select">
                            <option value="">-- 제출할 항목을 선택하세요 --</option>
                            <option value="finance_bank_balance">[금융기관] 항목: 은행 잔고 증명서</option>
                            <option value="finance_loan">[금융기관] 항목: 차입금 및 부채 증명서</option>
                            <option value="finance_interest">[금융기관] 항목: 이자 비용 내역서</option>
                            <option value="finance_guarantee">[금융기관] 항목: 지급보증 내역</option>
                        </select>
                    </div>
                </div>

                <!-- 4. 외부조회 (거래처) -->
                <div id="sub-partner" class="sub-tab-content" style="display: none;">
                    <div class="form-group-block">
                        <label for="history_partner_doc" class="field-label">거래처 외부조회 문서 선택</label>
                        <select id="history_partner_doc" name="partner_doc" class="custom-select">
                            <option value="">-- 제출할 항목을 선택하세요 --</option>
                            <option value="partner_receivables">[거래처] 항목: 매출채권 잔액 확인서</option>
                            <option value="partner_payables">[거래처] 항목: 매입채무 잔액 확인서</option>
                            <option value="partner_sales_volume">[거래처] 항목: 연간 주요 거래처 매출원장</option>
                            <option value="partner_confirm">[거래처] 항목: 채권채무조회서 수발신 내역</option>
                        </select>
                    </div>
                </div>
            </div> <!-- end sub-tab-contents -->

            <div class="form-group-block" style="margin-top: 24px;">
                <label for="history_file_upload" class="field-label">파일 업로드 (엑셀, PDF 등)</label>
                <div class="file-drop-area" id="history-file-drop-area" style="background: rgba(0,0,0,0.2); border: 2px dashed rgba(255,255,255,0.2); padding: 40px; text-align: center; border-radius: 12px; cursor: pointer; transition: all 0.3s ease;">
                    <span class="file-icon" style="font-size: 40px; margin-bottom: 15px; display: block;">📂</span>
                    <span class="file-msg" style="color: var(--text-secondary); display: block; margin-bottom: 10px;">클릭하거나 파일을 여기로 드래그하세요</span>
                    <input class="file-input" type="file" id="history_file_upload" name="file" required style="display: none;">
                    <button type="button" class="btn-file-select" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">파일 선택</button>
                </div>
            </div>
            
            <div class="form-group-block" style="margin-top: 24px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 24px;">
                <label for="history_help_text" class="field-label">추가 요청/전달 사항 (선택)</label>
                <textarea id="history_help_text" name="help_text" rows="2" placeholder="회계사님께 전달할 메시지가 있다면 적어주세요." style="width: 100%; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white;"></textarea>
            </div>

            <button type="submit" class="btn-submit" style="margin-top: 20px;">
                <span>자료 제출하기</span>
                <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
        </form>
    </div>

    <!-- 타임라인 -->
    <div class="history-table-section">
        <h3 style="margin-bottom: 15px; color: #e2e8f0; display: flex; align-items: center; gap: 8px;">
            <span>🕒</span> 전체 제출 이력 타임라인
        </h3>
        <div class="audit-table-wrapper">
            <table class="audit-upload-table">
                <thead>
                    <tr>
                        <th style="width: 15%;">제출일시</th>
                        <th style="width: 45%;">제출 파일 / 항목명</th>
                        <th style="width: 25%;">처리 상태</th>
                        <th style="width: 15%;">법인 검토결과</th>
                    </tr>
                </thead>
                <tbody>
                {% if history_files %}
                    {% for f in history_files %}
                    <tr class="doc-row doc-common">
                        <td style="color: var(--text-secondary); font-size: 0.9rem;">
                            {{ f.created_at.split('T')[0] if f.created_at else '' }}<br>
                            {{ f.created_at.split('T')[1][:5] if f.created_at and 'T' in f.created_at else '' }}
                        </td>
                        <td class="doc-info">
                            {% if f.file_url %}
                                <a href="{{ f.public_url }}" target="_blank" style="color: #a78bfa; text-decoration: underline; display: flex; align-items: center; gap: 5px;">
                                    <span class="doc-icon">📄</span>
                                    <span class="doc-name">{{ f.file_name }}</span>
                                </a>
                            {% else %}
                                <div class="doc-text-wrapper" style="display: flex; align-items: center; gap: 5px;">
                                    <span class="doc-icon" style="filter: grayscale(1);">ℹ️</span>
                                    <span class="doc-name" style="color: var(--text-secondary);">{{ f.file_name }}</span>
                                </div>
                            {% endif %}
                        </td>
                        <td>
                            <span style="font-size: 0.85rem; padding: 6px 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; display: inline-block; white-space: pre-line; line-height: 1.4; color: var(--text-secondary);">{{ f.help_text }}</span>
                        </td>
                        <td>
                            <span class="status-badge" style="background: rgba(99, 102, 241, 0.1); color: #818cf8; border-color: rgba(99, 102, 241, 0.2); padding: 4px 8px;">
                                {{ f.status }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td colspan="4" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                            아직 데이터베이스에 등록된 제출 내역이 없습니다.
                        </td>
                    </tr>
                {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>
'''

script_block = """
<script>
    function switchSubTab(tabId) {
        // 모든 내용 숨기기
        const contents = document.querySelectorAll('.sub-tab-content');
        contents.forEach(c => c.style.display = 'none');
        
        // 클릭한 탭의 내용 보이기
        const target = document.getElementById(tabId);
        if(target) target.style.display = 'block';
        
        // 모든 버튼에서 active 제거
        const btns = document.querySelectorAll('.sub-tab-btn');
        btns.forEach(b => {
            b.classList.remove('active');
            b.style.background = 'rgba(255,255,255,0.05)';
            b.style.borderColor = 'rgba(255,255,255,0.1)';
            b.style.fontWeight = 'normal';
        });
        
        // 클릭한 버튼 활성화
        const activeBtn = document.querySelector(`.sub-tab-btn[data-subtab="${tabId}"]`);
        if(activeBtn) {
            activeBtn.classList.add('active');
            activeBtn.style.background = 'rgba(99, 102, 241, 0.2)';
            activeBtn.style.borderColor = '#818cf8';
            activeBtn.style.fontWeight = 'bold';
        }
        
        // 숨겨진 카테고리 필드 업데이트
        let catValue = 'P-File';
        if(tabId === 'sub-written') catValue = 'Temp';
        else if(tabId === 'sub-finance') catValue = 'Ext_F';
        else if(tabId === 'sub-partner') catValue = 'Ext_C';
        document.getElementById('history-category-hidden').value = catValue;
    }

    // 파일 선택 이벤트 연동
    document.addEventListener('DOMContentLoaded', () => {
        const fileArea = document.getElementById('history-file-drop-area');
        const fileInput = document.getElementById('history_file_upload');
        const fileBtn = fileArea ? fileArea.querySelector('.btn-file-select') : null;
        
        if (fileArea && fileInput && fileBtn) {
            fileBtn.addEventListener('click', () => fileInput.click());
            fileArea.addEventListener('click', (e) => {
                if (e.target !== fileBtn && e.target !== fileInput) {
                    fileInput.click();
                }
            });
            fileInput.addEventListener('change', () => {
                const msg = fileArea.querySelector('.file-msg');
                if (fileInput.files.length > 0) {
                    msg.textContent = fileInput.files[0].name;
                    msg.style.color = '#818cf8';
                } else {
                    msg.textContent = '클릭하거나 파일을 여기로 드래그하세요';
                    msg.style.color = 'var(--text-secondary)';
                }
            });
        }
    });
</script>
"""

# Now we replace the old partner-history-view with the new one
pattern = r'<div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: none;">.*?<div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'
# CAREFUL: Make sure we preserve the starting of partner-inquiry-view
replacement = new_html + '\n\n' + script_block + '\n\n' + '    <div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with codecs.open('templates/company.html', 'w', 'utf-8') as f:
    f.write(content)
print("Updated company.html successfully.")
