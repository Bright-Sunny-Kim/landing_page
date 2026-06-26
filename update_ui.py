import re

def update_company_html():
    with open('templates/company.html', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    summary_html = """
                              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">?ÑÏ≤¥ ?†Ï≤≠</div>
                                      <div id="summary-total" style="font-size: 1.5rem; font-weight: bold; color: #fff;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">ÏßÑÌñâÏ§?/div>
                                      <div id="summary-progress" style="font-size: 1.5rem; font-weight: bold; color: #60a5fa;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">ÎØ∏Í≤∞(?ÄÍ∏?</div>
                                      <div id="summary-pending" style="font-size: 1.5rem; font-weight: bold; color: #fbbf24;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">?ÑÎ£å</div>
                                      <div id="summary-completed" style="font-size: 1.5rem; font-weight: bold; color: #4ade80;">0</div>
                                  </div>
                              </div>
"""
    if 'summary-total' not in content:
        content = re.sub(r'(<div id="ext-finance-dashboard">\s*<div style="display: flex;.*?</button>\s*</div>)', r'\1\n' + summary_html, content, flags=re.DOTALL)
        with open('templates/company.html', 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)

def update_main_js():
    with open('static/js/main.js', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    js_to_add = """
        if(document.getElementById("summary-total")) {
            document.getElementById("summary-total").textContent = data.length;
            document.getElementById("summary-progress").textContent = data.filter(d => ["draft", "submitted", "fee_pending", "fee_paid", "form_downloaded", "mail_sent"].includes(d.status)).length;
            document.getElementById("summary-pending").textContent = data.filter(d => ["draft", "submitted", "fee_pending"].includes(d.status)).length;
            document.getElementById("summary-completed").textContent = data.filter(d => d.status === "completed").length;
        }
"""
    if 'summary-total' not in content:
        content = content.replace('function renderInquiryList(data) {', 'function renderInquiryList(data) {\n' + js_to_add)
        with open('static/js/main.js', 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)

def update_master_html():
    with open('templates/master.html', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    admin_buttons = """
                    <button class="btn-submit" onclick="exportAdminInquiry()" style="padding: 8px 16px; width: auto; font-size: 0.9rem; margin-right: 10px;">?ëÏ? ?§Ïö¥Î°úÎìú</button>
                    <button class="btn-logout" onclick="loadAdminInquiryStatus()" style="padding: 8px 16px; width: auto; font-size: 0.9rem;">?àÎ°úÍ≥†Ïπ®</button>
"""
    if 'exportAdminInquiry' not in content:
        content = re.sub(r'<button class="btn-logout" onclick="loadAdminInquiryStatus\(\)"[^>]+>?àÎ°úÍ≥†Ïπ®</button>', admin_buttons, content)
        with open('templates/master.html', 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)

def update_master_js():
    with open('static/js/main.js', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    js_to_add = """
window.promptUpdateDetail = async function(id) {
    const tracking = prompt("?±Í∏∞Î≤àÌò∏Î•??ÖÎ†•?òÏÑ∏??(ÎπàÏπ∏?¥Î©¥ Í∏∞Ï°¥?†Ï?):");
    const notes = prompt("?¥Îãπ??Î©îÎ™®Î•??ÖÎ†•?òÏÑ∏??(ÎπàÏπ∏?¥Î©¥ Í∏∞Ï°¥?†Ï?):");
    
    if(tracking === null && notes === null) return;
    
    let updates = {};
    if(tracking) updates.mail_tracking_no = tracking;
    if(notes) updates.notes = notes;
    
    if(Object.keys(updates).length > 0) {
        try {
            const res = await fetch(`/api/admin/inquiry/detail/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(updates)
            });
            if(res.ok) {
                alert("?ÖÎç∞?¥Ìä∏ ?ÑÎ£å");
                loadAdminInquiryStatus();
            } else {
                alert("?ÖÎç∞?¥Ìä∏ ?§Ìå®");
            }
        } catch(e) { console.error(e); }
    }
};

window.exportAdminInquiry = function() {
    window.location.href = '/api/admin/inquiry/export';
};
"""
    if 'promptUpdateDetail' not in content:
        content = content + "\n" + js_to_add
        content = content.replace(
            '<button class="btn-logout" style="padding:4px 8px; width:auto; font-size:0.8rem;" onclick="viewInquiryHistory(${item.id})">?¥Î†•</button>',
            '<button class="btn-logout" style="padding:4px 8px; width:auto; font-size:0.8rem;" onclick="viewInquiryHistory(${item.id})">?¥Î†•</button>' +
            '<button class="btn-submit" style="padding:4px 8px; width:auto; font-size:0.8rem; margin-left:5px;" onclick="promptUpdateDetail(${item.id})">?òÏ†ï</button>'
        )
        with open('static/js/main.js', 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)

update_company_html()
update_main_js()
update_master_html()
update_master_js()
print("Success!")
