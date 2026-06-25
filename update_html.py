import re

with open('templates/company.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_html = """
            <div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: none;">
                <header class="dashboard-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px; margin-bottom: 20px;">
                    <div class="status-badge" style="background: rgba(99, 102, 241, 0.2); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.4);">
                        <span class="pulse-dot" style="background: #a78bfa;"></span>
                        <span>대시보드</span>
                    </div>
                    <h1 id="dashboard-heading">📊 제출내역 조회 및 진척도</h1>
                    <p style="color: var(--text-secondary); margin-top: 10px; font-size: 0.95rem;">지금까지 제출하신 자료의 진척도와 미제출 내역을 한눈에 파악하세요.</p>
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

                <!-- 전체 제출 이력 타임라인 -->
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
"""

pattern = r'<div class="glass-card dashboard-card master-card" id="partner-history-view".*?</div>\s*</div>\s*</div>'
# Try to match the whole partner-history-view div. The original one is nested with 2 divs.
# Let's use a simpler regex that matches up to the next view
pattern2 = r'<div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: none;">.*?<div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'

content = re.sub(pattern2, new_html + '\n            <div class="glass-card dashboard-card master-card" id="partner-inquiry-view"', content, flags=re.DOTALL)

with open('templates/company.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('company.html updated successfully!')
