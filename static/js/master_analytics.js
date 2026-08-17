// -*- coding: utf-8 -*-
/**
 * Master Enterprise Analytics Hub Front-end Module
 * 혜안 마스터 기업 정밀 재무분석 & 감사 리스크 허브 스크립트
 */

(function () {
    'use strict';

    // 전역 상태 객체
    let currentAnalyticsData = null;
    let selectedDirectFiles = [];

    // 유틸리티: 숫자 3자리 콤마 및 억/만원 포맷
    function formatCurrency(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) return '-';
        const num = Number(amount);
        const absNum = Math.abs(num);
        const sign = num < 0 ? '-' : '';

        if (absNum >= 100000000) {
            const eok = (absNum / 100000000).toFixed(1);
            return `${sign}${Number(eok).toLocaleString()}억원`;
        } else if (absNum >= 10000) {
            const man = Math.round(absNum / 10000);
            return `${sign}${man.toLocaleString()}만원`;
        }
        return `${sign}${Math.round(absNum).toLocaleString()}원`;
    }

    function formatNumber(val, decimals = 1, unit = '') {
        if (val === undefined || val === null || isNaN(val)) return '-';
        return `${Number(val).toFixed(decimals)}${unit}`;
    }

    function getRatioStatusBadge(status) {
        if (!status) return '';
        let color = '#94a3b8';
        let bg = 'rgba(148, 163, 184, 0.15)';
        if (status.includes('양호') || status.includes('우수') || status.includes('안전')) {
            color = '#34d399';
            bg = 'rgba(16, 185, 129, 0.15)';
        } else if (status.includes('보통') || status.includes('적정')) {
            color = '#38bdf8';
            bg = 'rgba(56, 189, 248, 0.15)';
        } else if (status.includes('주의')) {
            color = '#fbbf24';
            bg = 'rgba(245, 158, 11, 0.15)';
        } else if (status.includes('위험') || status.includes('취약') || status.includes('과다')) {
            color = '#f87171';
            bg = 'rgba(239, 68, 68, 0.15)';
        }
        return `<span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: ${bg}; color: ${color}; font-weight: 600;">${status}</span>`;
    }

    // 1. 모드 전환 (파트너사 선택 vs 직접 파일 업로드)
    window.switchAnalyticsMode = function (mode) {
        const tabCompany = document.getElementById('tab-mode-company');
        const tabDirect = document.getElementById('tab-mode-direct');
        const panelCompany = document.getElementById('panel-company-mode');
        const panelDirect = document.getElementById('panel-direct-mode');

        if (mode === 'company') {
            if (tabCompany) {
                tabCompany.classList.add('active');
                tabCompany.style.background = '#6366f1';
                tabCompany.style.color = '#ffffff';
            }
            if (tabDirect) {
                tabDirect.classList.remove('active');
                tabDirect.style.background = 'transparent';
                tabDirect.style.color = '#94a3b8';
            }
            if (panelCompany) panelCompany.style.display = 'block';
            if (panelDirect) panelDirect.style.display = 'none';
        } else {
            if (tabDirect) {
                tabDirect.classList.add('active');
                tabDirect.style.background = '#6366f1';
                tabDirect.style.color = '#ffffff';
            }
            if (tabCompany) {
                tabCompany.classList.remove('active');
                tabCompany.style.background = 'transparent';
                tabCompany.style.color = '#94a3b8';
            }
            if (panelCompany) panelCompany.style.display = 'none';
            if (panelDirect) panelDirect.style.display = 'block';
        }
    };
    // 전역 스코프에도 직접 할당 (HTML onclick 대비)
    window.switchAnalyticsMode = window.switchAnalyticsMode;


    // 2. 드롭존 파일 선택 칩 렌더링
    function renderSelectedFilesChips() {
        const container = document.getElementById('analytics-selected-files');
        if (!container) return;
        container.innerHTML = '';

        if (selectedDirectFiles.length === 0) {
            return;
        }

        selectedDirectFiles.forEach((file, index) => {
            const chip = document.createElement('div');
            chip.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); border-radius: 6px; font-size: 0.8rem; color: #c7d2fe;';
            chip.innerHTML = `
                <span>📄 ${file.name} (${Math.round(file.size / 1024)} KB)</span>
                <span class="btn-remove-file" data-index="${index}" style="cursor: pointer; font-weight: 700; color: #f87171; margin-left: 4px;">&times;</span>
            `;
            container.appendChild(chip);
        });

        // 삭제 이벤트
        container.querySelectorAll('.btn-remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.getAttribute('data-index'), 10);
                selectedDirectFiles.splice(idx, 1);
                renderSelectedFilesChips();
            });
        });
    }

    // 3. 파싱 데이터 수집 현황 및 무결성 검증 렌더링 (Phase 2 - 가로형 2행 매트릭스)
    function renderIngestionHealthBlock(health, bundle) {
        const healthContainer = document.getElementById('analytics-health-container');
        if (!healthContainer || !health) return;
        healthContainer.style.display = 'block';

        // 1. 무결성 점수 게이지
        const scoreEl = document.getElementById('health-integrity-score');
        const badgeEl = document.getElementById('health-integrity-badge');
        const score = health.integrity_score !== undefined ? health.integrity_score : 100;
        if (scoreEl) scoreEl.textContent = `${score}점`;
        if (badgeEl) {
            const color = score >= 90 ? '#34d399' : (score >= 70 ? '#fbbf24' : '#f87171');
            const bg = score >= 90 ? 'rgba(16,185,129,0.15)' : (score >= 70 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)');
            badgeEl.style.borderColor = color;
            badgeEl.style.background = bg;
            badgeEl.style.color = color;
        }

        const curYear = health.current_year || (document.getElementById('analytics-fiscal-year')?.value || '2025');
        const priorYear = health.prior_year || (Number(curYear) - 1);

        const curLabel = document.getElementById('health-cur-year-label');
        const priorLabel = document.getElementById('health-prior-year-label');
        if (curLabel) curLabel.textContent = `당기 (${curYear}년)`;
        if (priorLabel) priorLabel.textContent = `전기 (${priorYear}년)`;

        const curData = health.current || {
            balance_sheet: health.balance_sheet,
            income_statement: health.income_statement,
            trial_balance: health.trial_balance,
            journal_entries: health.journal_entries,
            subledger: health.subledger
        };

        const priorData = health.prior || {
            balance_sheet: { status: 'missing' },
            income_statement: { status: 'missing' },
            trial_balance: { status: 'missing' },
            journal_entries: { status: 'missing' },
            subledger: { status: 'missing' }
        };

        // 셀 렌더러 함수
        const renderCell = (cellId, dataType, dataObj) => {
            const cell = document.getElementById(cellId);
            if (!cell) return;

            if (!dataObj || dataObj.status === 'missing') {
                cell.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 4px;">
                        <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; background: rgba(100,116,139,0.2); color: #94a3b8; font-weight: 600;">⚪ 미수집</span>
                        <span style="font-size: 0.68rem; color: #64748b;">미등록</span>
                    </div>
                `;
            } else {
                const count = dataObj.count ? `${Number(dataObj.count).toLocaleString()}건` : '수집완료';
                const fn = dataObj.filename ? dataObj.filename : '';
                const isBal = dataObj.is_balanced;
                const balText = isBal ? '✓ 일치' : '⚠️ 차이';
                const badgeBg = isBal ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)';
                const badgeColor = isBal ? '#34d399' : '#fbbf24';

                cell.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 4px;">
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; font-weight: 700;">🟢 ${count}</span>
                            <span style="font-size: 0.68rem; color: ${isBal ? '#38bdf8' : '#fbbf24'};">${balText}</span>
                        </div>
                        <div style="font-size: 0.68rem; color: #94a3b8; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${fn}">
                            ${fn ? `📁 ${fn}` : '원장 파싱'}
                        </div>
                        <button type="button" class="btn-inspect-data" data-type="${dataType}" style="padding: 2px 8px; font-size: 0.68rem; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); border-radius: 4px; color: #a5b4fc; cursor: pointer; transition: all 0.2s;">
                            👁️ 미리보기
                        </button>
                    </div>
                `;
            }
        };

        // 1행: 당기 (2025년)
        renderCell('cell-cur-bs-content', 'balance_sheet', curData.balance_sheet);
        renderCell('cell-cur-is-content', 'income_statement', curData.income_statement);
        renderCell('cell-cur-tb-content', 'trial_balance', curData.trial_balance);
        renderCell('cell-cur-journal-content', 'journal_entries', curData.journal_entries);
        renderCell('cell-cur-subledger-content', 'subledger', curData.subledger);

        // 2행: 전기 (2024년)
        renderCell('cell-prior-bs-content', 'balance_sheet', priorData.balance_sheet);
        renderCell('cell-prior-is-content', 'income_statement', priorData.income_statement);
        renderCell('cell-prior-tb-content', 'trial_balance', priorData.trial_balance);
        renderCell('cell-prior-journal-content', 'journal_entries', priorData.journal_entries);
        renderCell('cell-prior-subledger-content', 'subledger', priorData.subledger);

        // 동적으로 생성된 미리보기 버튼에 클릭 이벤트 재바인딩
        healthContainer.querySelectorAll('.btn-inspect-data').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dtype = e.currentTarget.getAttribute('data-type');
                openDataInspector(dtype);
            });
        });
    }

    // 4. 분석 결과 렌더링 엔진
    function renderAnalyticsPayload(data) {
        currentAnalyticsData = data;
        const wrapper = document.getElementById('analytics-results-wrapper');
        if (!wrapper) return;

        // [Phase 2] 수집 현황 검증 블록 렌더링
        if (data.ingestion_health) {
            renderIngestionHealthBlock(data.ingestion_health, data.normalized_bundle);
        }

        // 메타 헤더
        const titleEl = document.getElementById('res-company-title');
        const badgeEl = document.getElementById('res-fiscal-badge');
        const chipsEl = document.getElementById('res-files-chips');

        if (titleEl) titleEl.textContent = data.company_name || '분석 대상 기업';
        if (badgeEl) {
            const fy = document.getElementById('analytics-fiscal-year')?.value || '2025';
            badgeEl.textContent = `${fy}년 결산 종합 분석`;
        }

        if (chipsEl) {
            chipsEl.innerHTML = '';
            (data.analyzed_files || []).forEach(fn => {
                const chip = document.createElement('span');
                chip.style.cssText = 'padding: 2px 8px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; font-size: 0.75rem; color: #cbd5e1;';
                chip.textContent = `✓ ${fn}`;
                chipsEl.appendChild(chip);
            });
        }

        // 4대 KPI 요약 카드
        const summary = data.summary || {};
        const setKpi = (valId, diffId, curVal, prevVal) => {
            const vEl = document.getElementById(valId);
            const dEl = document.getElementById(diffId);
            if (vEl) vEl.textContent = formatCurrency(curVal);
            if (dEl && prevVal !== undefined && prevVal !== null && prevVal !== 0) {
                const diff = (curVal || 0) - prevVal;
                const pct = ((diff / Math.abs(prevVal)) * 100).toFixed(1);
                const sign = diff >= 0 ? '+' : '';
                const color = diff >= 0 ? '#34d399' : '#f87171';
                dEl.innerHTML = `<span style="color: ${color}; font-weight: 600;">${sign}${pct}%</span> <span style="color: #64748b;">(전기 ${formatCurrency(prevVal)})</span>`;
            } else if (dEl) {
                dEl.textContent = '전기 데이터 없음';
            }
        };

        setKpi('kpi-assets-val', 'kpi-assets-diff', summary.assets, summary.assets_prev);
        setKpi('kpi-sales-val', 'kpi-sales-diff', summary.sales, summary.sales_prev);
        setKpi('kpi-op-income-val', 'kpi-op-income-diff', summary.operating_income, summary.operating_income_prev);
        setKpi('kpi-net-income-val', 'kpi-net-income-diff', summary.net_income, summary.net_income_prev);

        // 4대 재무비율 렌더링
        const ratios = data.ratios || {};
        const renderRatioCategory = (containerId, badgeId, categoryData) => {
            const cont = document.getElementById(containerId);
            const bEl = document.getElementById(badgeId);
            if (!cont || !categoryData) return;
            cont.innerHTML = '';

            let worstStatus = '양호';
            Object.entries(categoryData).forEach(([key, item]) => {
                if (!item || typeof item !== 'object') return;
                const row = document.createElement('div');
                row.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px dashed rgba(255,255,255,0.05);';
                row.innerHTML = `
                    <span style="color: #cbd5e1;">${item.label || key}</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 700; color: #fff;">${formatNumber(item.value, 1, item.unit || '%')}</span>
                        ${getRatioStatusBadge(item.status)}
                    </div>
                `;
                cont.appendChild(row);

                if (item.status && (item.status.includes('위험') || item.status.includes('취약'))) {
                    worstStatus = '위험';
                } else if (item.status && item.status.includes('주의') && worstStatus !== '위험') {
                    worstStatus = '주의';
                }
            });

            if (bEl) {
                bEl.innerHTML = getRatioStatusBadge(worstStatus);
            }
        };

        renderRatioCategory('ratio-list-stability', 'badge-stability', ratios.stability);
        renderRatioCategory('ratio-list-profitability', 'badge-profitability', ratios.profitability);
        renderRatioCategory('ratio-list-growth', 'badge-growth', ratios.growth);
        renderRatioCategory('ratio-list-activity', 'badge-activity', ratios.activity);

        // JET 이상치 테이블 렌더링
        const jet = data.jet_anomalies || {};
        const jetCountBadge = document.getElementById('jet-anomaly-count-badge');
        const jetRiskBadge = document.getElementById('jet-risk-score-badge');
        const jetTbody = document.getElementById('jet-anomalies-tbody');

        if (jetCountBadge) jetCountBadge.textContent = `${jet.anomaly_count || 0}건`;
        if (jetRiskBadge) {
            const score = jet.risk_score || 0;
            const level = score >= 50 ? '고위험' : (score >= 20 ? '주의' : '정상');
            const color = score >= 50 ? '#f87171' : (score >= 20 ? '#fbbf24' : '#34d399');
            const bg = score >= 50 ? 'rgba(239,68,68,0.2)' : (score >= 20 ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)');
            jetRiskBadge.style.background = bg;
            jetRiskBadge.style.color = color;
            jetRiskBadge.textContent = `위험도: ${level} (${score}점)`;
        }

        if (jetTbody) {
            jetTbody.innerHTML = '';
            const anomalies = jet.anomalies || [];
            if (anomalies.length === 0) {
                jetTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #34d399;">✓ 이상 징후 전표가 발견되지 않았습니다.</td></tr>';
            } else {
                anomalies.forEach(a => {
                    const tr = document.createElement('tr');
                    tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04);';
                    tr.innerHTML = `
                        <td style="padding: 8px 10px; color: #cbd5e1;">${a.date || '-'}</td>
                        <td style="padding: 8px 10px; font-weight: 600; color: #e2e8f0;">${a.account || '-'}</td>
                        <td style="padding: 8px 10px; text-align: right; color: #fca5a5; font-weight: 700;">${Math.round(a.amount || 0).toLocaleString()}</td>
                        <td style="padding: 8px 10px;"><span style="background: rgba(239,68,68,0.15); color: #f87171; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;">${a.rule || '이상치'}</span></td>
                        <td style="padding: 8px 10px; color: #94a3b8; font-size: 0.78rem;">${a.desc || a.reason || '-'}</td>
                    `;
                    jetTbody.appendChild(tr);
                });
            }
        }

        // 거래처원장 리스크 렌더링
        const subledger = data.subledger_risks || {};
        const top5Badge = document.getElementById('subledger-top5-badge');
        const flagsChips = document.getElementById('subledger-flags-chips');
        const overdueTbody = document.getElementById('subledger-overdue-tbody');

        if (top5Badge) {
            const top5Val = subledger.top5_concentration_pct || 0;
            top5Badge.textContent = `Top 5 매출처 집중도: ${top5Val.toFixed(1)}%`;
            if (top5Val >= 70) {
                top5Badge.style.background = 'rgba(239,68,68,0.2)';
                top5Badge.style.color = '#f87171';
            }
        }

        if (flagsChips) {
            flagsChips.innerHTML = '';
            (subledger.risk_flags || []).forEach(flag => {
                const chip = document.createElement('span');
                chip.style.cssText = 'padding: 3px 8px; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24; border-radius: 4px; font-size: 0.75rem; font-weight: 600;';
                chip.textContent = `⚠️ ${flag}`;
                flagsChips.appendChild(chip);
            });
        }

        if (overdueTbody) {
            overdueTbody.innerHTML = '';
            const overdueList = subledger.overdue_receivables || [];
            if (overdueList.length === 0) {
                overdueTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #34d399;">✓ 180일 이상 장기 미회수 부실 채권이 없습니다.</td></tr>';
            } else {
                overdueList.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04);';
                    tr.innerHTML = `
                        <td style="padding: 8px 10px; color: #f1f5f9; font-weight: 600;">${item.customer_name}</td>
                        <td style="padding: 8px 10px; text-align: right; color: #fbbf24; font-weight: 700;">${Math.round(item.amount || 0).toLocaleString()}원</td>
                        <td style="padding: 8px 10px; text-align: center; color: #f87171;">${item.days_overdue || '-'}일</td>
                        <td style="padding: 8px 10px;"><span style="background: rgba(239,68,68,0.2); color: #f87171; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;">${item.risk_level || '고위험'}</span></td>
                    `;
                    overdueTbody.appendChild(tr);
                });
            }
        }

        // 5대 분석 한계점 체크리스트 렌더링
        const checklistCont = document.getElementById('analytics-checklist-list');
        if (checklistCont) {
            checklistCont.innerHTML = '';
            const items = data.limitations_checklist || [];
            items.forEach((chk, i) => {
                const row = document.createElement('label');
                row.style.cssText = 'display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px; background: rgba(30,41,59,0.5); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; cursor: pointer; transition: all 0.2s;';
                row.innerHTML = `
                    <input type="checkbox" id="chk-limit-${i}" style="margin-top: 4px; accent-color: #6366f1; width: 16px; height: 16px;">
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                            <span style="font-weight: 700; color: #f1f5f9; font-size: 0.88rem;">${i + 1}. ${chk.category}</span>
                            <span style="font-size: 0.72rem; padding: 1px 6px; background: rgba(99,102,241,0.15); color: #818cf8; border-radius: 4px;">${chk.additional_evidence_needed || '추가 서류 필요'}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: #94a3b8;">${chk.limitation}</div>
                    </div>
                `;
                checklistCont.appendChild(row);
            });
        }

        // K-GAAP 마크다운 조서 본문 렌더링
        const mdBody = document.getElementById('analytics-report-md-body');
        if (mdBody) {
            const reportMd = data.report_md || '# 분석 보고서가 없습니다.';
            if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
                mdBody.innerHTML = marked.parse(reportMd);
            } else {
                mdBody.innerHTML = `<pre style="white-space: pre-wrap; font-family: monospace; color: #e2e8f0;">${reportMd}</pre>`;
            }
        }

        // 결과 래퍼 노출
        wrapper.style.display = 'block';
        wrapper.scrollIntoView({ behavior: 'smooth' });
    }

    // 4. 파트너사 원클릭 분석 실행
    async function handleCompanyAnalysis() {
        const select = document.getElementById('analytics-company-select');
        const companyName = select ? select.value.trim() : '';

        if (!companyName) {
            alert('분석할 파트너사를 선택해 주세요.');
            return;
        }

        const loading = document.getElementById('analytics-loading');
        const wrapper = document.getElementById('analytics-results-wrapper');
        const statusEl = document.getElementById('company-files-status');

        const fySelect = document.getElementById('analytics-fiscal-year');
        const fy = fySelect ? fySelect.value : '2025';

        if (loading) loading.style.display = 'block';
        if (wrapper) wrapper.style.display = 'none';
        if (statusEl) statusEl.textContent = `'${companyName}'의 ${fy}년도 회계 엑셀 자료를 취합하여 분석 중...`;

        try {
            const response = await fetch(`/master/api/analyze-company/${encodeURIComponent(companyName)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fiscal_year: fy })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || '분석 요청에 실패했습니다.');
            }

            if (statusEl) statusEl.textContent = `✓ '${companyName}' (${fy}년) 분석 완료 (${(result.analyzed_files || []).length}개 파일 처리됨)`;
            renderAnalyticsPayload(result);

        } catch (err) {
            console.error('[MASTER_ANALYTICS:FRONT_ERROR]', err);
            alert(`분석 오류: ${err.message}`);
            if (statusEl) statusEl.textContent = `오류: ${err.message}`;
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    // 5. 직접 업로드 엑셀 분석 실행
    async function handleDirectAnalysis() {
        if (selectedDirectFiles.length === 0) {
            alert('분석할 엑셀(.xlsx, .xls) 또는 CSV 파일을 최소 1개 이상 첨부해 주세요.');
            return;
        }

        const nameInput = document.getElementById('analytics-direct-company-name');
        const companyName = nameInput ? nameInput.value.trim() : '직접 분석 기업';
        const fySelect = document.getElementById('analytics-fiscal-year');
        const fy = fySelect ? fySelect.value : '2025';

        const loading = document.getElementById('analytics-loading');
        const wrapper = document.getElementById('analytics-results-wrapper');

        if (loading) loading.style.display = 'block';
        if (wrapper) wrapper.style.display = 'none';

        const formData = new FormData();
        formData.append('company_name', companyName);
        formData.append('fiscal_year', fy);
        selectedDirectFiles.forEach(f => {
            formData.append('files', f);
        });

        try {
            const response = await fetch('/master/api/analyze-direct', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || '직접 파일 분석에 실패했습니다.');
            }

            renderAnalyticsPayload(result);

        } catch (err) {
            console.error('[MASTER_ANALYTICS:DIRECT_ERROR]', err);
            alert(`직접 분석 오류: ${err.message}`);
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    // 6. 분석 결과 DB 영속화 저장
    async function handleSaveAnalysis() {
        if (!currentAnalyticsData) {
            alert('저장할 분석 결과가 없습니다.');
            return;
        }

        const btn = document.getElementById('btn-save-current-analysis');
        if (btn) btn.disabled = true;

        const fy = document.getElementById('analytics-fiscal-year')?.value || 2025;

        try {
            const response = await fetch('/master/api/save-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: currentAnalyticsData.company_name,
                    fiscal_year: parseInt(fy, 10),
                    analysis_data: currentAnalyticsData,
                    report_md: currentAnalyticsData.report_md
                })
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error || '저장에 실패했습니다.');

            alert(`✓ ${result.message || '분석 결과가 안전하게 저장되었습니다.'}`);
            // 저장 이력 목록 자동 갱신
            if (currentAnalyticsData.company_name) {
                fetchLocalArchiveHistory(currentAnalyticsData.company_name);
            }

        } catch (err) {
            console.error('[MASTER_ANALYTICS:SAVE_ERROR]', err);
            alert(`저장 실패: ${err.message}`);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // 7-1. 로컬 보관함 과거 분석 데이터셋 목록 조회 (Phase 3)
    async function fetchLocalArchiveHistory(companyName) {
        const sel = document.getElementById('select-local-archive-history');
        if (!sel || !companyName) return;

        try {
            const resp = await fetch(`/master/api/datasets/local-list/${encodeURIComponent(companyName)}`);
            const res = await resp.json();
            sel.innerHTML = '';

            if (res.success && res.datasets && res.datasets.length > 0) {
                res.datasets.forEach(ds => {
                    const opt = document.createElement('option');
                    opt.value = ds.filename;
                    opt.textContent = `[${ds.fiscal_year}년] ${ds.saved_at} 저장본 (${(ds.size_bytes / 1024).toFixed(1)} KB)`;
                    sel.appendChild(opt);
                });
            } else {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = '과거 분석 보관 이력 없음';
                sel.appendChild(opt);
            }
        } catch (err) {
            console.error('[MASTER_ANALYTICS:LOCAL_LIST_ERROR]', err);
        }
    }

    // 7-2. 로컬 보관함 데이터셋 0.01초 즉시 복원 (Phase 3)
    async function handleLoadLocalArchive() {
        const compSel = document.getElementById('analytics-company-select');
        const histSel = document.getElementById('select-local-archive-history');
        const companyName = compSel ? compSel.value : '';
        const filename = histSel ? histSel.value : '';

        if (!companyName || !filename) {
            alert('불러올 과거 분석 보관본을 선택해 주세요.');
            return;
        }

        const btn = document.getElementById('btn-load-local-archive');
        if (btn) btn.disabled = true;

        try {
            const url = `/master/api/datasets/local-load?company_name=${encodeURIComponent(companyName)}&filename=${encodeURIComponent(filename)}`;
            const resp = await fetch(url);
            const payload = await resp.json();

            if (!resp.ok) throw new Error(payload.error || '데이터 로드에 실패했습니다.');

            // 화면에 0.01초 즉시 복원
            renderAnalyticsPayload(payload);
            const wrapper = document.getElementById('analytics-results-wrapper');
            if (wrapper) {
                wrapper.style.display = 'block';
                wrapper.scrollIntoView({ behavior: 'smooth' });
            }
            alert(`✓ '${companyName}'의 ${filename} 분석 데이터가 0.01초 만에 완벽히 복원되었습니다.`);

        } catch (err) {
            console.error('[MASTER_ANALYTICS:LOCAL_LOAD_ERROR]', err);
            alert(`복원 실패: ${err.message}`);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // 7-3. 마크다운 복사 및 다운로드
    function handleCopyMarkdown() {
        if (!currentAnalyticsData || !currentAnalyticsData.report_md) {
            alert('복사할 마크다운 보고서가 없습니다.');
            return;
        }
        navigator.clipboard.writeText(currentAnalyticsData.report_md).then(() => {
            alert('✓ K-GAAP 감사 보고서 마크다운이 클립보드에 복사되었습니다.');
        }).catch(err => {
            alert('클립보드 복사 실패: ' + err);
        });
    }

    function handleDownloadMarkdown() {
        if (!currentAnalyticsData || !currentAnalyticsData.report_md) {
            alert('다운로드할 마크다운 보고서가 없습니다.');
            return;
        }
        const blob = new Blob([currentAnalyticsData.report_md], { type: 'text/markdown;charset=utf-8;' });
        const link = document.createElement('a');
        const fname = `${currentAnalyticsData.company_name}_기업분석보고서_${new Date().toISOString().slice(0, 10)}.md`;
        link.href = URL.createObjectURL(blob);
        link.download = fname;
        link.click();
    }

    // 8. 회계 원천 데이터 인스펙터 모달 로직 (Phase 2)
    let currentInspectorData = [];
    let currentInspectorTitle = '';

    function openDataInspector(dataType) {
        if (!currentAnalyticsData || !currentAnalyticsData.normalized_bundle) {
            alert('먼저 분석을 실행하여 데이터를 수집해 주세요.');
            return;
        }

        const bundle = currentAnalyticsData.normalized_bundle;
        const rawMap = bundle.raw_datasets || {};
        const titleMap = {
            'balance_sheet': '재무상태표 (Balance Sheet)',
            'income_statement': '손익계산서 (Income Statement)',
            'trial_balance': '합계잔액시산표 (Trial Balance)',
            'journal_entries': '분개장 전표 (Journal Entries - 샘플)',
            'subledger': '거래처원장 (Subledger - 샘플)'
        };

        const keyMap = {
            'balance_sheet': 'balance_sheet',
            'income_statement': 'income_statement',
            'trial_balance': 'trial_balance',
            'journal_entries': 'journal_entries_sample',
            'subledger': 'subledger_sample'
        };

        const records = rawMap[keyMap[dataType]] || [];
        currentInspectorData = records;
        currentInspectorTitle = titleMap[dataType] || dataType;

        const modal = document.getElementById('modal-data-inspector');
        const titleEl = document.getElementById('inspector-modal-title');
        const countEl = document.getElementById('inspector-modal-count');

        if (titleEl) titleEl.textContent = currentInspectorTitle;
        if (countEl) countEl.textContent = `${records.length.toLocaleString()}건`;

        // 테이블 렌더링
        renderInspectorTable(records, dataType);
        // JSON 렌더링
        const jsonEl = document.getElementById('inspector-json-content');
        if (jsonEl) jsonEl.textContent = JSON.stringify(records, null, 2);

        // 테이블 탭 활성화
        switchInspectorTab('table');

        if (modal) modal.style.display = 'flex';
    }

    function renderInspectorTable(records, dataType) {
        const thead = document.getElementById('inspector-table-thead');
        const tbody = document.getElementById('inspector-table-tbody');
        if (!thead || !tbody) return;

        thead.innerHTML = '';
        tbody.innerHTML = '';

        if (!records || records.length === 0) {
            tbody.innerHTML = '<tr><td style="text-align:center; padding:30px; color:#64748b;">수집된 데이터가 없습니다.</td></tr>';
            return;
        }

        const headers = Object.keys(records[0]);
        const trHead = document.createElement('tr');
        headers.forEach(h => {
            const th = document.createElement('th');
            th.style.cssText = 'padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);';
            th.textContent = h;
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        records.slice(0, 100).forEach(r => {
            const tr = document.createElement('tr');
            tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04);';
            headers.forEach(h => {
                const td = document.createElement('td');
                td.style.cssText = 'padding: 6px 12px; color: #cbd5e1;';
                const val = r[h];
                if (typeof val === 'number') {
                    td.style.textAlign = 'right';
                    td.style.fontWeight = '600';
                    td.textContent = Math.abs(val) > 1000 ? Math.round(val).toLocaleString() : val;
                } else {
                    td.textContent = val !== null && val !== undefined ? String(val) : '-';
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    function switchInspectorTab(mode) {
        const tableTab = document.getElementById('tab-inspect-table');
        const jsonTab = document.getElementById('tab-inspect-json');
        const tableCont = document.getElementById('inspector-table-container');
        const jsonCont = document.getElementById('inspector-json-container');

        if (mode === 'table') {
            if (tableTab) { tableTab.style.background = '#6366f1'; tableTab.style.color = '#fff'; }
            if (jsonTab) { jsonTab.style.background = 'rgba(255,255,255,0.08)'; jsonTab.style.color = '#cbd5e1'; }
            if (tableCont) tableCont.style.display = 'block';
            if (jsonCont) jsonCont.style.display = 'none';
        } else {
            if (jsonTab) { jsonTab.style.background = '#6366f1'; jsonTab.style.color = '#fff'; }
            if (tableTab) { tableTab.style.background = 'rgba(255,255,255,0.08)'; tableTab.style.color = '#cbd5e1'; }
            if (jsonCont) jsonCont.style.display = 'block';
            if (tableCont) tableCont.style.display = 'none';
        }
    }

    // 9. 초기화 바인딩 함수
    window.initAnalyticsHub = function () {
        console.log('[MASTER_ANALYTICS] Analytics Hub 초기화 완료');

        // 드롭존 바인딩
        const dropzone = document.getElementById('analytics-dropzone');
        const fileInput = document.getElementById('analytics-file-input');

        if (dropzone && fileInput) {
            dropzone.addEventListener('click', () => fileInput.click());

            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.style.borderColor = '#818cf8';
                dropzone.style.background = 'rgba(99,102,241,0.08)';
            });

            dropzone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                dropzone.style.borderColor = 'rgba(99,102,241,0.4)';
                dropzone.style.background = 'rgba(99,102,241,0.03)';
            });

            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.style.borderColor = 'rgba(99,102,241,0.4)';
                dropzone.style.background = 'rgba(99,102,241,0.03)';

                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    Array.from(e.dataTransfer.files).forEach(f => {
                        if (!selectedDirectFiles.some(existing => existing.name === f.name)) {
                            selectedDirectFiles.push(f);
                        }
                    });
                    renderSelectedFilesChips();
                }
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(f => {
                        if (!selectedDirectFiles.some(existing => existing.name === f.name)) {
                            selectedDirectFiles.push(f);
                        }
                    });
                    renderSelectedFilesChips();
                    fileInput.value = '';
                }
            });
        }

        // 탭 전환 버튼 바인딩
        document.getElementById('tab-mode-company')?.addEventListener('click', () => window.switchAnalyticsMode('company'));
        document.getElementById('tab-mode-direct')?.addEventListener('click', () => window.switchAnalyticsMode('direct'));

        // 실행 버튼 바인딩
        document.getElementById('btn-run-company-analysis')?.addEventListener('click', handleCompanyAnalysis);
        document.getElementById('btn-run-direct-analysis')?.addEventListener('click', handleDirectAnalysis);
        document.getElementById('btn-save-current-analysis')?.addEventListener('click', handleSaveAnalysis);
        document.getElementById('btn-copy-report-md')?.addEventListener('click', handleCopyMarkdown);
        document.getElementById('btn-download-report-md')?.addEventListener('click', handleDownloadMarkdown);

        // [Phase 3] 로컬 보관함 불러오기 버튼 및 기업 선택 시 이력 조회 바인딩
        document.getElementById('btn-load-local-archive')?.addEventListener('click', handleLoadLocalArchive);
        const compSelect = document.getElementById('analytics-company-select');
        if (compSelect) {
            compSelect.addEventListener('change', () => {
                fetchLocalArchiveHistory(compSelect.value);
            });
            if (compSelect.value) {
                fetchLocalArchiveHistory(compSelect.value);
            }
        }

        // 데이터 인스펙터 버튼 바인딩
        document.querySelectorAll('.btn-inspect-data').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dtype = e.currentTarget.getAttribute('data-type');
                openDataInspector(dtype);
            });
        });

        // 모달 닫기/탭/복사 바인딩
        document.getElementById('btn-close-inspector')?.addEventListener('click', () => {
            const modal = document.getElementById('modal-data-inspector');
            if (modal) modal.style.display = 'none';
        });

        document.getElementById('tab-inspect-table')?.addEventListener('click', () => switchInspectorTab('table'));
        document.getElementById('tab-inspect-json')?.addEventListener('click', () => switchInspectorTab('json'));

        document.getElementById('btn-copy-inspector-json')?.addEventListener('click', () => {
            const jsonText = JSON.stringify(currentInspectorData, null, 2);
            navigator.clipboard.writeText(jsonText).then(() => {
                alert(`✓ ${currentInspectorTitle} 원본 JSON이 클립보드에 복사되었습니다.`);
            });
        });
    };

    // DOM 로드 완료 시 바인딩
    document.addEventListener('DOMContentLoaded', () => {
        window.initAnalyticsHub();
    });

})();
