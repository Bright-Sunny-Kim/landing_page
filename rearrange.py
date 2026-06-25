import re

with open('templates/company.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove sidebar menu for partner-pfile
content = re.sub(r'<li class=\"master-menu-item\" data-menu=\"partner-pfile\">.*?</li>', '', content, flags=re.DOTALL)

# 2. Extract the P-File form content
pfile_view_match = re.search(r'<div class=\"glass-card dashboard-card master-card\" id=\"partner-pfile-view\".*?<div class=\"audit-checklist-section\">(.*?)</div>\s*</div>\s*<button type=\"submit\" class=\"btn-submit\"', content, re.DOTALL)
if pfile_view_match:
    pfile_inner_html = pfile_view_match.group(1)
    # Remove the whole partner-pfile-view div including the form and submit button
    content = re.sub(r'<!-- P-File 뷰 -->.*?</div>\s*<!-- 기타 뷰 플레이스홀더 -->', '<!-- 기타 뷰 플레이스홀더 -->', content, flags=re.DOTALL)

    # 3. Add to sub-tabs navigation
    sub_tab_nav = '''
                <!-- 내부 서브 탭 네비게이션 -->
                <div class="sub-tabs-container" style="display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px;">
                    <button type="button" class="sub-tab-btn active" data-subtab="sub-pfile" onclick="switchSubTab('sub-pfile')">🏢 회사기본사항 (P-File)</button>
                    <button type="button" class="sub-tab-btn" data-subtab="sub-written" onclick="switchSubTab('sub-written')">📂 서면제출자료</button>
                    <button type="button" class="sub-tab-btn" data-subtab="sub-ext-finance" onclick="switchSubTab('sub-ext-finance')">🏦 외부조회 (금융기관)</button>
                    <button type="button" class="sub-tab-btn" data-subtab="sub-ext-partner" onclick="switchSubTab('sub-ext-partner')">🏢 외부조회 (거래처)</button>
                </div>
'''
    # Replace old sub-tab nav
    content = re.sub(r'<!-- 내부 서브 탭 네비게이션 -->.*?</div>', sub_tab_nav, content, count=1, flags=re.DOTALL)

    # 4. Change 'active' state of sub-written pane
    content = content.replace('<div id="sub-written" class="sub-tab-pane" style="display: block;">', '<div id="sub-written" class="sub-tab-pane" style="display: none;">')
    
    # 5. Insert sub-pfile pane inside sub-tab-contents
    pfile_pane = f'''
                    <!-- 0. 회사기본사항 (P-File) 탭 -->
                    <div id="sub-pfile" class="sub-tab-pane" style="display: block;">
                        <div class="audit-checklist-section">
                            <p class="checklist-desc">외부회계감사 영구조서(P-File) 구성을 위한 회사 기본 자료를 업로드해 주세요.</p>
                            {pfile_inner_html}
                        </div>
                    </div>
'''
    # Find the sub-tab-contents div and insert pfile_pane
    content = content.replace('<!-- 서브 탭 콘텐츠 영역 -->\n                <div class="sub-tab-contents">', f'<!-- 서브 탭 콘텐츠 영역 -->\n                <div class="sub-tab-contents">\n{pfile_pane}')

    # 6. Check if we need to remove form_type=pfile if it exists in the pfile_inner_html (it was outside in the wrapper, but let's be sure)
    # The wrapper had <input type="hidden" name="form_type" value="pfile"> which we removed in step 2.

    with open('templates/company.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('company.html successfully restructured.')
else:
    print('Could not find pfile view match.')
