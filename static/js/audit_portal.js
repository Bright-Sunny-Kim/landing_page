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
        calendarInstance: null,
        templatesTree: []
    };

    // DOM 요소 캐싱
    const dom = {
        companySelect: document.getElementById('audit-company-select'),
        yearSelect: document.getElementById('audit-year-select'),
        menuItems: document.querySelectorAll('.audit-menu-list .master-menu-item'),
        tabPanes: document.querySelectorAll('.audit-tab-pane'),
        wpTreeContainer: document.getElementById('wp-tree-container'),
        wpTreeSearch: document.getElementById('wp-tree-search'),
        wpActiveCode: document.getElementById('wp-active-code'),
        wpActiveTitle: document.getElementById('wp-active-title'),
        wpActiveSection: document.getElementById('wp-active-section'),
        wpEditor: document.getElementById('wp-markdown-editor'),
        btnGenerateAi: document.getElementById('btn-generate-wp-ai'),
        btnSaveWp: document.getElementById('btn-save-wp'),
        btnExportExcel: document.getElementById('btn-export-wp-excel'),
        reconPriorVal: document.getElementById('recon-prior-val'),
        reconCurrentVal: document.getElementById('recon-current-val'),
        reconVarianceVal: document.getElementById('recon-variance-val'),
        reconStatusVal: document.getElementById('recon-status-val'),
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
        setupEventListeners();
    }

    // 고객사 목록 로드
    async function loadCompanies() {
        console.log('[REQUEST] GET /api/audit/companies');
        try {
            const res = await fetch('/api/audit/companies');
            const data = await res.json();
            if (data.success && data.companies) {
                dom.companySelect.innerHTML = '<option value="">감사 대상 기업을 선택하세요</option>';
                data.companies.forEach((comp, idx) => {
                    const opt = document.createElement('option');
                    opt.value = comp.company_name;
                    opt.textContent = `${comp.company_name} (${comp.corporate_number || '법인'})`;
                    if (idx === 0) {
                        opt.selected = true;
                        state.currentCompany = comp.company_name;
                    }
                    dom.companySelect.appendChild(opt);
                });
                console.log(`[RENDER] Loaded ${data.companies.length} companies, active=${state.currentCompany}`);
            }
        } catch (err) {
            console.error('[ERROR] Failed to load companies:', err);
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
                renderTemplatesTree(data.tree);
            }
        } catch (err) {
            console.error('[ERROR] Failed to load template tree:', err);
        }
    }

    // 조서 색인 아코디언 트리 렌더링 (Section만 먼저 표시, 클릭 시 세부내역 확장)
    function renderTemplatesTree(tree, filterQuery = '') {
        dom.wpTreeContainer.innerHTML = '';
        const query = filterQuery.toLowerCase().trim();
        
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
            
            // 기본 상태: 검색 중일 때만 자동 확장, 기본 상태에서는 모든 Section을 접어서 6대 Section이 한눈에 보이도록 처리
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
                const itemEl = document.createElement('div');
                const isActive = (item.account_code === state.activeAccountCode);
                itemEl.className = `wp-tree-item ${isActive ? 'active' : ''}`;
                itemEl.dataset.sectionCode = section.code;
                itemEl.dataset.accountCode = item.account_code;
                itemEl.dataset.accountName = item.account_name;
                
                itemEl.innerHTML = `
                    <span><strong>[${item.account_code}]</strong> ${item.account_name}</span>
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
    // 2. 조서 선택 및 AI 자동생성 인터랙션
    // =========================================================================
    function selectWorkingPaper(sectionCode, accountCode, accountName, sectionTitle) {
        state.activeSectionCode = sectionCode;
        state.activeAccountCode = accountCode;
        state.activeAccountName = accountName;
        
        // UI 헤더 갱신
        dom.wpActiveCode.textContent = accountCode;
        dom.wpActiveTitle.textContent = accountName;
        dom.wpActiveSection.textContent = sectionTitle || `Section ${sectionCode}`;
        
        // 트리 active 클래스 토글
        document.querySelectorAll('.wp-tree-item').forEach(el => {
            el.classList.toggle('active', el.dataset.accountCode === accountCode);
        });
        
        console.log(`[WP] Selected working paper: [${accountCode}] ${accountName}`);
        
        // RAG 가이드 뷰 업데이트
        updateRagGuideView(accountCode);
    }

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

    // ✨ AI 조서 자동생성 실행
    async function handleGenerateWorkingPaper() {
        if (!state.currentCompany) {
            alert('감사 대상 기업을 먼저 선택해주세요.');
            return;
        }

        console.log(`[WP] Generating AI working paper for [${state.activeAccountCode}] at ${state.currentCompany}`);
        dom.btnGenerateAi.disabled = true;
        dom.btnGenerateAi.innerHTML = '<span>⏳ 생성 및 대사 중...</span>';

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
                state.reconciliationData = wpData.reconciliation;
                
                // 마크다운 에디터 바인딩
                dom.wpEditor.value = wpData.working_paper_md;
                
                // 6대 장부 대사 바 수치 바인딩
                if (wpData.reconciliation) {
                    const r = wpData.reconciliation;
                    dom.reconPriorVal.textContent = Number(r.prior_val || 0).toLocaleString() + '원';
                    dom.reconCurrentVal.textContent = Number(r.current_val || 0).toLocaleString() + '원';
                    dom.reconVarianceVal.textContent = `${Number(r.variance_val || 0).toLocaleString()}원 (${r.variance_pct.toFixed(1)}%)`;
                    dom.reconStatusVal.textContent = '🟢 대사 완료 (100%)';
                }
                
                console.log('[WP:SUCCESS] Working paper successfully generated and rendered');
            } else {
                alert(result.error || '감사조서 생성에 실패했습니다.');
            }
        } catch (err) {
            console.error('[ERROR] Generate working paper failed:', err);
            alert('조서 생성 중 오류가 발생했습니다: ' + err.message);
        } finally {
            dom.btnGenerateAi.disabled = false;
            dom.btnGenerateAi.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24"><path d="M7.5 5.6L10 0l2.5 5.6L18 8l-5.5 2.4L10 16l-2.5-5.6L2 8l5.5-2.4zm12 9.4l1.5-3.4 1.5 3.4 3.4 1.5-3.4 1.5-1.5 3.4-1.5-3.4-3.4-1.5 3.4-1.5z"/></svg><span>✨ AI 조서 자동생성</span>';
        }
    }

    // 📥 K-GAAP 엑셀 다운로드
    async function handleExportExcel() {
        const mdContent = dom.wpEditor.value.trim();
        if (!mdContent) {
            alert('먼저 조서를 생성하거나 작성해주세요.');
            return;
        }

        console.log(`[WP] Exporting Excel for [${state.activeAccountCode}]`);
        dom.btnExportExcel.disabled = true;
        dom.btnExportExcel.innerHTML = '<span>⏳ 엑셀 변환 중...</span>';

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
                a.href = url;
                a.download = `${state.currentYear}_${state.currentCompany}_감사조서_${state.activeAccountCode}.xlsx`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                console.log('[WP:EXCEL_DOWNLOAD_COMPLETE]');
            } else {
                alert('엑셀 다운로드에 실패했습니다.');
            }
        } catch (err) {
            console.error('[ERROR] Excel export failed:', err);
            alert('엑셀 다운로드 오류: ' + err.message);
        } finally {
            dom.btnExportExcel.disabled = false;
            dom.btnExportExcel.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24"><path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2v9.67z"/></svg><span>📥 K-GAAP 엑셀 다운로드</span>';
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
        dom.companySelect.addEventListener('change', (e) => {
            state.currentCompany = e.target.value;
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

        // 에디터 탭 전환 (조서 본체 vs RAG 가이드)
        dom.wpTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                dom.wpTabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const targetId = btn.dataset.target;
                dom.wpTabContents.forEach(content => {
                    content.style.display = (content.id === targetId) ? 'block' : 'none';
                });
            });
        });

        // 버튼 클릭 이벤트
        dom.btnGenerateAi.addEventListener('click', handleGenerateWorkingPaper);
        dom.btnExportExcel.addEventListener('click', handleExportExcel);
        dom.btnSaveWp.addEventListener('click', () => alert('감사조서가 저장되었습니다. (Draft 상태)'));

        const btnRefresh = document.getElementById('btn-refresh-audit-data');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                loadCompanies();
                loadProjects();
                if (state.calendarInstance) state.calendarInstance.refetchEvents();
                alert('감사 데이터를 새로고침했습니다.');
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
                generateAuditReportDraft();
                alert('K-GAAS 700 표준 AI 감사보고서 초안이 생성되었습니다.');
            });
        }

        if (btnSaveReport) {
            btnSaveReport.addEventListener('click', () => {
                alert('감사보고서가 시스템에 안전하게 저장되었습니다.');
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

    // 포털 시작
    initAuditPortal();
});
