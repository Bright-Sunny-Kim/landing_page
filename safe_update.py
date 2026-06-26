import re
import os

def read_file(path):
    for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except Exception:
            pass
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def run():
    c1 = read_file("templates/company.html")
    # 🔹 금융기관 외부조회 신청 현황
    summary_html = """
                              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">전체 신청</div>
                                      <div id="summary-total" style="font-size: 1.5rem; font-weight: bold; color: #fff;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">진행중</div>
                                      <div id="summary-progress" style="font-size: 1.5rem; font-weight: bold; color: #60a5fa;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">미결(대기)</div>
                                      <div id="summary-pending" style="font-size: 1.5rem; font-weight: bold; color: #fbbf24;">0</div>
                                  </div>
                                  <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                                      <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">완료</div>
                                      <div id="summary-completed" style="font-size: 1.5rem; font-weight: bold; color: #4ade80;">0</div>
                                  </div>
                              </div>
"""
    if "summary-total" not in c1:
        c1 = re.sub(r'(<div id="ext-finance-dashboard">\s*<div style="display: flex;.*?</button>\s*</div>)', r'\g<1>\n' + summary_html, c1, flags=re.DOTALL)
        write_file("templates/company.html", c1)

    c2 = read_file("static/js/main.js")
    js_to_add = """
        if(document.getElementById("summary-total")) {
            document.getElementById("summary-total").textContent = data.length;
            document.getElementById("summary-progress").textContent = data.filter(d => ["draft", "submitted", "fee_pending", "fee_paid", "form_downloaded", "mail_sent"].includes(d.status)).length;
            document.getElementById("summary-pending").textContent = data.filter(d => ["draft", "submitted", "fee_pending"].includes(d.status)).length;
            document.getElementById("summary-completed").textContent = data.filter(d => d.status === "completed").length;
        }
"""
    if "summary-total" not in c2:
        c2 = c2.replace('function renderInquiryList(data) {', 'function renderInquiryList(data) {\n' + js_to_add)
        write_file("static/js/main.js", c2)

    c3 = read_file("templates/master.html")
    admin_btns = """                    <button class="btn-submit" onclick="exportAdminInquiry()" style="padding: 8px 16px; width: auto; font-size: 0.9rem; margin-right: 10px;">엑셀 다운로드</button>
                    <button class="btn-logout" onclick="loadAdminInquiryStatus()" style="padding: 8px 16px; width: auto; font-size: 0.9rem;">새로고침</button>"""
    if "exportAdminInquiry" not in c3:
        c3 = re.sub(r'<button class="btn-logout" onclick="loadAdminInquiryStatus\(\)"[^>]*>새로고침</button>', admin_btns, c3)
        write_file("templates/master.html", c3)

    c4 = read_file("static/js/main.js")
    js_to_add2 = """
window.promptUpdateDetail = async function(id) {
    const tracking = prompt("등기번호를 입력하세요 (빈칸이면 기존유지):");
    const notes = prompt("담당자 메모를 입력하세요 (빈칸이면 기존유지):");
    
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
                alert("업데이트 완료");
                loadAdminInquiryStatus();
            } else {
                alert("업데이트 실패");
            }
        } catch(e) { console.error(e); }
    }
};

window.exportAdminInquiry = function() {
    window.location.href = '/api/admin/inquiry/export';
};
"""
    if "promptUpdateDetail" not in c4:
        c4 = c4 + "\n" + js_to_add2
        c4 = c4.replace('<button class="btn-logout" style="padding:4px 8px; width:auto; font-size:0.8rem;" onclick="viewInquiryHistory(${item.id})">이력</button>',
                        '<button class="btn-logout" style="padding:4px 8px; width:auto; font-size:0.8rem;" onclick="viewInquiryHistory(${item.id})">이력</button><button class="btn-submit" style="padding:4px 8px; width:auto; font-size:0.8rem; margin-left:5px;" onclick="promptUpdateDetail(${item.id})">수정</button>')
        write_file("static/js/main.js", c4)

    print("Success")

if __name__ == '__main__':
    run()
