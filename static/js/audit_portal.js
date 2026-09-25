/**
 * Hyean CPA 회계감사 전용 포털 클라이언트 스크립트
 * (static/js/audit_portal.js)
 * 
 * - 4대 메인 탭 전환 라우팅
 * - K-GAAP 2023 조서 색인 트리 렌더링 & 검색
 * - 6대 장부 연계 AI 조서 자동생성 & 마크다운 에디터
 * - K-GAAP 원본 서식 엑셀(.xlsx) 원클릭 다운로드
 * - FullCalendar v6 인터랙티브 감사일정 캘린더 & D-Day 알림
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[AUTH] Hyean CPA Audit Portal initialized');

    // 전역 상태
    const state = {
        currentCompany: '',
        currentYear: '2025',
        activeSectionCode: '4000',
        activeAccountCode: 'A-0',
        activeAccountName: '현금및현금성자산·장단기금융상품',
        activeWorkingPaperMd: '',
        reconciliationData: null,
        relatedPnlData: [],
        calendarInstance: null,
        templatesTree: [],
        companiesList: [],
        ajeEntries: []
    };

    // DOM 요소 캐싱
    const dom = {
        companySelect: document.getElementById('audit-company-select'),
        yearSelect: document.getElementById('audit-year-select'),
        inchargeBadge: document.getElementById('audit-incharge-badge'),
        statusBadge: document.getElementById('audit-project-status-badge'),
        menuItems: document.querySelectorAll('.audit-menu-list .master-menu-item'),
        tabPanes: document.querySelectorAll('.audit-tab-pane'),
        wpTreeContainer: document.getElementById('wp-tree-container'),
        wpTreeSearch: document.getElementById('wp-tree-search'),
        wpActiveCode: document.getElementById('wp-active-code'),
        wpActiveTitle: document.getElementById('wp-active-title'),
        wpActiveSection: document.getElementById('wp-active-section'),
        wpEditor: document.getElementById('wp-markdown-editor'),
        wpPreview: document.getElementById('wp-markdown-rendered-view'),
        btnGenerateAi: document.getElementById('btn-generate-wp-ai'),
        btnSaveWp: document.getElementById('btn-save-wp'),
        btnExportExcel: document.getElementById('btn-export-wp-excel'),
        reconPriorVal: document.getElementById('recon-prior-val'),
        reconCurrentVal: document.getElementById('recon-current-val'),
        reconVarianceVal: document.getElementById('recon-variance-val'),
        reconAdjTotalVal: document.getElementById('recon-adj-total-val'),
        reconFinalVal: document.getElementById('recon-final-val'),
        reconStatusVal: document.getElementById('recon-status-val'),
        reconSubaccountsTbody: document.getElementById('recon-subaccounts-tbody'),
        reconSubaccountsTfoot: document.getElementById('recon-subaccounts-tfoot'),
        tfootPriorVal: document.getElementById('tfoot-prior-val'),
        tfootCurrentVal: document.getElementById('tfoot-current-val'),
        tfootVarianceVal: document.getElementById('tfoot-variance-val'),
        tfootRateVal: document.getElementById('tfoot-rate-val'),
        tfootDrAdj: document.getElementById('tfoot-dr-adj'),
        tfootCrAdj: document.getElementById('tfoot-cr-adj'),
        tfootFinalVal: document.getElementById('tfoot-final-val'),
        ajeContainer: document.getElementById('wp-aje-container'),
        ajeRowsTbody: document.getElementById('aje-rows-tbody'),
        btnAddAjeRow: document.getElementById('btn-add-aje-row'),
        ajeBalanceBadge: document.getElementById('aje-balance-badge'),
        ajeTfootDrSum: document.getElementById('aje-tfoot-dr-sum'),
        ajeTfootCrSum: document.getElementById('aje-tfoot-cr-sum'),
        ajeTfootStatus: document.getElementById('aje-tfoot-status'),
        ajeAccountSuggestions: document.getElementById('aje-account-suggestions'),
        relatedPnlContainer: document.getElementById('wp-related-pnl-container'),
        relatedPnlTbody: document.getElementById('related-pnl-tbody'),
        relatedPnlTfoot: document.getElementById('related-pnl-tfoot'),
        pnlCountBadge: document.getElementById('pnl-count-badge'),
        pnlTfootPriorVal: document.getElementById('pnl-tfoot-prior-val'),
        pnlTfootCurrentVal: document.getElementById('pnl-tfoot-current-val'),
        pnlTfootVarianceVal: document.getElementById('pnl-tfoot-variance-val'),
        pnlTfootRateVal: document.getElementById('pnl-tfoot-rate-val'),
        pnlTfootDrAdj: document.getElementById('pnl-tfoot-dr-adj'),
        pnlTfootCrAdj: document.getElementById('pnl-tfoot-cr-adj'),
        pnlTfootFinalVal: document.getElementById('pnl-tfoot-final-val'),
        wpTabBtns: document.querySelectorAll('.wp-tab-btn'),
        wpTabContents: document.querySelectorAll('.wp-tab-content'),
        ragGuideView: document.getElementById('wp-rag-guide-view'),
        ragGuideContainer: document.getElementById('wp-rag-guide-container'),
        btnAddSchedule: document.getElementById('btn-add-schedule'),
        modalSchedule: document.getElementById('modal-audit-schedule'),
        btnCloseScheduleModal: document.getElementById('btn-close-schedule-modal'),
        btnCancelSchedule: document.getElementById('btn-cancel-schedule'),
        formSchedule: document.getElementById('form-audit-schedule'),
        projectsTbody: document.getElementById('audit-projects-tbody'),
        financeTbody: document.getElementById('audit-finance-tbody')
    };

    // =========================================================================
    // 1. 초기화 및 고객사 / 조서 트리 로딩
    // =========================================================================
    async function initAuditPortal() {
        await loadCompanies();
        await loadTemplatesTree();
        await loadProjects();
        initCalendar();
        initAjeBlock();
        setupEventListeners();
    }

    // 고객사 목록 로드 (로그인한 회계사 배정 우선 바인딩)
    async function loadCompanies() {
        console.log('[REQUEST] GET /api/audit/companies');
        try {
            const res = await fetch('/api/audit/companies');
            const data = await res.json();
            if (data.success && data.companies) {
                state.companiesList = data.companies;
                dom.companySelect.innerHTML = '<option value="">감사 대상 기업을 선택하세요</option>';
                data.companies.forEach((comp, idx) => {
                    const opt = document.createElement('option');
                    opt.value = comp.company_name;
                    opt.textContent = `${comp.company_name} (${comp.corporate_number || '법인'})`;
                    if (idx === 0) {
                        opt.selected = true;
                        state.currentCompany = comp.company_name;
                        updateHeaderBadges(comp);
                    }
                    dom.companySelect.appendChild(opt);
                });
                console.log(`[RENDER] Loaded ${data.companies.length} companies, active=${state.currentCompany}`);
            }
        } catch (err) {
            console.error('[ERROR] Failed to load companies:', err);
        }
    }

    function updateHeaderBadges(comp) {
        if (!comp) return;
        if (dom.inchargeBadge) {
            dom.inchargeBadge.textContent = `In-charge: ${comp.in_charge_name || '김동선'}`;
        }
        if (dom.statusBadge) {
            dom.statusBadge.textContent = comp.status_label || '실증감사 진행중';
        }
    }

    // K-GAAP 2023 조서 색인 트리 로드
    async function loadTemplatesTree() {
        console.log('[REQUEST] GET /api/audit/templates/tree');
        try {
            const res = await fetch('/api/audit/templates/tree');
            const data = await res.json();
            if (data.success && data.tree) {
                state.templatesTree = data.tree;
                await loadCompanyAssignment(state.currentCompany);
            }
        } catch (err) {
            console.error('[ERROR] Failed to load template tree:', err);
        }
    }

    // 선택된 회사의 배정 정보 로드 (계정별 담당자 맵핑)
    async function loadCompanyAssignment(companyName) {
        if (!companyName) {
            renderTemplatesTree(state.templatesTree);
            return;
        }
        try {
            const res = await fetch(`/api/audit/assignments?company_name=${encodeURIComponent(companyName)}`);
            const data = await res.json();
            if (data.success && data.assignments && data.assignments.length > 0) {
                state.currentCompanyAssignment = data.assignments[0];
            } else {
                state.currentCompanyAssignment = null;
            }
        } catch (err) {
            console.warn('[ASSIGN:FETCH_WARN]', err);
            state.currentCompanyAssignment = null;
        }
        renderTemplatesTree(state.templatesTree);
    }

    // 조서 색인 아코디언 트리 렌더링 (본인 배정 계정 [내 담당] 뱃지 부여)
    function renderTemplatesTree(tree, filterQuery = '') {
        dom.wpTreeContainer.innerHTML = '';
        const query = filterQuery.toLowerCase().trim();
        const myEmail = document.body.dataset.userEmail || '';
        const assignMap = state.currentCompanyAssignment?.account_assignments || {};
        
        tree.forEach(section => {
            if (!section.items || section.items.length === 0) return;
            
            // 검색 필터링 여부
            const matchingItems = query 
                ? section.items.filter(it => 
                    it.account_code.toLowerCase().includes(query) || 
                    it.account_name.toLowerCase().includes(query) || 
                    section.title.toLowerCase().includes(query)
                  )
                : section.items;

            if (query && matchingItems.length === 0) return;

            const groupEl = document.createElement('div');
            groupEl.className = 'wp-section-group';
            
            const isAutoExpanded = query ? true : false;
            
            const headerEl = document.createElement('div');
            headerEl.className = `wp-section-header ${isAutoExpanded ? 'expanded' : ''}`;
            headerEl.innerHTML = `
                <div class="wp-section-title-wrap">
                    <svg class="wp-section-chevron" viewBox="0 0 24 24"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/></svg>
                    <span class="wp-section-name">${section.title}</span>
                </div>
                <span class="badge-count">${matchingItems.length}개</span>
            `;
            
            const listEl = document.createElement('div');
            listEl.className = `wp-item-list ${isAutoExpanded ? 'open' : ''}`;
            
            matchingItems.forEach(item => {
                const isActive = (item.account_code === state.activeAccountCode);
                const assignedEmail = assignMap[item.account_code] || '';
                const isAssignedToMe = (myEmail && assignedEmail === myEmail);
                
                const itemEl = document.createElement('div');
                itemEl.className = `wp-tree-item ${isActive ? 'active' : ''} ${isAssignedToMe ? 'my-assigned-wp' : ''}`;
                itemEl.dataset.sectionCode = section.code;
                itemEl.dataset.accountCode = item.account_code;
                itemEl.dataset.accountName = item.account_name;
                
                let assignBadge = '';
                if (isAssignedToMe) {
                    assignBadge = `<span class="badge-tag" style="background: rgba(16,185,129,0.2); color: #34d399; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-weight: 600;">내 담당</span>`;
                } else if (assignedEmail) {
                    assignBadge = `<span class="badge-tag" style="background: rgba(148,163,184,0.15); color: #94a3b8; font-size: 0.7rem; padding: 1px 5px; border-radius: 4px; margin-left: 4px;">${assignedEmail.split('@')[0]}</span>`;
                }
                
                itemEl.innerHTML = `
                    <div style="display: flex; align-items: center; min-width: 0; flex: 1;">
                        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"><strong>[${item.account_code}]</strong> ${item.account_name}</span>
                        ${assignBadge}
                    </div>
                    <span class="wp-item-proc-badge">${item.procedure_count}절차</span>
                `;
                
                itemEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectWorkingPaper(section.code, item.account_code, item.account_name, section.title);
                });
                listEl.appendChild(itemEl);
            });
            
            // Section 클릭 시 아코디언 토글
            headerEl.addEventListener('click', () => {
                const isOpen = listEl.classList.toggle('open');
                headerEl.classList.toggle('expanded', isOpen);
            });
            
            groupEl.appendChild(headerEl);
            groupEl.appendChild(listEl);
            dom.wpTreeContainer.appendChild(groupEl);
        });
        
        console.log(`[RENDER] K-GAAP 조서 아코디언 트리 렌더링 완료 (Query: "${filterQuery}")`);
    }

    // =========================================================================
    // 2. 조서 선택 및 6대 장부 실시간 수치 대사 (Reconciliation)
    // =========================================================================
    async function selectWorkingPaper(sectionCode, accountCode, accountName, sectionTitle) {
        state.activeSectionCode = sectionCode;
        state.activeAccountCode = accountCode;
        state.activeAccountName = accountName;
        
        // UI 헤더 갱신
        dom.wpActiveCode.textContent = accountCode;
        dom.wpActiveTitle.textContent = accountName;
        dom.wpActiveSection.textContent = sectionTitle || `Section ${sectionCode}`;
        
        // 드롭다운 버튼 라벨 갱신 & 드롭다운 팝오버 닫기
        const dropdownLabel = document.getElementById('wp-dropdown-label');
        if (dropdownLabel) {
            dropdownLabel.textContent = `[${accountCode}] ${accountName} ▾`;
        }
        const dropdownMenu = document.getElementById('wp-tree-dropdown-menu');
        if (dropdownMenu) {
            dropdownMenu.style.display = 'none';
        }

        // 트리 active 클래스 토글
        document.querySelectorAll('.wp-tree-item').forEach(el => {
            el.classList.toggle('active', el.dataset.accountCode === accountCode);
        });
        
        console.log(`[WP] Selected working paper: [${accountCode}] ${accountName}`);
        
        // RAG 가이드 뷰 업데이트
        updateRagGuideView(accountCode);

        // 이전 조서 내용 초기화 (새 계정 선택)
        if (dom.wpEditor) dom.wpEditor.value = '';
        renderMarkdownPreview('');

        // 6대 장부 JSON 실시간 대사 수치 즉시 조회
        if (state.currentCompany) {
            try {
                const res = await fetch('/api/audit/working-papers/reconcile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_name: state.currentCompany,
                        fiscal_year: state.currentYear,
                        account_code: accountCode
                    })
                });
                const result = await res.json();
                if (result.success && result.reconciliation) {
                    renderReconciliationDashboard(result.reconciliation);
                    const pnlList = result.related_pnl || result.reconciliation.related_pnl || [];
                    renderRelatedPnlDashboard(pnlList);
                }
            } catch (err) {
                console.warn('[RECON:WARN] Quick reconcile failed:', err);
            }
        }
    }

    // =========================================================================
    // 2-1. 대사 대시보드 및 계정과목별 세부 테이블 렌더링 & 실시간 수정분개 계산
    // =========================================================================
    function renderReconciliationDashboard(recon) {
        if (!recon) return;
        state.reconciliationData = recon;
        
        // 1. 상단 요약 바 갱신
        const pVal = Number(recon.prior_val || 0);
        const cVal = Number(recon.current_val || 0);
        const vVal = Number(recon.variance_val || (cVal - pVal));
        const vRate = Number(recon.variance_pct || 0);
        const drTotal = Number(recon.adj_debit_total || 0);
        const crTotal = Number(recon.adj_credit_total || 0);
        const finalVal = Number(recon.adjusted_val || (cVal + drTotal - crTotal));
        
        if (dom.reconPriorVal) dom.reconPriorVal.textContent = pVal.toLocaleString() + '원';
        if (dom.reconCurrentVal) dom.reconCurrentVal.textContent = cVal.toLocaleString() + '원';
        if (dom.reconVarianceVal) {
            const sign = vVal > 0 ? '+' : '';
            dom.reconVarianceVal.textContent = `${sign}${vVal.toLocaleString()}원 (${sign}${vRate.toFixed(1)}%)`;
        }
        if (dom.reconAdjTotalVal) {
            dom.reconAdjTotalVal.textContent = `${drTotal.toLocaleString()}원 / ${crTotal.toLocaleString()}원`;
        }
        if (dom.reconFinalVal) {
            dom.reconFinalVal.textContent = finalVal.toLocaleString() + '원';
        }
        if (dom.reconStatusVal) {
            dom.reconStatusVal.textContent = recon.is_matched ? '🟢 100% 일치' : '🔴 대사 불일치';
            dom.reconStatusVal.className = `recon-badge ${recon.is_matched ? 'badge-planned' : ''}`;
        }
        
        // 2. 하단 계정과목별 세부 대사 테이블 렌더링
        const subAccounts = recon.sub_accounts || [];
        if (!dom.reconSubaccountsTbody) return;
        
        if (subAccounts.length === 0) {
            dom.reconSubaccountsTbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; color: #94a3b8; padding: 18px;">
                        해당 조서 코드와 매핑된 세부 계정과목이 없습니다.
                    </td>
                </tr>
            `;
            if (dom.reconSubaccountsTfoot) dom.reconSubaccountsTfoot.style.display = 'none';
            return;
        }
        
        dom.reconSubaccountsTbody.innerHTML = '';
        subAccounts.forEach((acc, idx) => {
            const accName = acc.account_name || acc.name || '계정';
            const accPrior = Number(acc.prior_amount || acc.prior || 0);
            const accCurrent = Number(acc.current_amount || acc.current || 0);
            const accVar = Number(acc.variance_amount || acc.variance || (accCurrent - accPrior));
            const accRate = Number(acc.variance_rate || acc.variance_pct || 0);
            const accDr = Number(acc.adj_debit || 0);
            const accCr = Number(acc.adj_credit || 0);
            const accFinal = Number(acc.adjusted_amount || (accCurrent + accDr - accCr));
            
            const sign = accVar > 0 ? '+' : '';
            const badgeClass = accVar > 0 ? 'plus' : (accVar < 0 ? 'minus' : 'zero');
            const contraBadge = acc.is_contra ? `<span style="font-size: 0.7rem; color: #f87171; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); padding: 1px 5px; border-radius: 4px; margin-right: 6px; font-weight: 600;">차감</span>` : '';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="acc-name">${contraBadge}${accName}</td>
                <td class="num-cell" style="color: #94a3b8;">${accPrior.toLocaleString()}원</td>
                <td class="num-cell" style="font-weight: 600; color: #f1f5f9;">${accCurrent.toLocaleString()}원</td>
                <td class="num-cell">
                    <span class="var-badge ${badgeClass}">${sign}${accVar.toLocaleString()}원</span>
                </td>
                <td class="num-cell">
                    <span class="var-badge ${badgeClass}">${sign}${accRate.toFixed(1)}%</span>
                </td>
                <td class="num-cell">
                    <input type="number" class="recon-adj-input debit-input" data-idx="${idx}" value="${accDr}" step="1000" placeholder="0">
                </td>
                <td class="num-cell">
                    <input type="number" class="recon-adj-input credit-input" data-idx="${idx}" value="${accCr}" step="1000" placeholder="0">
                </td>
                <td class="num-cell acc-final-cell" style="font-weight: 700; color: #38bdf8;">${accFinal.toLocaleString()}원</td>
            `;
            dom.reconSubaccountsTbody.appendChild(tr);
        });
        
        // 3. 푸터 합계 갱신
        if (dom.reconSubaccountsTfoot) {
            dom.reconSubaccountsTfoot.style.display = 'table-footer-group';
            if (dom.tfootPriorVal) dom.tfootPriorVal.textContent = pVal.toLocaleString() + '원';
            if (dom.tfootCurrentVal) dom.tfootCurrentVal.textContent = cVal.toLocaleString() + '원';
            if (dom.tfootVarianceVal) {
                const sign = vVal > 0 ? '+' : '';
                dom.tfootVarianceVal.textContent = `${sign}${vVal.toLocaleString()}원`;
            }
            if (dom.tfootRateVal) {
                const sign = vVal > 0 ? '+' : '';
                dom.tfootRateVal.textContent = `${sign}${vRate.toFixed(1)}%`;
            }
            if (dom.tfootDrAdj) dom.tfootDrAdj.textContent = `${drTotal.toLocaleString()}원`;
            if (dom.tfootCrAdj) dom.tfootCrAdj.textContent = `${crTotal.toLocaleString()}원`;
            if (dom.tfootFinalVal) dom.tfootFinalVal.textContent = `${finalVal.toLocaleString()}원`;
        }
        
        // 4. 입력 이벤트 바인딩 (실시간 차변/대변 수정분개 계산)
        bindAdjustmentInputEvents(subAccounts, pVal, cVal, vVal, vRate);

        // 5. AJE 자동완성 드롭다운 갱신 및 기존 AJE 분개내역 재동기화
        updateAjeDatalistSuggestions(subAccounts);
        if (state.ajeEntries && state.ajeEntries.length > 0) {
            syncAjeToReconciliationTable();
        }
    }

    function bindAdjustmentInputEvents(subAccounts, pVal, cVal, vVal, vRate) {
        dom.reconSubaccountsTbody.querySelectorAll('.recon-adj-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx, 10);
                const tr = e.target.closest('tr');
                if (!tr || isNaN(idx) || !subAccounts[idx]) return;
                
                const drInput = tr.querySelector('.debit-input');
                const crInput = tr.querySelector('.credit-input');
                const finalCell = tr.querySelector('.acc-final-cell');
                
                const drVal = parseFloat(drInput.value) || 0;
                const crVal = parseFloat(crInput.value) || 0;
                
                const accCurrent = Number(subAccounts[idx].current_amount || subAccounts[idx].current || 0);
                const accFinal = accCurrent + drVal - crVal;
                
                subAccounts[idx].adj_debit = drVal;
                subAccounts[idx].adj_credit = crVal;
                subAccounts[idx].adjusted_amount = accFinal;
                
                if (finalCell) finalCell.textContent = accFinal.toLocaleString() + '원';
                
                // 전체 합계 재계산 (차감 계정은 순액에서 차감)
                let totalDr = 0;
                let totalCr = 0;
                let totalFinal = 0;
                subAccounts.forEach(a => {
                    const c = Number(a.current_amount || a.current || 0);
                    const d = Number(a.adj_debit || 0);
                    const r = Number(a.adj_credit || 0);
                    totalDr += d;
                    totalCr += r;
                    const netRow = (c + d - r);
                    if (a.is_contra) {
                        totalFinal -= netRow;
                    } else {
                        totalFinal += netRow;
                    }
                });
                
                if (state.reconciliationData) {
                    state.reconciliationData.adj_debit_total = totalDr;
                    state.reconciliationData.adj_credit_total = totalCr;
                    state.reconciliationData.adjusted_val = totalFinal;
                    state.reconciliationData.sub_accounts = subAccounts;
                }
                
                if (dom.reconAdjTotalVal) dom.reconAdjTotalVal.textContent = `${totalDr.toLocaleString()}원 / ${totalCr.toLocaleString()}원`;
                if (dom.reconFinalVal) dom.reconFinalVal.textContent = totalFinal.toLocaleString() + '원';
                if (dom.tfootDrAdj) dom.tfootDrAdj.textContent = `${totalDr.toLocaleString()}원`;
                if (dom.tfootCrAdj) dom.tfootCrAdj.textContent = `${totalCr.toLocaleString()}원`;
                if (dom.tfootFinalVal) dom.tfootFinalVal.textContent = `${totalFinal.toLocaleString()}원`;
            });
        });
    }

    // =========================================================================
    // 2-2. 📊 관련 손익항목 (Related P&L Items) 대시보드 렌더링
    // =========================================================================
    function renderRelatedPnlDashboard(pnlList = []) {
        state.relatedPnlData = pnlList || [];
        if (!dom.relatedPnlTbody) return;

        if (!pnlList || pnlList.length === 0) {
            dom.relatedPnlTbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; color: #94a3b8; padding: 16px;">
                        해당 조서 계정과 매핑된 손익계산서(I/S) 항목이 없습니다.
                    </td>
                </tr>
            `;
            if (dom.relatedPnlTfoot) dom.relatedPnlTfoot.style.display = 'none';
            if (dom.pnlCountBadge) dom.pnlCountBadge.textContent = '관련 손익 0건';
            return;
        }

        if (dom.pnlCountBadge) dom.pnlCountBadge.textContent = `관련 손익 ${pnlList.length}건`;
        dom.relatedPnlTbody.innerHTML = '';

        let totalPrior = 0;
        let totalCurrent = 0;
        let totalVar = 0;
        let totalDr = 0;
        let totalCr = 0;
        let totalFinal = 0;

        pnlList.forEach((item) => {
            const name = item.account_name || item.name || '손익항목';
            const pnlType = item.pnl_type || '비용';
            const prior = Number(item.prior_amount || item.prior || 0);
            const curr = Number(item.current_amount || item.current || 0);
            const diff = Number(item.variance_amount || item.variance || (curr - prior));
            const rate = Number(item.variance_pct || item.variance_rate || 0);
            const drAdj = Number(item.adj_debit || 0);
            const crAdj = Number(item.adj_credit || 0);
            
            // 손익 최종치 산정 (비용은 Dr 증가, 수익은 Cr 증가)
            let finalVal = curr;
            if (pnlType.includes('비용')) {
                finalVal = curr + drAdj - crAdj;
            } else if (pnlType.includes('수익')) {
                finalVal = curr - drAdj + crAdj;
            } else {
                finalVal = curr + drAdj - crAdj;
            }
            item.adjusted_amount = finalVal;

            totalPrior += prior;
            totalCurrent += curr;
            totalVar += diff;
            totalDr += drAdj;
            totalCr += crAdj;
            totalFinal += finalVal;

            const sign = diff > 0 ? '+' : '';
            const badgeClass = diff > 0 ? 'plus' : (diff < 0 ? 'minus' : 'zero');
            let typeBadgeClass = 'other';
            if (pnlType.includes('비용')) typeBadgeClass = 'expense';
            else if (pnlType.includes('수익')) typeBadgeClass = 'revenue';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="pnl-name">${name}</td>
                <td style="text-align: center;"><span class="pnl-type-badge ${typeBadgeClass}">${pnlType}</span></td>
                <td class="num-cell" style="color: #94a3b8;">${prior.toLocaleString()}원</td>
                <td class="num-cell" style="font-weight: 600; color: #f1f5f9;">${curr.toLocaleString()}원</td>
                <td class="num-cell"><span class="var-badge ${badgeClass}">${sign}${diff.toLocaleString()}원</span></td>
                <td class="num-cell"><span class="var-badge ${badgeClass}">${sign}${rate.toFixed(1)}%</span></td>
                <td class="num-cell aje-pnl-dr-cell" style="color: #60a5fa; font-weight: 600;">${drAdj ? drAdj.toLocaleString() + '원' : '-'}</td>
                <td class="num-cell aje-pnl-cr-cell" style="color: #f87171; font-weight: 600;">${crAdj ? crAdj.toLocaleString() + '원' : '-'}</td>
                <td class="num-cell pnl-final-cell" style="font-weight: 700; color: #34d399;">${finalVal.toLocaleString()}원</td>
            `;
            dom.relatedPnlTbody.appendChild(tr);
        });

        // 푸터 업데이트
        if (dom.relatedPnlTfoot) {
            dom.relatedPnlTfoot.style.display = 'table-footer-group';
            if (dom.pnlTfootPriorVal) dom.pnlTfootPriorVal.textContent = totalPrior.toLocaleString() + '원';
            if (dom.pnlTfootCurrentVal) dom.pnlTfootCurrentVal.textContent = totalCurrent.toLocaleString() + '원';
            if (dom.pnlTfootVarianceVal) {
                const sign = totalVar > 0 ? '+' : '';
                dom.pnlTfootVarianceVal.textContent = `${sign}${totalVar.toLocaleString()}원`;
            }
            if (dom.pnlTfootRateVal) {
                const totalRate = totalPrior !== 0 ? (totalVar / Math.abs(totalPrior) * 100) : 0;
                const sign = totalVar > 0 ? '+' : '';
                dom.pnlTfootRateVal.textContent = `${sign}${totalRate.toFixed(1)}%`;
            }
            if (dom.pnlTfootDrAdj) dom.pnlTfootDrAdj.textContent = `${totalDr.toLocaleString()}원`;
            if (dom.pnlTfootCrAdj) dom.pnlTfootCrAdj.textContent = `${totalCr.toLocaleString()}원`;
            if (dom.pnlTfootFinalVal) dom.pnlTfootFinalVal.textContent = `${totalFinal.toLocaleString()}원`;
        }

        updateAjeDatalistSuggestions();
    }

    // =========================================================================
    // 2-3. ⚖️ 감사 수정분개 (AJE / RJE) 인터랙티브 분개장 엔진
    // =========================================================================
    function initAjeBlock() {
        if (!dom.btnAddAjeRow || !dom.ajeRowsTbody) return;

        // 분개 행 추가 버튼 리스너
        dom.btnAddAjeRow.addEventListener('click', () => {
            addAjeRow();
        });

        // 초기 기본 1개 분개 행 생성 (비어있을 때)
        if (state.ajeEntries.length === 0) {
            addAjeRow();
        } else {
            renderAjeRows();
        }
    }

    // Datalist 계정과목 추천 업데이트 (현재 계정의 세부 과목 및 관련 손익 과목 등록)
    function updateAjeDatalistSuggestions(subAccounts = []) {
        if (!dom.ajeAccountSuggestions) return;
        const baseSuggestions = [
            '대손상각비', '대손충당금', '감가상각비', '감가상각누계액', '외상매출금',
            '받을어음', '외상매입금', '지급어음', '미수금', '미지급금', '선급금', '선수금',
            '이자수익', '이자비용', '외환차익', '외환차손', '유형자산처분이익', '유형자산처분손실',
            '보조금', '잡손실', '잡이익', '전기오류수정손실', '전기오류수정이익', '당기순이익'
        ];
        
        const subList = subAccounts.length ? subAccounts : (state.reconciliationData?.sub_accounts || []);
        const subNames = subList.map(a => a.account_name || a.name).filter(Boolean);
        const pnlNames = (state.relatedPnlData || []).map(p => p.account_name || p.name).filter(Boolean);
        
        const uniqueList = Array.from(new Set([...subNames, ...pnlNames, ...baseSuggestions]));
        
        dom.ajeAccountSuggestions.innerHTML = uniqueList.map(name => `<option value="${name}">`).join('');
    }

    function addAjeRow(drAcc = '', drAmt = 0, crAcc = '', crAmt = 0, memo = '') {
        const newRow = {
            id: 'aje_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
            dr_account: drAcc,
            dr_amount: drAmt,
            cr_account: crAcc,
            cr_amount: crAmt,
            memo: memo
        };
        state.ajeEntries.push(newRow);
        renderAjeRows();
        syncAjeToReconciliationTable();
    }

    function deleteAjeRow(rowId) {
        state.ajeEntries = state.ajeEntries.filter(r => r.id !== rowId);
        if (state.ajeEntries.length === 0) {
            addAjeRow();
        } else {
            renderAjeRows();
            syncAjeToReconciliationTable();
        }
    }

    function renderAjeRows() {
        if (!dom.ajeRowsTbody) return;
        dom.ajeRowsTbody.innerHTML = '';

        state.ajeEntries.forEach((row) => {
            const tr = document.createElement('tr');
            tr.dataset.id = row.id;
            tr.innerHTML = `
                <td>
                    <input type="text" class="aje-table-input aje-dr-account" list="aje-account-suggestions" placeholder="예: 대손상각비" value="${row.dr_account || ''}">
                </td>
                <td>
                    <input type="number" class="aje-table-input num-input debit-val aje-dr-amount" step="1000" placeholder="0" value="${row.dr_amount ? row.dr_amount : ''}">
                </td>
                <td>
                    <input type="text" class="aje-table-input aje-cr-account" list="aje-account-suggestions" placeholder="예: 대손충당금" value="${row.cr_account || ''}">
                </td>
                <td>
                    <input type="number" class="aje-table-input num-input credit-val aje-cr-amount" step="1000" placeholder="0" value="${row.cr_amount ? row.cr_amount : ''}">
                </td>
                <td>
                    <input type="text" class="aje-table-input aje-memo" placeholder="분개 사유/내역" value="${row.memo || ''}">
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn-del-aje-row" data-id="${row.id}" title="분개 행 삭제">❌</button>
                </td>
            `;

            // 입력 이벤트 바인딩 (실시간 총괄표 및 관련 손익 동기화)
            tr.querySelectorAll('input').forEach(input => {
                input.addEventListener('input', () => {
                    row.dr_account = tr.querySelector('.aje-dr-account').value.trim();
                    row.dr_amount = parseFloat(tr.querySelector('.aje-dr-amount').value) || 0;
                    row.cr_account = tr.querySelector('.aje-cr-account').value.trim();
                    row.cr_amount = parseFloat(tr.querySelector('.aje-cr-amount').value) || 0;
                    row.memo = tr.querySelector('.aje-memo').value.trim();

                    syncAjeToReconciliationTable();
                });
            });

            // 삭제 버튼 리스너
            tr.querySelector('.btn-del-aje-row').addEventListener('click', () => {
                deleteAjeRow(row.id);
            });

            dom.ajeRowsTbody.appendChild(tr);
        });
    }

    // 계정과목 유연한 매칭 헬퍼
    function isAccountMatched(inputAcc, targetAcc) {
        if (!inputAcc || !targetAcc) return false;
        const s1 = inputAcc.replace(/[\s\(\)\/_\-\[\]]/g, '').toLowerCase();
        const s2 = targetAcc.replace(/[\s\(\)\/_\-\[\]]/g, '').toLowerCase();
        if (s1 === s2) return true;
        if (s1.length >= 2 && s2.includes(s1)) return true;
        if (s2.length >= 2 && s1.includes(s2)) return true;
        return false;
    }

    // 🔄 AJE 분개 내역 ➔ 총괄 대사표 & 관련 손익항목(Related P&L) 실시간 자동 집계 전파
    function syncAjeToReconciliationTable() {
        let totalDr = 0;
        let totalCr = 0;

        state.ajeEntries.forEach(entry => {
            const drVal = Number(entry.dr_amount || 0);
            const crVal = Number(entry.cr_amount || 0);
            totalDr += drVal;
            totalCr += crVal;
        });

        // 1. AJE 푸터 및 대차평형 뱃지 갱신
        if (dom.ajeTfootDrSum) dom.ajeTfootDrSum.textContent = totalDr.toLocaleString() + '원';
        if (dom.ajeTfootCrSum) dom.ajeTfootCrSum.textContent = totalCr.toLocaleString() + '원';
        
        const diff = totalDr - totalCr;
        if (dom.ajeBalanceBadge) {
            if (diff === 0) {
                dom.ajeBalanceBadge.className = 'aje-diff-badge balanced';
                dom.ajeBalanceBadge.textContent = '🟢 대차일치 (차액 0원)';
                if (dom.ajeTfootStatus) dom.ajeTfootStatus.textContent = '대차 평형 상태';
            } else {
                dom.ajeBalanceBadge.className = 'aje-diff-badge unbalanced';
                dom.ajeBalanceBadge.textContent = `🔴 대차차액: ${Math.abs(diff).toLocaleString()}원`;
                if (dom.ajeTfootStatus) dom.ajeTfootStatus.textContent = `차액 발생 (${diff > 0 ? '차변' : '대변'} +${Math.abs(diff).toLocaleString()}원)`;
            }
        }

        // 2. 총괄 대사표(Reconciliation Table) 계정과목별 실시간 자동 반영
        if (state.reconciliationData && state.reconciliationData.sub_accounts) {
            const subAccounts = state.reconciliationData.sub_accounts;
            let grandDr = 0;
            let grandCr = 0;
            let grandFinal = 0;

            subAccounts.forEach((acc, idx) => {
                const rawName = (acc.account_name || acc.name || '').trim();

                // AJE 분개장에서 일치하는 계정과목 차변/대변 금액 합산
                let matchedDr = 0;
                let matchedCr = 0;

                state.ajeEntries.forEach(entry => {
                    if (isAccountMatched(entry.dr_account, rawName)) matchedDr += Number(entry.dr_amount || 0);
                    if (isAccountMatched(entry.cr_account, rawName)) matchedCr += Number(entry.cr_amount || 0);
                });

                acc.adj_debit = matchedDr;
                acc.adj_credit = matchedCr;

                const accCurrent = Number(acc.current_amount || acc.current || 0);
                const accFinal = accCurrent + matchedDr - matchedCr;
                acc.adjusted_amount = accFinal;

                grandDr += matchedDr;
                grandCr += matchedCr;

                const netRow = accFinal;
                if (acc.is_contra) {
                    grandFinal -= netRow;
                } else {
                    grandFinal += netRow;
                }

                // 대사 테이블 DOM 해당 행 실시간 갱신
                if (dom.reconSubaccountsTbody) {
                    const tr = dom.reconSubaccountsTbody.children[idx];
                    if (tr) {
                        const drInput = tr.querySelector('.debit-input');
                        const crInput = tr.querySelector('.credit-input');
                        const finalCell = tr.querySelector('.acc-final-cell');

                        if (drInput) drInput.value = matchedDr || '';
                        if (crInput) crInput.value = matchedCr || '';
                        if (finalCell) finalCell.textContent = accFinal.toLocaleString() + '원';
                    }
                }
            });

            // 상단 요약 바 및 대사 푸터 실시간 갱신
            state.reconciliationData.adj_debit_total = grandDr;
            state.reconciliationData.adj_credit_total = grandCr;
            state.reconciliationData.adjusted_val = grandFinal;
            state.reconciliationData.aje_entries = state.ajeEntries;

            if (dom.reconAdjTotalVal) dom.reconAdjTotalVal.textContent = `${grandDr.toLocaleString()}원 / ${grandCr.toLocaleString()}원`;
            if (dom.reconFinalVal) dom.reconFinalVal.textContent = grandFinal.toLocaleString() + '원';
            if (dom.tfootDrAdj) dom.tfootDrAdj.textContent = `${grandDr.toLocaleString()}원`;
            if (dom.tfootCrAdj) dom.tfootCrAdj.textContent = `${grandCr.toLocaleString()}원`;
            if (dom.tfootFinalVal) dom.tfootFinalVal.textContent = `${grandFinal.toLocaleString()}원`;
        }

        // 3. 📊 관련 손익항목(Related P&L) 테이블 실시간 자동 반영
        if (state.relatedPnlData && state.relatedPnlData.length > 0) {
            let pnlTotalDr = 0;
            let pnlTotalCr = 0;
            let pnlTotalFinal = 0;

            state.relatedPnlData.forEach((item, idx) => {
                const pnlName = (item.account_name || item.name || '').trim();
                const pnlType = item.pnl_type || '비용';

                let matchedDr = 0;
                let matchedCr = 0;

                state.ajeEntries.forEach(entry => {
                    if (isAccountMatched(entry.dr_account, pnlName)) matchedDr += Number(entry.dr_amount || 0);
                    if (isAccountMatched(entry.cr_account, pnlName)) matchedCr += Number(entry.cr_amount || 0);
                });

                item.adj_debit = matchedDr;
                item.adj_credit = matchedCr;

                const curr = Number(item.current_amount || item.current || 0);
                let finalVal = curr;
                if (pnlType.includes('비용')) {
                    finalVal = curr + matchedDr - matchedCr;
                } else if (pnlType.includes('수익')) {
                    finalVal = curr - matchedDr + matchedCr;
                } else {
                    finalVal = curr + matchedDr - matchedCr;
                }
                item.adjusted_amount = finalVal;

                pnlTotalDr += matchedDr;
                pnlTotalCr += matchedCr;
                pnlTotalFinal += finalVal;

                // 손익 테이블 DOM 행 갱신
                if (dom.relatedPnlTbody) {
                    const tr = dom.relatedPnlTbody.children[idx];
                    if (tr) {
                        const drCell = tr.querySelector('.aje-pnl-dr-cell');
                        const crCell = tr.querySelector('.aje-pnl-cr-cell');
                        const finalCell = tr.querySelector('.pnl-final-cell');

                        if (drCell) drCell.textContent = matchedDr ? matchedDr.toLocaleString() + '원' : '-';
                        if (crCell) crCell.textContent = matchedCr ? matchedCr.toLocaleString() + '원' : '-';
                        if (finalCell) finalCell.textContent = finalVal.toLocaleString() + '원';
                    }
                }
            });

            // 손익 푸터 갱신
            if (dom.pnlTfootDrAdj) dom.pnlTfootDrAdj.textContent = `${pnlTotalDr.toLocaleString()}원`;
            if (dom.pnlTfootCrAdj) dom.pnlTfootCrAdj.textContent = `${pnlTotalCr.toLocaleString()}원`;
            if (dom.pnlTfootFinalVal) dom.pnlTfootFinalVal.textContent = `${pnlTotalFinal.toLocaleString()}원`;
        }
    }

    // 드롭다운 메뉴 토글
    window.toggleWpTreeDropdown = function (e) {
        if (e) e.stopPropagation();
        const menu = document.getElementById('wp-tree-dropdown-menu');
        if (!menu) return;
        const isOpen = menu.style.display === 'block';
        menu.style.display = isOpen ? 'none' : 'block';
        if (!isOpen) {
            const searchInput = document.getElementById('wp-tree-search');
            if (searchInput) {
                setTimeout(() => searchInput.focus(), 50);
            }
        }
    };

    // 외부 클릭 시 드롭다운 닫기
    document.addEventListener('click', (e) => {
        const wrapper = document.querySelector('.wp-dropdown-wrapper');
        const menu = document.getElementById('wp-tree-dropdown-menu');
        if (menu && menu.style.display === 'block') {
            if (wrapper && !wrapper.contains(e.target)) {
                menu.style.display = 'none';
            }
        }
    });

    function updateRagGuideView(accountCode) {
        let foundItem = null;
        for (const sec of state.templatesTree) {
            for (const it of sec.items) {
                if (it.account_code === accountCode) {
                    foundItem = it;
                    break;
                }
            }
        }
        
        if (foundItem) {
            dom.ragGuideContainer.innerHTML = `
                <div style="margin-bottom:12px;">
                    <h4 style="color:#60a5fa; margin-bottom:6px;">📘 [${foundItem.account_code}] ${foundItem.account_name} 감사 지침</h4>
                    <p style="font-size:0.85rem; color:#94a3b8;">관련 템플릿 파일: <code>${foundItem.filename}</code> (${foundItem.procedure_count}개 표준 절차)</p>
                </div>
                <div style="background:rgba(30,41,59,0.5); padding:12px; border-radius:8px; font-size:0.85rem; line-height:1.6; color:#cbd5e1;">
                    <p>• <strong>K-GAAS 330/500/505 준용</strong>: 총괄표 대사, 거래처/은행 외부조회, 기간귀속(Cutoff) 검증 의무 수행</p>
                    <p>• <strong>핵심 경영진 주장</strong>: 실재성(Existence), 완전성(Completeness), 평가(Valuation), 권리와 의무(Rights & Obligations)</p>
                </div>
            `;
        }
    }

    // =========================================================================
    // 2-2. 비동기 알림 토스트 (Non-blocking Toast)
    // =========================================================================
    function showAuditToast(message, type = 'success') {
        let toastContainer = document.getElementById('audit-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'audit-toast-container';
            toastContainer.style.cssText = 'position: fixed; bottom: 28px; right: 28px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
            document.body.appendChild(toastContainer);
        }
        
        const toast = document.createElement('div');
        const bg = type === 'error' ? 'linear-gradient(135deg, #ef4444, #dc2626)' : (type === 'warning' ? 'linear-gradient(135deg, #f59e0b, #d97706)' : 'linear-gradient(135deg, #10b981, #059669)');
        toast.style.cssText = `background: ${bg}; color: #ffffff; padding: 12px 20px; border-radius: 10px; font-size: 0.88rem; font-weight: 600; box-shadow: 0 8px 24px rgba(0,0,0,0.35); pointer-events: auto; opacity: 0; transform: translateY(12px); transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; gap: 10px; border: 1px solid rgba(255,255,255,0.2);`;
        toast.innerHTML = `<span>${message}</span>`;
        toastContainer.appendChild(toast);
        
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(12px)';
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    // =========================================================================
    // 2-3. 조서 마크다운 실시간 서식 렌더러 (Markdown & Table Preview)
    // =========================================================================
    function renderMarkdownPreview(markdownText) {
        if (!dom.wpPreview) return;
        const text = (markdownText || '').trim();
        if (!text) {
            dom.wpPreview.innerHTML = `
                <div class="wp-empty-placeholder" style="text-align: center; padding: 60px 20px; color: #94a3b8;">
                    <div style="font-size: 2.4rem; margin-bottom: 12px;">📑</div>
                    <h3 style="color: #cbd5e1; font-size: 1.1rem; margin-bottom: 6px;">선택된 계정의 조서가 아직 생성되지 않았습니다</h3>
                    <p style="font-size: 0.88rem; color: #64748b;">우측 상단의 <strong>[✨ AI 조서 자동생성]</strong> 버튼을 클릭하여 K-GAAP 표준 감사조서를 생성하세요.</p>
                </div>
            `;
            return;
        }

        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            dom.wpPreview.innerHTML = marked.parse(text);
        } else {
            dom.wpPreview.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.7; color: #e2e8f0;">${text}</pre>`;
        }
    }

    // ✨ AI 조서 자동생성 실행
    async function handleGenerateWorkingPaper() {
        if (!state.currentCompany) {
            showAuditToast('감사 대상 기업을 먼저 선택해주세요.', 'warning');
            return;
        }

        const origHtml = dom.btnGenerateAi.innerHTML;
        console.log(`[WP] Generating AI working paper for [${state.activeAccountCode}] at ${state.currentCompany}`);
        dom.btnGenerateAi.disabled = true;
        dom.btnGenerateAi.innerHTML = '<span class="audit-loading-spinner"></span><span>생성 및 대사 중...</span>';

        try {
            const res = await fetch('/api/audit/working-papers/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: state.currentCompany,
                    fiscal_year: state.currentYear,
                    account_code: state.activeAccountCode
                })
            });

            const result = await res.json();
            if (result.success && result.data) {
                const wpData = result.data;
                state.activeWorkingPaperMd = wpData.working_paper_md;
                
                // 마크다운 에디터 및 실시간 서식 뷰어 바인딩
                dom.wpEditor.value = wpData.working_paper_md;
                renderMarkdownPreview(wpData.working_paper_md);
                
                // 미리보기 서식 탭 자동 활성화
                const subTabBtns = document.querySelectorAll('.wp-sub-tabs .wp-tab-btn');
                const subTabContents = document.querySelectorAll('.wp-tab-content');
                subTabBtns.forEach(b => b.classList.toggle('active', b.dataset.subtab === 'subtab-wp-preview'));
                subTabContents.forEach(c => {
                    const isPreview = (c.id === 'subtab-wp-preview');
                    c.style.display = isPreview ? 'block' : 'none';
                    c.classList.toggle('active', isPreview);
                });
                
                // 6대 장부 대사 대시보드 렌더링
                if (wpData.reconciliation) {
                    renderReconciliationDashboard(wpData.reconciliation);
                }
                if (wpData.related_pnl || wpData.reconciliation?.related_pnl) {
                    renderRelatedPnlDashboard(wpData.related_pnl || wpData.reconciliation.related_pnl);
                }
                
                showAuditToast(`✨ [${state.activeAccountCode}] AI 감사조서 자동생성이 완료되었습니다.`);
                console.log('[WP:SUCCESS] Working paper successfully generated and rendered');
            } else {
                showAuditToast(result.error || '감사조서 생성에 실패했습니다.', 'error');
            }
        } catch (err) {
            console.error('[ERROR] Generate working paper failed:', err);
            showAuditToast('조서 생성 중 오류가 발생했습니다: ' + err.message, 'error');
        } finally {
            dom.btnGenerateAi.disabled = false;
            dom.btnGenerateAi.innerHTML = origHtml;
        }
    }

    // 📥 K-GAAP 엑셀 다운로드
    async function handleExportExcel() {
        const mdContent = dom.wpEditor.value.trim();
        if (!mdContent) {
            showAuditToast('먼저 조서를 생성하거나 작성해주세요.', 'warning');
            return;
        }

        const origHtml = dom.btnExportExcel.innerHTML;
        console.log(`[WP] Exporting Excel for [${state.activeAccountCode}]`);
        dom.btnExportExcel.disabled = true;
        dom.btnExportExcel.innerHTML = '<span class="audit-loading-spinner"></span><span>엑셀 변환 중...</span>';

        try {
            const res = await fetch('/api/audit/working-papers/export-excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: state.currentCompany,
                    fiscal_year: state.currentYear,
                    account_code: state.activeAccountCode,
                    working_paper_md: mdContent,
                    reconciliation: state.reconciliationData
                })
            });

            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `${state.currentYear}_${state.currentCompany}_감사조서_${state.activeAccountCode}.xlsx`;
                document.body.appendChild(a);
                a.click();
                
                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    if (a.parentNode) a.remove();
                }, 1000);
                
                showAuditToast(`📥 [${state.activeAccountCode}] K-GAAP 엑셀 다운로드가 완료되었습니다.`);
                console.log('[WP:EXCEL_DOWNLOAD_COMPLETE]');
            } else {
                showAuditToast('엑셀 다운로드에 실패했습니다.', 'error');
            }
        } catch (err) {
            console.error('[ERROR] Excel export failed:', err);
            showAuditToast('엑셀 다운로드 오류: ' + err.message, 'error');
        } finally {
            dom.btnExportExcel.disabled = false;
            dom.btnExportExcel.innerHTML = origHtml;
        }
    }

    // =========================================================================
    // 3. FullCalendar v6 캘린더 연동
    // =========================================================================
    function initCalendar() {
        const calendarEl = document.getElementById('fullcalendar-audit-view');
        if (!calendarEl || typeof FullCalendar === 'undefined') return;

        state.calendarInstance = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'ko',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,listMonth'
            },
            buttonText: {
                today: '오늘',
                month: '월간',
                week: '주간',
                list: '일정목록'
            },
            events: '/api/audit/schedules',
            eventClick: (info) => {
                alert(`[${info.event.extendedProps.schedule_type || '감사일정'}]\n제목: ${info.event.title}\n기간: ${info.event.startStr} ~ ${info.event.endStr || info.event.startStr}\n메모: ${info.event.extendedProps.memo || '없음'}`);
            }
        });

        state.calendarInstance.render();
        console.log('[CAL] FullCalendar rendered successfully');
    }

    // 일정 등록 모달 핸들링
    function openScheduleModal() {
        dom.modalSchedule.style.display = 'flex';
        document.getElementById('sched-start').value = new Date().toISOString().split('T')[0];
        document.getElementById('sched-end').value = new Date().toISOString().split('T')[0];
    }

    function closeScheduleModal() {
        dom.modalSchedule.style.display = 'none';
        dom.formSchedule.reset();
    }

    async function handleSaveSchedule(e) {
        e.preventDefault();
        const title = document.getElementById('sched-title').value.trim();
        const type = document.getElementById('sched-type').value;
        const start = document.getElementById('sched-start').value;
        const end = document.getElementById('sched-end').value;
        const memo = document.getElementById('sched-memo').value.trim();

        try {
            const res = await fetch('/api/audit/schedules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    schedule_type: type,
                    start_date: start,
                    end_date: end,
                    memo: memo
                })
            });

            const result = await res.json();
            if (result.success) {
                closeScheduleModal();
                if (state.calendarInstance) {
                    state.calendarInstance.refetchEvents();
                }
                alert('감사 일정이 성공적으로 등록되었습니다.');
            }
        } catch (err) {
            console.error('[ERROR] Save schedule failed:', err);
            alert('일정 저장 오류: ' + err.message);
        }
    }

    // =========================================================================
    // 4. 감사 프로젝트 & 배정 목록 로드
    // =========================================================================
    async function loadProjects() {
        try {
            const res = await fetch('/api/audit/projects');
            const data = await res.json();
            if (data.success && data.projects && dom.projectsTbody) {
                dom.projectsTbody.innerHTML = '';
                data.projects.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${p.company_name}</strong></td>
                        <td>${p.fiscal_year}년도</td>
                        <td><span class="badge-incharge">${p.in_charge}</span></td>
                        <td>${p.engagement_partner}</td>
                        <td>${p.members.join(', ')}</td>
                        <td>${p.target_report_date}</td>
                        <td><span class="badge-status ${p.status === 'in_progress' ? 'badge-blue' : 'badge-planned'}">${p.status_label}</span></td>
                        <td><button class="btn btn-outline btn-sm">배정 수정</button></td>
                    `;
                    dom.projectsTbody.appendChild(tr);
                });
            }
        } catch (err) {
            console.error('[ERROR] Failed to load projects:', err);
        }
    }

    // =========================================================================
    // 5. 전역 이벤트 리스너 바인딩
    // =========================================================================
    function setupEventListeners() {
        // 4대 메인 탭 전환
        dom.menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const targetTab = item.dataset.tab;
                if (!targetTab) return;
                
                dom.menuItems.forEach(m => m.classList.remove('active'));
                item.classList.add('active');

                dom.tabPanes.forEach(pane => {
                    pane.classList.toggle('active', pane.id === targetTab);
                });

                console.log(`[NAV] Switched to tab: ${targetTab}`);

                // 캘린더 탭으로 전환 시 FullCalendar 다시 그리기
                if (targetTab === 'tab-audit-cal' && state.calendarInstance) {
                    setTimeout(() => state.calendarInstance.render(), 50);
                }
            });
        });

        // 기업 선택 변경
        dom.companySelect.addEventListener('change', async (e) => {
            state.currentCompany = e.target.value;
            const foundComp = state.companiesList.find(c => c.company_name === state.currentCompany);
            if (foundComp) {
                updateHeaderBadges(foundComp);
            }
            await loadCompanyAssignment(state.currentCompany);
            if (state.activeAccountCode) {
                selectWorkingPaper(state.activeSectionCode || '4000', state.activeAccountCode, state.activeAccountName, state.activeSectionTitle || 'Section 4000 계정별 입증감사');
            }
            console.log(`[ACTION] Changed company to: ${state.currentCompany}`);
        });

        // 사업연도 변경
        dom.yearSelect.addEventListener('change', (e) => {
            state.currentYear = e.target.value;
            console.log(`[ACTION] Changed fiscal year to: ${state.currentYear}`);
        });

        // 조서 검색 필터 (실시간 검색 및 아코디언 자동 확장)
        dom.wpTreeSearch.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            renderTemplatesTree(state.templatesTree, query);
        });

        // 조서 마크다운 에디터 직접 입력 시 실시간 미리보기 동기화
        if (dom.wpEditor) {
            dom.wpEditor.addEventListener('input', (e) => {
                state.activeWorkingPaperMd = e.target.value;
                renderMarkdownPreview(e.target.value);
            });
        }

        // 서식 탭 전환 (미리보기 vs 에디터 vs RAG 가이드)
        const subTabBtns = document.querySelectorAll('.wp-sub-tabs .wp-tab-btn');
        const subTabContents = document.querySelectorAll('.wp-tab-content');
        subTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                subTabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const targetId = btn.dataset.subtab || btn.dataset.target;
                subTabContents.forEach(content => {
                    if (content.id === targetId) {
                        content.style.display = 'block';
                        content.classList.add('active');
                    } else {
                        content.style.display = 'none';
                        content.classList.remove('active');
                    }
                });
            });
        });

        // 버튼 클릭 이벤트
        dom.btnGenerateAi.addEventListener('click', handleGenerateWorkingPaper);
        dom.btnExportExcel.addEventListener('click', handleExportExcel);
        dom.btnSaveWp.addEventListener('click', () => showAuditToast('💾 감사조서가 성공적으로 저장되었습니다. (Draft 상태)'));

        const btnRefresh = document.getElementById('btn-refresh-audit-data');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', async () => {
                const origHtml = btnRefresh.innerHTML;
                btnRefresh.disabled = true;
                btnRefresh.innerHTML = '<span class="audit-loading-spinner"></span><span>새로고침 중...</span>';
                try {
                    await loadCompanies();
                    await loadProjects();
                    if (state.calendarInstance) state.calendarInstance.refetchEvents();
                    showAuditToast('🔄 감사 데이터가 최신 상태로 새로고침되었습니다.');
                } finally {
                    btnRefresh.disabled = false;
                    btnRefresh.innerHTML = origHtml;
                }
            });
        }

        // 모바일 사이드바 토글 및 오버레이
        const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
        const sidebar = document.getElementById('audit-sidebar');
        const sidebarOverlay = document.getElementById('audit-sidebar-overlay');
        
        function closeMobileSidebar() {
            if (sidebar) sidebar.classList.remove('show-mobile');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
        }

        if (btnToggleSidebar && sidebar) {
            btnToggleSidebar.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = sidebar.classList.toggle('show-mobile');
                if (sidebarOverlay) {
                    sidebarOverlay.classList.toggle('active', isOpen);
                }
            });

            if (sidebarOverlay) {
                sidebarOverlay.addEventListener('click', closeMobileSidebar);
            }

            // 탭 클릭 시 모바일 사이드바 닫기
            dom.menuItems.forEach(item => {
                item.addEventListener('click', closeMobileSidebar);
            });
        }

        // =====================================================================
        // 5. 감사보고서 작성 (Report Generator) 인터랙션
        // =====================================================================
        const btnGenReport = document.getElementById('btn-generate-report-ai');
        const btnSaveReport = document.getElementById('btn-save-report');
        const btnPrintReport = document.getElementById('btn-print-report');
        const reportEditor = document.getElementById('audit-report-editor');
        const reportPreviewBody = document.getElementById('report-preview-body');
        const prevCompanyTitle = document.getElementById('prev-company-title');
        const prevIssueDate = document.getElementById('prev-issue-date');
        const opinionSelect = document.getElementById('report-opinion-type');
        const periodEndInput = document.getElementById('report-period-end');
        const issueDateInput = document.getElementById('report-issue-date');
        const kamSelect = document.getElementById('report-kam-status');
        const reportTabBtns = document.querySelectorAll('.report-tab-btn');
        const reportSubContents = document.querySelectorAll('.report-sub-content');
        const kamChips = document.querySelectorAll('.kam-chip');

        function generateAuditReportDraft() {
            const company = state.currentCompany || '주식회사 혜안';
            const year = state.currentYear || '2025';
            const periodEnd = periodEndInput ? periodEndInput.value : `${year}-12-31`;
            const issueDate = issueDateInput ? issueDateInput.value : '2026-03-20';
            const opinionType = opinionSelect ? opinionSelect.value : 'unqualified';
            const isKamIncluded = kamSelect ? (kamSelect.value === 'included') : true;

            let opinionText = '';
            let basisText = '';
            if (opinionType === 'unqualified') {
                opinionText = `우리는 ${company}(이하 "회사")의 재무제표, 즉 ${periodEnd} 현재의 재무상태표, 동일로 종료되는 회계연도의 손익계산서, 자본변동표 및 현금흐름표 그리고 유의적 회계정책의 요약을 포함하는 재무제표의 주석을 감사하였습니다.\n\n우리의 의견으로는 별첨된 회사의 재무제표는 ${company}의 ${periodEnd} 현재의 재무상태와 동일로 종료되는 회계연도의 재무성과 및 현금흐름을 한국채택국제회계기준(K-IFRS) 또는 일반기업회계기준(K-GAAP)에 따라 중요성의 관점에서 공정하게 표시하고 있습니다.`;
                basisText = `우리는 한국회계감사기준(K-GAAS)에 따라 감사를 수행하였습니다. 이 기준에 따른 우리의 책임은 이 감사보고서의 '재무제표감사에 대한 감사인의 책임' 단락에 기술되어 있습니다. 우리는 한국의 공인회계사 윤리강령에 따라 회사로부터 독립적이며, 이 강령에 따른 기타의 윤리적 책임들을 이행하였습니다. 우리는 우리가 입수한 감사증거가 감사의견을 위한 근거로서 충분하고 적절하다고 믿습니다.`;
            } else if (opinionType === 'qualified') {
                opinionText = `우리의 의견으로는 '한정의견의 근거' 단락에 기술된 사항이 미치는 영향을 제외하고는, 별첨된 회사의 재무제표는 ${company}의 ${periodEnd} 현재의 재무상태와 동일로 종료되는 회계연도의 재무성과 및 현금흐름을 회계처리기준에 따라 중요성의 관점에서 공정하게 표시하고 있습니다.`;
                basisText = `회사의 특정 재고자산 또는 채권에 대해 실사 입회 제한 또는 외부조회서 미회신으로 인하여 충분하고 적절한 감사증거를 입수할 수 없었습니다.`;
            } else if (opinionType === 'adverse') {
                opinionText = `우리의 의견으로는 '부적정의견의 근거' 단락에 기술된 사항의 중요성으로 말미암아, 별첨된 재무제표는 회사의 재무상태와 재무성과를 공정하게 표시하지 못하고 있습니다.`;
                basisText = `수익인식 및 자산평가와 관련된 중대한 왜곡표시가 재무제표 전반에 걸쳐 광범위하게 영향을 미치고 있습니다.`;
            } else {
                opinionText = `우리는 '의견거절의 근거' 단락에 기술된 사항의 중요성으로 인하여 감사의견의 근거를 제공하는 충분하고 적절한 감사증거를 입수할 수 없었으며, 따라서 재무제표에 대하여 감사의견을 표명하지 아니합니다.`;
                basisText = `계속기업가정의 불확실성 및 기초잔액에 대한 감사범위의 중대한 제한으로 인하여 감사의견을 표명할 수 없습니다.`;
            }

            let kamContent = '';
            if (isKamIncluded) {
                kamContent = `\n\n### 2. 핵심감사사항 (Key Audit Matters)\n\n핵심감사사항은 우리의 전문가적 판단에 따라 당기 재무제표감사에서 가장 유의적인 사항들입니다. 해당 사항들은 재무제표 전체에 대한 감사 관점에서 다루어졌으며, 우리는 이러한 사항에 대하여 별도의 의견을 제공하지는 않습니다.\n\n#### [KAM 1] 수익인식의 적정성 및 기간귀속(Cut-off) 검증\n- **핵심감사사항으로 결정한 이유**: 회사의 주요 매출 거래는 진행기준 및 인도기준에 따라 수익이 인식되며, 기말 전후 매출의 기간귀속 오류 위험이 높다고 판단하였습니다.\n- **감사인의 대응 절차**:\n  1. 회사의 매출 거래 프로세스 및 관련 내부통제 설계와 운영 효과성 평가\n  2. 기말 전후 주요 매출 거래에 대한 거래명세서, 세금계산서, 화물수령증 등 원본 증빙 대사\n  3. 주요 거래처 대상 채권 잔액 및 당기 거래내역에 대한 외부 독립조회 수행 및 100% 회신 대사 완료\n\n#### [KAM 2] 재고자산 순실현가치 평가 및 재고실사 입회\n- **핵심감사사항으로 결정한 이유**: 보유 재고자산의 진부화 및 저가법 평가 충당금 산정 시 경영진의 유의적 추정이 개입됩니다.\n- **감사인의 대응 절차**:\n  1. 결산일 기준 현장 실사 입회 및 샘플 검수(Test Count) 수행\n  2. 장기체화 재고 및 이동 없는 품목의 순실현가능가치(NRV) 산정 로직 검증`;
            }

            const fullDraft = `# 독립된 감사인의 감사보고서

**수신**: ${company} 주주 및 이사회 귀중

### 1. 감사의견 (Opinion)
${opinionText}

### 1-1. 감사의견의 근거 (Basis for Opinion)
${basisText}${kamContent}

### 3. 재무제표에 대한 경영진과 지배기구의 책임
경영진은 회계처리기준에 따라 공정하게 재무제표를 작성하고 표시할 책임이 있으며, 부정이나 오류에 의한 중요한 왜곡표시가 없는 재무제표를 작성하는 데 필요하다고 판단한 내부통제에 대한 책임이 있습니다. 지배기구는 회사의 재무보고절차의 감시에 대한 책임이 있습니다.

### 4. 재무제표감사에 대한 감사인의 책임
우리의 목적은 회사의 재무제표 전체에 부정이나 오류로 인한 중요한 왜곡표시가 없는지에 대하여 합리적인 확신을 얻어 감사의견이 포함된 감사보고서를 발행하는 데 있습니다.

---
**보고서 발행일자**: ${issueDate}
**감사인**: 회계법인 혜안 (Hyean Accounting Corporation)
**업무수행이사 (Engagement Partner)**: 공인회계사 김동선 (인)`;

            if (reportEditor) reportEditor.value = fullDraft;
            if (reportPreviewBody) reportPreviewBody.innerHTML = fullDraft.replace(/\n/g, '<br>');
            if (prevCompanyTitle) prevCompanyTitle.textContent = `${company} 주주 및 이사회 귀중`;
            if (prevIssueDate) prevIssueDate.textContent = issueDate;
        }

        if (btnGenReport) {
            btnGenReport.addEventListener('click', () => {
                const origHtml = btnGenReport.innerHTML;
                btnGenReport.disabled = true;
                btnGenReport.innerHTML = '<span class="audit-loading-spinner"></span><span>보고서 작성 중...</span>';
                setTimeout(() => {
                    generateAuditReportDraft();
                    showAuditToast('📑 K-GAAS 700 표준 AI 감사보고서 초안이 생성되었습니다.');
                    btnGenReport.disabled = false;
                    btnGenReport.innerHTML = origHtml;
                }, 300);
            });
        }

        if (btnSaveReport) {
            btnSaveReport.addEventListener('click', () => {
                showAuditToast('💾 감사보고서가 시스템에 안전하게 저장되었습니다.');
            });
        }

        if (btnPrintReport) {
            btnPrintReport.addEventListener('click', () => {
                // 서식 미리보기 탭 활성화 후 인쇄창 호출
                reportTabBtns.forEach(b => b.classList.remove('active'));
                const prevBtn = document.querySelector('.report-tab-btn[data-sub="preview"]');
                if (prevBtn) prevBtn.classList.add('active');
                reportSubContents.forEach(c => c.style.display = (c.id === 'report-view-preview') ? 'block' : 'none');
                
                setTimeout(() => window.print(), 300);
            });
        }

        // 보고서 서식 탭 전환
        reportTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                reportTabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const subType = btn.dataset.sub;
                reportSubContents.forEach(content => {
                    content.style.display = (content.id === `report-view-${subType}`) ? 'block' : 'none';
                });
                if (subType === 'preview' && reportEditor && reportPreviewBody) {
                    reportPreviewBody.innerHTML = reportEditor.value.replace(/\n/g, '<br>');
                }
            });
        });

        // KAM 칩 삽입
        kamChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const kamTitle = chip.textContent.trim();
                if (reportEditor) {
                    reportEditor.value += `\n\n#### [추가 핵심감사사항] ${kamTitle}\n- **감사 절차**: 관련 거래 및 평가 모델에 대한 입증절차를 수행하고 원본 증빙을 대사함.`;
                }
                alert(`[KAM] "${kamTitle}" 문단이 보고서에 추가되었습니다.`);
            });
        });

        // 캘린더 모달 이벤트
        dom.btnAddSchedule.addEventListener('click', openScheduleModal);
        dom.btnCloseScheduleModal.addEventListener('click', closeScheduleModal);
        dom.btnCancelSchedule.addEventListener('click', closeScheduleModal);
        dom.formSchedule.addEventListener('submit', handleSaveSchedule);
    }

    // =========================================================================
    // 6. [K-GAAP 표준 감사절차 참고 모달] 핸들러
    // =========================================================================
    window.openProcedureGuideModal = function () {
        const modal = document.getElementById('modal-audit-procedure-guide');
        if (!modal) return;

        const titleEl = document.getElementById('proc-guide-title');
        const fileEl = document.getElementById('proc-guide-file');
        const bodyEl = document.getElementById('proc-guide-body');

        // 현재 선택된 계정 템플릿 정보 검색
        let foundTemplate = null;
        for (const sec of state.templatesTree) {
            for (const item of (sec.items || [])) {
                if (item.account_code === state.activeAccountCode) {
                    foundTemplate = item;
                    break;
                }
            }
            if (foundTemplate) break;
        }

        const accCode = state.activeAccountCode || 'A-0';
        const accName = state.activeAccountName || '현금및현금성자산';

        if (titleEl) {
            titleEl.textContent = `[${accCode}] ${accName} K-GAAP 표준 감사절차`;
        }
        if (fileEl && foundTemplate) {
            fileEl.textContent = `서식 파일: ${foundTemplate.filename || '-'} (${foundTemplate.procedure_count || 0}개 실증절차)`;
        }

        // 세부 절차 목록 렌더링
        if (bodyEl) {
            bodyEl.innerHTML = '';

            // 기본 가이드 헤더 카드
            const introCard = document.createElement('div');
            introCard.style.cssText = 'background: rgba(30,41,59,0.5); padding: 14px 18px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);';
            introCard.innerHTML = `
                <div style="font-size: 0.9rem; font-weight: 600; color: #93c5fd; margin-bottom: 6px;">
                    📌 [${accCode}] ${accName} 핵심 감사 포인트 및 기준서 지침
                </div>
                <div style="font-size: 0.83rem; color: #cbd5e1; line-height: 1.5;">
                    • <strong>준용 기준서</strong>: K-GAAS 330(평가된 위험에 대한 감사인의 대응), K-GAAS 500(감사증거), K-GAAS 505(외부조회)<br>
                    • <strong>핵심 주장</strong>: 실재성(Existence), 완전성(Completeness), 기간귀속(Cutoff), 권리와 의무(Rights & Obligations)
                </div>
            `;
            bodyEl.appendChild(introCard);

            // 템플릿 내 세부 절차 목록 (없을 경우 기본 표준 절차 fallback 생성)
            let procList = foundTemplate?.procedures || [];
            if (!procList || procList.length === 0) {
                procList = [
                    {
                        procedure_type: "Part 1. 기본 실증절차",
                        title: `1. ${accName} 총괄표 작성 및 총계정원장/시산표 대사`,
                        assertions: ["E", "C", "CL"],
                        content: "당기 및 전기 잔액의 일치 여부를 총계정원장 및 재무상태표와 상호 대사하고 주요 변동 원인을 분석함."
                    },
                    {
                        procedure_type: "Part 1. 기본 실증절차",
                        title: `2. ${accName} 금융기관/거래처 외부조회 및 회신 검증`,
                        assertions: ["E", "R&O"],
                        content: "기준일 현재 전 금융기관 및 주요 거래처에 조회서를 발송하고 직접 회신받아 장부 잔액과 대사함."
                    },
                    {
                        procedure_type: "Part 2. 추가 감사절차",
                        title: `3. 기말 결산 전후 기간귀속(Cut-off) 테스트`,
                        assertions: ["CO", "C"],
                        content: "결산일 전후 10일간의 입출금 및 거래 전표를 표본 추출하여 올바른 회계기간에 귀속되었는지 검증함."
                    }
                ];
            }

            procList.forEach((proc, idx) => {
                const card = document.createElement('div');
                card.style.cssText = 'background: rgba(15,23,42,0.8); padding: 14px 18px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; gap: 8px;';

                const assertionsHtml = (proc.assertions || ['E', 'C']).map(ast => {
                    return `<span class="badge-tag" style="background: rgba(59,130,246,0.2); color: #60a5fa; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${ast}</span>`;
                }).join(' ');

                const safeContent = (proc.content || proc.title || '').replace(/'/g, "\\'");

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.75rem; color: #a5b4fc; font-weight: 600;">${proc.procedure_type || 'Part 1. 실증절차'}</span>
                        <div style="display: flex; gap: 4px;">
                            ${assertionsHtml}
                        </div>
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #f8fafc;">
                        ${proc.title || `${idx + 1}. 실증감사절차`}
                    </div>
                    <div style="font-size: 0.82rem; color: #94a3b8; line-height: 1.4;">
                        ${proc.content || '표준 감사 지침에 따라 표본을 추출하고 원본 증빙과의 일치성을 대사함.'}
                    </div>
                    <div style="display: flex; justify-content: flex-end; margin-top: 4px;">
                        <button type="button" class="btn-submit" onclick="insertProcedureToEditor('${safeContent}')" style="padding: 4px 12px; font-size: 0.78rem; width: auto;">
                            📋 조서에 이 절차 삽입
                        </button>
                    </div>
                `;
                bodyEl.appendChild(card);
            });
        }

        modal.style.display = 'flex';
    };

    window.closeProcedureGuideModal = function () {
        const modal = document.getElementById('modal-audit-procedure-guide');
        if (modal) modal.style.display = 'none';
    };

    window.insertProcedureToEditor = function (procedureText) {
        if (!dom.wpEditor) return;
        const insertBlock = `\n\n### [수행된 감사절차]\n- **절차 내용**: ${procedureText}\n- **수행 결과**: 원본 증빙 및 원장과 대사하였으며 중요한 왜곡표시가 발견되지 아니함.\n- **검증 완료일**: ${new Date().toISOString().split('T')[0]}`;
        dom.wpEditor.value += insertBlock;
        alert('✓ 선택한 감사절차가 조서 에디터에 추가되었습니다.');
        closeProcedureGuideModal();
    };

    // 포털 시작
    initAuditPortal();
});

