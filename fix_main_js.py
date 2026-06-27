import os

def fix_main_js():
    path = r"C:\Users\CLAUD\landing_page\static\js\main.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split before the corrupted block
    split_marker = "// ==========================================\n//  외부조회 (Financial Inquiry)"
    if split_marker not in content:
        split_marker = "// ==========================================\n//  ܺȸ (Financial Inquiry)"
        
    parts = content.split(split_marker)
    original_js = parts[0]

    correct_js = """// ==========================================
//  외부조회 (Financial Inquiry)
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // 요소 확인
    const financeDashboard = document.getElementById('ext-finance-dashboard');
    const financeWizard = document.getElementById('ext-finance-wizard');
    if (!financeDashboard || !financeWizard) return; // 해당 페이지가 아님

    let allBanks = [];

    // 은행 목록 불러오기
    async function loadFinancialInstitutions() {
        try {
            const res = await fetch('/api/financial_institutions');
            if(res.ok) {
                allBanks = await res.json();
            }
        } catch(e) {
            console.error('Failed to load banks:', e);
        }
    }

    // 신청 현황 불러오기
    window.loadInquiryStatus = async function() {
        try {
            const res = await fetch('/api/inquiry/status');
            if(res.ok) {
                const data = await res.json();
                renderInquiryList(data);
            }
        } catch(e) {
            console.error('Failed to load inquiry status:', e);
        }
    };

    function renderInquiryList(data) {
        if(document.getElementById("summary-total")) {
            document.getElementById("summary-total").textContent = data.length;
            document.getElementById("summary-progress").textContent = data.filter(d => ["draft", "submitted", "fee_pending", "fee_paid", "form_downloaded", "mail_sent"].includes(d.status)).length;
            document.getElementById("summary-pending").textContent = data.filter(d => ["draft", "submitted", "fee_pending"].includes(d.status)).length;
            document.getElementById("summary-completed").textContent = data.filter(d => d.status === "completed").length;
        }

        const tbody = document.getElementById('finance-inquiry-list');
        tbody.innerHTML = '';
        if(data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 20px;">신청 내역이 없습니다.</td></tr>';
            return;
        }

        const statusMap = {
            'draft': '작성중',
            'submitted': '신청완료',
            'fee_pending': '입금대기',
            'fee_paid': '입금확인',
            'form_downloaded': '서식다운로드완료',
            'mail_sent': '발송완료',
            'received': '회신완료',
            'completed': '완료',
            'cancelled': '취소'
        };

        data.forEach(item => {
            const dateStr = item.created_at ? item.created_at.split('T')[0] : '';
            const bankName = item.financial_institutions ? item.financial_institutions.institution_name : '알수없음';
            const statusStr = statusMap[item.status] || item.status;
            const isPaper = (item.inquiry_type === 'paper');

            let actionBtn = '';
            if (isPaper && item.status === 'fee_paid') {
                actionBtn = `<button class="btn-submit" style="padding: 4px 10px; font-size: 0.8rem; width: auto;" onclick="downloadInquiryForm(${item.id})">서식 다운로드</button>`;
            } else if (isPaper && (item.status === 'form_downloaded' || item.status === 'mail_sent')) {
                actionBtn = `<button class="btn-logout" style="padding: 4px 10px; font-size: 0.8rem; width: auto;" onclick="downloadInquiryForm(${item.id})">다시 다운로드</button>`;
            } else {
                actionBtn = '-';
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${dateStr}</td>
                <td style="color: #a78bfa;">${bankName}</td>
                <td>${isPaper ? '서면 발송' : '온라인 발급'}</td>
                <td><span class="status-badge" style="background: rgba(99,102,241,0.1); color: #818cf8; padding: 4px 8px;">${statusStr}</span></td>
                <td>${actionBtn}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // 마법사 열기
    window.showInquiryWizard = function() {
        financeDashboard.style.display = 'none';
        financeWizard.style.display = 'block';
        goToWizardStep(1);
    };

    window.hideInquiryWizard = function() {
        financeWizard.style.display = 'none';
        financeDashboard.style.display = 'block';
        loadInquiryStatus();
    };

    // Step 이동
    window.goToWizardStep = function(stepNum) {
        document.getElementById('wizard-step-1').style.display = 'none';
        document.getElementById('wizard-step-2').style.display = 'none';
        document.getElementById('wizard-step-3').style.display = 'none';
        
        document.getElementById(`wizard-step-${stepNum}`).style.display = 'block';
    };

    // 은행 검색
    window.searchBanks = function() {
        const query = document.getElementById('bank-search-input').value.trim();
        const resultsDiv = document.getElementById('bank-search-results');
        resultsDiv.innerHTML = '';

        const filtered = allBanks.filter(b => b.institution_name.includes(query) || b.institution_code.includes(query));
        
        if(filtered.length === 0) {
            resultsDiv.innerHTML = '<p style="color: var(--text-secondary);">검색 결과가 없습니다.</p>';
            return;
        }

        filtered.forEach(b => {
            const div = document.createElement('div');
            div.style.cssText = 'padding: 15px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; transition: all 0.2s;';
            div.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">${b.institution_name}</div>
                <div style="font-size: 0.8rem; color: #a78bfa;">[${b.institution_code}] ${b.inquiry_type === 'online' ? '온라인발급' : '서면발송'}</div>
            `;
            div.onmouseover = () => div.style.borderColor = '#818cf8';
            div.onmouseout = () => div.style.borderColor = 'rgba(255,255,255,0.1)';
            div.onclick = () => selectBank(b);
            resultsDiv.appendChild(div);
        });
    };

    // 은행 선택
    function selectBank(bank) {
        document.getElementById('selected-bank-id').value = bank.id;
        document.getElementById('selected-bank-type').value = bank.inquiry_type;
        document.getElementById('selected-bank-name').textContent = `${bank.institution_name} (${bank.inquiry_type === 'online' ? '온라인발급' : '서면발송'})`;
        goToWizardStep(2);
    }

    // Step 2 유효성 검사 및 Step 3 이동
    window.validateStep2 = function() {
        const bankId = document.getElementById('selected-bank-id').value;
        const fy = document.getElementById('inquiry-fiscal-year').value;
        
        if(!bankId || !fy) {
            alert('필수 값을 모두 입력해주세요.');
            return;
        }
        
        const type = document.getElementById('selected-bank-type').value;
        if(type === 'online') {
            document.getElementById('online-guide-box').style.display = 'block';
            document.getElementById('paper-guide-box').style.display = 'none';
        } else {
            document.getElementById('online-guide-box').style.display = 'none';
            document.getElementById('paper-guide-box').style.display = 'block';
        }
        
        goToWizardStep(3);
    };

    // 최종 신청
    window.submitInquiryRequest = async function() {
        const bankId = document.getElementById('selected-bank-id').value;
        const fy = document.getElementById('inquiry-fiscal-year').value;
        const type = document.getElementById('selected-bank-type').value;
        const companyNameEl = document.querySelector('.company-highlight');
        const companyName = companyNameEl ? companyNameEl.textContent : '알수없는회사';
        
        try {
            const res = await fetch('/api/inquiry/new', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company_name: companyName,
                    fiscal_year: parseInt(fy),
                    institution_id: parseInt(bankId),
                    inquiry_type: type
                })
            });
            const data = await res.json();
            
            if(data.success) {
                alert(`신청이 완료되었습니다.\\n요청번호: ${data.request_id}`);
                hideInquiryWizard();
            } else {
                alert(`신청 실패: ${data.error}`);
            }
        } catch(e) {
            console.error('Submit error:', e);
            alert('오류가 발생했습니다.');
        }
    };
    
    // 서식 다운로드
    window.downloadInquiryForm = function(requestId) {
        window.location.href = `/api/inquiry/download_form/${requestId}`;
        setTimeout(loadInquiryStatus, 2000);
    };

    // 초기 데이터 로드
    loadFinancialInstitutions();
    
    // 외부조회 탭 클릭 시 목록 새로고침
    const extFinanceTabBtn = document.querySelector('button[data-subtab="sub-ext-finance"]');
    if(extFinanceTabBtn) {
        extFinanceTabBtn.addEventListener('click', () => {
            loadInquiryStatus();
        });
    }
});

// ==========================================
// 관리자 (Admin) - 금융기관 외부조회 신청 관리
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const adminFinanceMenu = document.querySelector('.master-menu-item[data-menu="finance-inquiry"]');
    const adminFinanceView = document.getElementById('finance-inquiry-view');
    const homeDashboardView = document.getElementById('home-dashboard-view');
    
    if (adminFinanceMenu && adminFinanceView) {
        // 메뉴 클릭 시 화면 전환 처리 (기존 메뉴 클릭 이벤트에 기능 추가)
        adminFinanceMenu.addEventListener('click', (e) => {
            e.preventDefault();
            // 모든 뷰 숨기기
            const allCards = document.querySelectorAll('.master-card');
            allCards.forEach(c => c.style.display = 'none');
            
            // 모든 메뉴 active 제거
            const allMenus = document.querySelectorAll('.master-menu-item');
            allMenus.forEach(m => m.classList.remove('active'));
            
            // 대상 뷰 보이기
            adminFinanceView.style.display = 'block';
            adminFinanceMenu.classList.add('active');
            
            window.loadAdminInquiryStatus();
        });
        
        // 홈 메뉴 클릭 시 조치 (다른 메뉴 클릭 처리 확장)
        const homeMenu = document.querySelector('.master-menu-item[data-menu="home"]');
        if(homeMenu) {
            homeMenu.addEventListener('click', () => {
                if(adminFinanceView) adminFinanceView.style.display = 'none';
                if(homeDashboardView) homeDashboardView.style.display = 'block';
            });
        }
    }
});

// 어드민 리스트 로드
window.loadAdminInquiryStatus = async function() {
    try {
        const res = await fetch('/api/admin/inquiry/list');
        if(res.ok) {
            const data = await res.json();
            renderAdminInquiryList(data);
        } else {
            console.error('Failed to fetch admin inquiry list');
        }
    } catch(e) {
        console.error(e);
    }
};

function renderAdminInquiryList(data) {
    const tbody = document.getElementById('admin-inquiry-list');
    if(!tbody) return;
    
    tbody.innerHTML = '';
    if(data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-secondary);">조회 신청 내역이 없습니다.</td></tr>';
        return;
    }
    
    const statusMap = {
        'draft': '작성중',
        'submitted': '신청완료',
        'fee_pending': '입금대기',
        'fee_paid': '입금완료(발송대기)',
        'form_downloaded': '서식다운로드완료',
        'mail_sent': '발송완료',
        'received': '회신완료',
        'completed': '완료',
        'cancelled': '취소'
    };
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        const dateStr = item.created_at ? item.created_at.split('T')[0] : '';
        const bankName = item.financial_institutions ? item.financial_institutions.institution_name : '알수없음';
        const typeStr = item.inquiry_type === 'online' ? '온라인발급' : '서면발송';
        const statusStr = statusMap[item.status] || item.status;
        
        tr.innerHTML = `
            <td><input type="checkbox" class="inquiry-checkbox" value="${item.id}" data-current-status="${item.status}"></td>
            <td>${dateStr}</td>
            <td style="font-weight:bold; color:var(--text-primary);">${item.company_name}</td>
            <td style="color:#a78bfa;">${bankName}</td>
            <td>${typeStr}</td>
            <td><span class="status-badge" style="background:rgba(255,255,255,0.05);">${item.fiscal_year}</span></td>
            <td><span class="status-badge" style="background:rgba(99,102,241,0.1); color:#818cf8;">${statusStr}</span></td>
            <td>
                <button class="btn-logout" style="padding:4px 8px; width:auto; font-size:0.8rem;" onclick="viewInquiryHistory(${item.id})">이력</button>
                <button class="btn-submit" style="padding:4px 8px; width:auto; font-size:0.8rem; margin-left:5px;" onclick="promptUpdateDetail(${item.id})">수정</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 전체 선택
window.toggleAllInquiries = function(checkbox) {
    const checkboxes = document.querySelectorAll('.inquiry-checkbox');
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
};

// 일괄 업데이트
window.updateBulkStatus = async function() {
    const newStatus = document.getElementById('bulk-status-select').value;
    if(!newStatus) {
        alert('변경할 상태를 선택하세요.');
        return;
    }
    
    const checkboxes = document.querySelectorAll('.inquiry-checkbox:checked');
    if(checkboxes.length === 0) {
        alert('업데이트할 항목을 선택하세요.');
        return;
    }
    
    const updates = [];
    checkboxes.forEach(cb => {
        updates.push({
            id: parseInt(cb.value),
            status: newStatus
        });
    });
    
    try {
        const res = await fetch('/api/admin/inquiry/status', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ updates })
        });
        
        const data = await res.json();
        if(data.success) {
            alert(`상태가 성공적으로 변경되었습니다.`);
            window.loadAdminInquiryStatus();
            document.getElementById('check-all-inquiries').checked = false;
        } else {
            alert(`오류: ${data.error}`);
        }
    } catch(e) {
        console.error(e);
        alert('상태 변경 중 오류가 발생했습니다.');
    }
};

window.viewInquiryHistory = async function(requestId) {
    try {
        const res = await fetch(`/api/admin/inquiry/history/${requestId}`);
        if(res.ok) {
            const data = await res.json();
            let msg = `[요청 ID: ${requestId}] 진행 이력\\n\\n`;
            data.forEach(h => {
                msg += `- ${h.created_at}: ${h.previous_status} -> ${h.new_status} (${h.changed_by})\\n`;
            });
            alert(msg);
        }
    } catch(e) {
        console.error(e);
    }
};

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
    
    final_content = original_js + "\n" + correct_js
    with open(path, "w", encoding="utf-8") as f:
        f.write(final_content)

if __name__ == "__main__":
    fix_main_js()
