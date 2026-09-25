// -*- coding: utf-8 -*-
/**
 * Master Enterprise Analytics Hub Front-end Module
 * 혜안 마스터 기업 정밀 재무분석 & 감사 리스크 허브 스크립트
 */

(function () {
    'use strict';

    // 전역 상태 객체
    let currentAnalyticsData = null;
    window.selectedDirectFiles = window.selectedDirectFiles || [];

    // 전역 브라우저 파일 드롭 기본동작(파일 열기) 원천 차단
    window.addEventListener('dragover', (e) => e.preventDefault());
    window.addEventListener('drop', (e) => e.preventDefault());

    // 안전한 JSON fetch 파서 (HTML 500 에러 페이지 반환 시 SyntaxError 방지)
    async function safeFetchJson(url, options = {}, fallbackErrorMsg = '요청 처리에 실패했습니다.') {
        const response = await fetch(url, options);
        const contentType = response.headers.get('content-type') || '';
        
        let data = null;
        if (contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (e) {
                console.warn('[SAFE_FETCH] JSON 파싱 실패:', e);
            }
        } else {
            const rawText = await response.text();
            console.warn('[SAFE_FETCH] Non-JSON 응답 수신 (상태코드: ' + response.status + '):', rawText.slice(0, 200));
        }

        if (!response.ok) {
            const errMsg = (data && data.error) 
                ? data.error 
                : (response.status === 500 
                    ? '서버 내부 오류(500)가 발생했습니다. 서버 로그 또는 권한/용량 설정을 확인해 주세요.' 
                    : `${fallbackErrorMsg} (상태코드: ${response.status})`);
            throw new Error(errMsg);
        }

        if (!data) {
            throw new Error('서버로부터 올바른 JSON 응답을 수신하지 못했습니다.');
        }

        return data;
    }

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
    window.switchAnalyticsMode = window.switchAnalyticsMode;


    // 2. 드롭존 파일 선택 칩 렌더링
    window.renderSelectedFilesChips = function () {
        const container = document.getElementById('analytics-selected-files');
        const mainText = document.getElementById('analytics-dropzone-main-text');
        const subText = document.getElementById('analytics-dropzone-sub-text');
        const dropzone = document.getElementById('analytics-dropzone');
        if (!container) return;
        container.innerHTML = '';

        if (!window.selectedDirectFiles || window.selectedDirectFiles.length === 0) {
            if (dropzone) {
                dropzone.style.borderColor = 'rgba(99,102,241,0.6)';
                dropzone.style.background = 'rgba(99,102,241,0.05)';
            }
            if (mainText) mainText.textContent = '6대 회계자료 엑셀(.xlsx, .xls) 또는 CSV 파일을 여기에 끌어다 놓으세요';
            if (subText) subText.innerHTML = '또는 <span style="color: #818cf8; text-decoration: underline; font-weight: 700;">내 PC에서 파일 선택</span> (재무상태표, 손익계산서, 합잔, 분개장, 거래처원장, 계정별원장 다중 선택 가능)';
            return;
        }

        if (dropzone) {
            dropzone.style.borderColor = '#10b981';
            dropzone.style.background = 'rgba(16,185,129,0.08)';
        }
        if (mainText) mainText.innerHTML = `<span style="color: #34d399;">✓ 총 ${window.selectedDirectFiles.length}개의 회계 파일이 준비되었습니다.</span>`;
        if (subText) subText.innerHTML = '<span style="color: #cbd5e1;">추가 파일을 더 끌어다 놓거나 클릭하여 계속 추가할 수 있습니다.</span>';

        window.selectedDirectFiles.forEach((file, index) => {
            const chip = document.createElement('div');
            chip.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: rgba(99,102,241,0.25); border: 1px solid rgba(99,102,241,0.5); border-radius: 6px; font-size: 0.85rem; color: #c7d2fe; font-weight: 600;';
            chip.innerHTML = `
                <span>📄 ${file.name} (${Math.round(file.size / 1024)} KB)</span>
                <span class="btn-remove-file" data-index="${index}" style="cursor: pointer; font-weight: 700; color: #f87171; margin-left: 6px; padding: 0 4px; font-size: 1.1rem;" title="파일 제거">&times;</span>
            `;
            container.appendChild(chip);
        });

        // 삭제 이벤트
        container.querySelectorAll('.btn-remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const idx = parseInt(e.currentTarget.getAttribute('data-index'), 10);
                window.selectedDirectFiles.splice(idx, 1);
                window.renderSelectedFilesChips();
            });
        });
    };

    // 전역 파일 핸들러 (인라인 이벤트 지원)
    window.handleAnalyticsFileInputChange = function (input) {
        if (input && input.files && input.files.length > 0) {
            Array.from(input.files).forEach(f => {
                if (!window.selectedDirectFiles.some(existing => existing.name === f.name)) {
                    window.selectedDirectFiles.push(f);
                }
            });
            window.renderSelectedFilesChips();
            input.value = '';
        }
    };

    window.handleAnalyticsDragOver = function (e) {
        e.preventDefault();
        e.stopPropagation();
        const dropzone = document.getElementById('analytics-dropzone');
        if (dropzone) {
            dropzone.style.borderColor = '#818cf8';
            dropzone.style.background = 'rgba(99,102,241,0.15)';
        }
    };

    window.handleAnalyticsDragLeave = function (e) {
        e.preventDefault();
        e.stopPropagation();
        const dropzone = document.getElementById('analytics-dropzone');
        if (dropzone) {
            if (window.selectedDirectFiles && window.selectedDirectFiles.length > 0) {
                dropzone.style.borderColor = '#10b981';
                dropzone.style.background = 'rgba(16,185,129,0.08)';
            } else {
                dropzone.style.borderColor = 'rgba(99,102,241,0.6)';
                dropzone.style.background = 'rgba(99,102,241,0.05)';
            }
        }
    };

    window.handleAnalyticsDrop = function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            Array.from(e.dataTransfer.files).forEach(f => {
                if (!window.selectedDirectFiles.some(existing => existing.name === f.name)) {
                    window.selectedDirectFiles.push(f);
                }
            });
            window.renderSelectedFilesChips();
        }
    };

    // 3. 파싱 데이터 수집 현황 및 무결성 검증 렌더링 (Phase 2 - 가로형 2행 매트릭스)
    function renderIngestionHealthBlock(health, bundle) {
        const healthContainer = document.getElementById('analytics-health-container');
        if (!healthContainer || !health) return;

        // 전달받은 객체가 result 전체 페이로드인 경우 ingestion_health 추출
        if (health.ingestion_health) {
            bundle = health.normalized_bundle || bundle;
            health = health.ingestion_health;
        }

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
            subledger: health.subledger,
            account_ledger: health.account_ledger
        };

        const priorData = health.prior || {
            balance_sheet: { status: 'missing' },
            income_statement: { status: 'missing' },
            trial_balance: { status: 'missing' },
            journal_entries: { status: 'missing' },
            subledger: { status: 'missing' },
            account_ledger: { status: 'missing' }
        };

        // 셀 렌더러 함수
        const renderCell = (cellId, dataType, dataObj, targetFy) => {
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
                const count = dataObj.count ? (typeof dataObj.count === 'number' ? `${Number(dataObj.count).toLocaleString()}건` : dataObj.count) : '수집완료';
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
                        <button type="button" class="btn-inspect-data" data-type="${dataType}" data-fy="${targetFy}" style="padding: 2px 8px; font-size: 0.68rem; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); border-radius: 4px; color: #a5b4fc; cursor: pointer; transition: all 0.2s;">
                            👁️ 미리보기
                        </button>
                    </div>
                `;
            }
        };

        // 1행: 당기 (2025년)
        renderCell('cell-cur-bs-content', 'balance_sheet', curData.balance_sheet, curYear);
        renderCell('cell-cur-is-content', 'income_statement', curData.income_statement, curYear);
        renderCell('cell-cur-tb-content', 'trial_balance', curData.trial_balance, curYear);
        renderCell('cell-cur-journal-content', 'journal_entries', curData.journal_entries, curYear);
        renderCell('cell-cur-subledger-content', 'subledger', curData.subledger, curYear);
        renderCell('cell-cur-accountledger-content', 'account_ledger', curData.account_ledger, curYear);

        // 2행: 전기 (2024년)
        renderCell('cell-prior-bs-content', 'balance_sheet', priorData.balance_sheet, priorYear);
        renderCell('cell-prior-is-content', 'income_statement', priorData.income_statement, priorYear);
        renderCell('cell-prior-tb-content', 'trial_balance', priorData.trial_balance, priorYear);
        renderCell('cell-prior-journal-content', 'journal_entries', priorData.journal_entries, priorYear);
        renderCell('cell-prior-subledger-content', 'subledger', priorData.subledger, priorYear);
        renderCell('cell-prior-accountledger-content', 'account_ledger', priorData.account_ledger, priorYear);

        // 동적으로 생성된 미리보기 버튼에 클릭 이벤트 재바인딩
        healthContainer.querySelectorAll('.btn-inspect-data').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dtype = e.currentTarget.getAttribute('data-type');
                const dfy = e.currentTarget.getAttribute('data-fy') || curYear;
                openDataInspector(dtype, dfy);
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

    // 4. [저장본 기반 0.01초 정밀 분석 & AI 조서 산출] 실행
    async function handleStoredAnalysis(customCompany = null, customFy = null, customSessionId = null) {
        const compSelect = document.getElementById('analytics-company-select');
        const fySelect = document.getElementById('analytics-fiscal-year');
        const histSelect = document.getElementById('select-local-archive-history');
        const emptyNotice = document.getElementById('analytics-empty-notice');

        const companyName = customCompany || (compSelect ? compSelect.value.trim() : '');
        const fy = customFy || (fySelect ? fySelect.value : '2025');
        const sessionId = customSessionId || (histSelect ? histSelect.value : '');

        if (!companyName) {
            alert('분석을 진행할 기업을 선택해 주세요.');
            return;
        }

        const loading = document.getElementById('analytics-loading');
        const wrapper = document.getElementById('analytics-results-wrapper');

        if (loading) loading.style.display = 'block';
        if (wrapper) wrapper.style.display = 'none';
        if (emptyNotice) emptyNotice.style.display = 'none';

        try {
            console.log(`[MASTER_ANALYTICS:STORED] 분석 요청 시작: company=${companyName}, fy=${fy}, session=${sessionId || 'LATEST'}`);
            const result = await safeFetchJson(
                '/master/api/analyze-stored-dataset',
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_name: companyName,
                        fiscal_year: fy,
                        session_id: sessionId
                    })
                },
                '저장본 정밀 분석에 실패했습니다.'
            );

            renderAnalyticsPayload(result);

        } catch (err) {
            console.error('[MASTER_ANALYTICS:STORED_ERROR]', err);
            if (emptyNotice && err.message.includes('찾을 수 없습니다')) {
                emptyNotice.style.display = 'block';
            } else {
                alert(`정밀 분석 오류: ${err.message}`);
            }
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    // 5. [1단계 수집 & 스마트 파싱 & 우분투 서버 영구 저장] 실행
    window.handleIngestFiles = async function () {
        if (!window.selectedDirectFiles || window.selectedDirectFiles.length === 0) {
            alert('수집할 엑셀(.xlsx, .xls) 또는 CSV 파일을 최소 1개 이상 첨부해 주세요.');
            return;
        }

        const compSelect = document.getElementById('ingest-company-select');
        const nameInput = document.getElementById('analytics-direct-company-name');
        const companyName = (nameInput ? nameInput.value.trim() : '') || (compSelect ? compSelect.value.trim() : '');
        if (!companyName) {
            alert('수집 대상 기업명을 선택하거나 직접 입력해 주세요.');
            if (nameInput) nameInput.focus();
            return;
        }

        const fySelect = document.getElementById('ingest-fiscal-year');
        const fy = fySelect ? fySelect.value : '2025';

        const btn = document.getElementById('btn-run-ingest');
        const originBtnHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span>⏳ 자료 수집 & 우분투 서버 영구 저장 중...</span>';
        }

        const formData = new FormData();
        formData.append('company_name', companyName);
        formData.append('fiscal_year', fy);
        window.selectedDirectFiles.forEach(f => {
            formData.append('files', f);
        });

        try {
            console.log(`[MASTER_INGEST:SEND] 6대 회계자료 수집 요청: company=${companyName}, files=${window.selectedDirectFiles.length}`);
            const result = await safeFetchJson(
                '/master/api/ingest-files',
                {
                    method: 'POST',
                    body: formData
                },
                '회계자료 수집 처리에 실패했습니다.'
            );

            console.log('[MASTER_INGEST:RECV] 수집 완료 성공:', result);

            // 1. 6대 장부 수집 매트릭스 렌더링
            renderIngestionHealthBlock(result);

            // 2. 수집 완료 성공 배너 표시
            const successBanner = document.getElementById('ingest-success-banner');
            const descEl = document.getElementById('ingest-success-desc');
            if (descEl) {
                descEl.textContent = `'${companyName}' 기업의 6대 장부가 성공적으로 파싱되어 세션(${result.session_id})으로 보관되었습니다.`;
            }
            if (successBanner) {
                successBanner.style.display = 'flex';
                // 배너 내 즉시 분석 버튼 바인딩
                const gotoBtn = document.getElementById('btn-goto-analytics-from-ingest');
                if (gotoBtn) {
                    gotoBtn.onclick = () => {
                        // 1. 기업 정밀 분석 탭으로 전환
                        document.querySelector('.master-menu-item[data-menu="analytics-hub"]')?.click();
                        // 2. 파트너사 셀렉트에 기업명 설정
                        const compSel = document.getElementById('analytics-company-select');
                        if (compSel) {
                            let found = false;
                            for (let i = 0; i < compSel.options.length; i++) {
                                if (compSel.options[i].value === companyName) {
                                    compSel.selectedIndex = i;
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                const newOpt = document.createElement('option');
                                newOpt.value = companyName;
                                newOpt.textContent = companyName;
                                newOpt.selected = true;
                                compSel.appendChild(newOpt);
                            }
                        }
                        // 3. 0.01초 즉시 분석 실행
                        handleStoredAnalysis(companyName, fy, result.session_id);
                    };
                }
            }

            // 3. 실시간 업로드 이력 관리 센터 즉시 새로고침
            loadRealtimeUploadHistory(companyName);

            alert(`✓ [수집 완료] '${companyName}' 기업의 회계자료가 우분투 서버 영구 저장소에 안전하게 보관되었습니다!`);

        } catch (err) {
            console.error('[MASTER_INGEST:ERROR]', err);
            alert(`회계자료 수집 오류: ${err.message}`);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originBtnHtml;
            }
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
            const result = await safeFetchJson(
                '/master/api/save-analysis',
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_name: currentAnalyticsData.company_name,
                        fiscal_year: parseInt(fy, 10),
                        analysis_data: currentAnalyticsData,
                        report_md: currentAnalyticsData.report_md
                    })
                },
                '저장에 실패했습니다.'
            );

            alert(`✓ ${result.message || '분석 결과가 안전하게 저장되었습니다.'}`);
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
            const res = await safeFetchJson(
                `/master/api/datasets/local-list/${encodeURIComponent(companyName)}`,
                {},
                '로컬 데이터셋 목록 조회 실패'
            );
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
            const payload = await safeFetchJson(url, {}, '데이터 복원에 실패했습니다.');

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
    window.masterLakehouseStore = {}; // 연도별 원천 데이터 캐시

    function openDataInspector(dataType, targetFy) {
        const titleMap = {
            'balance_sheet': '재무상태표 (Balance Sheet)',
            'income_statement': '손익계산서 (Income Statement)',
            'trial_balance': '합계잔액시산표 (Trial Balance)',
            'journal_entries': '분개장 전표 (Journal Entries - 샘플)',
            'subledger': '거래처원장 (Subledger - 샘플)',
            'account_ledger': '계정별원장 (General Ledger - 7대 필드)'
        };

        const keyMap = {
            'balance_sheet': 'balance_sheet',
            'income_statement': 'income_statement',
            'trial_balance': 'trial_balance',
            'journal_entries': 'journal_entries',
            'subledger': 'subledger',
            'account_ledger': 'account_ledger'
        };

        const targetKey = keyMap[dataType] || dataType;
        let records = [];

        // 1. 연도별 lakehouse 캐시 우선 탐색
        if (targetFy && window.masterLakehouseStore && window.masterLakehouseStore[targetFy]) {
            const fyStore = window.masterLakehouseStore[targetFy];
            const st = fyStore.statements || {};
            if (st[targetKey] && Array.isArray(st[targetKey])) {
                records = st[targetKey];
            } else if (st[dataType] && Array.isArray(st[dataType])) {
                records = st[dataType];
            }
        }

        // 2. Fallback: currentAnalyticsData
        if ((!records || records.length === 0) && currentAnalyticsData) {
            const bundle = currentAnalyticsData.normalized_bundle || {};
            const rawMap = bundle.raw_datasets || {};
            records = (rawMap && (rawMap[targetKey] || rawMap[dataType])) || 
                      bundle[targetKey] || 
                      bundle[dataType] || 
                      [];
        }

        currentInspectorData = records;
        const fyLabel = targetFy ? ` [${targetFy}년]` : '';
        currentInspectorTitle = `${titleMap[dataType] || dataType}${fyLabel}`;

        const modal = document.getElementById('modal-data-inspector');
        const titleEl = document.getElementById('inspector-modal-title');
        const countEl = document.getElementById('inspector-modal-count');

        if (titleEl) titleEl.textContent = currentInspectorTitle;
        if (countEl) countEl.textContent = `${(records || []).length.toLocaleString()}건`;

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
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px; color:#94a3b8; font-size: 0.9rem;">수집된 데이터가 없거나 미등록 상태입니다.</td></tr>';
            return;
        }

        // 1. 합계잔액시산표 (Trial Balance) 특화 렌더러
        if (dataType === 'trial_balance') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 14px; text-align: right; color: #38bdf8; font-weight: 700; width: 16%;">차변 잔액</th>
                    <th style="padding: 10px 14px; text-align: right; color: #94a3b8; font-weight: 600; width: 16%;">차변 합계</th>
                    <th style="padding: 10px 16px; text-align: center; color: #f8fafc; font-weight: 700; width: 36%;">계정과목</th>
                    <th style="padding: 10px 14px; text-align: right; color: #94a3b8; font-weight: 600; width: 16%;">대변 합계</th>
                    <th style="padding: 10px 14px; text-align: right; color: #38bdf8; font-weight: 700; width: 16%;">대변 잔액</th>
                </tr>
            `;

            records.forEach(r => {
                const tr = document.createElement('tr');
                const isSub = r.IsSubtotal || r.RowKind === 'subtotal' || r.RowKind === 'group';
                const isTotal = r.RowKind === 'total' || String(r.Account).includes('합계') || String(r.Account).includes('◀');
                
                let rowBg = 'transparent';
                let fontWeight = '400';
                let textColor = '#e2e8f0';

                if (isTotal) {
                    rowBg = 'rgba(99,102,241,0.18)';
                    fontWeight = '700';
                    textColor = '#a5b4fc';
                } else if (isSub) {
                    rowBg = 'rgba(255,255,255,0.04)';
                    fontWeight = '600';
                    textColor = '#f8fafc';
                }

                tr.style.cssText = `background: ${rowBg}; border-bottom: 1px solid rgba(255,255,255,0.05); font-weight: ${fontWeight};`;

                const fmt = (v) => {
                    if (v === null || v === undefined || isNaN(v)) return '-';
                    if (v === 0) return '0';
                    return Math.round(v).toLocaleString();
                };

                const debitBal = r.DebitBalance !== undefined ? r.DebitBalance : (r.NetBalance > 0 ? r.NetBalance : null);
                const creditBal = r.CreditBalance !== undefined ? r.CreditBalance : (r.NetBalance < 0 ? Math.abs(r.NetBalance) : null);

                tr.innerHTML = `
                    <td style="padding: 7px 14px; text-align: right; color: ${debitBal ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(debitBal)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #94a3b8; font-family: monospace; font-size: 0.85rem;">${fmt(r.DebitTurnover)}</td>
                    <td style="padding: 7px 16px; text-align: left; color: ${textColor};">${r.RawAccount || r.Account || '-'}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #94a3b8; font-family: monospace; font-size: 0.85rem;">${fmt(r.CreditTurnover)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: ${creditBal ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(creditBal)}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 2. 재무상태표 (Balance Sheet) 특화 렌더러
        if (dataType === 'balance_sheet') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 16px; text-align: left; color: #f8fafc; font-weight: 700; width: 40%;">계정과목</th>
                    <th style="padding: 10px 14px; text-align: right; color: #94a3b8; font-weight: 600; width: 15%;">당기 총액(원천)</th>
                    <th style="padding: 10px 14px; text-align: right; color: #34d399; font-weight: 700; width: 15%;">당기 순액(표시)</th>
                    <th style="padding: 10px 14px; text-align: right; color: #94a3b8; font-weight: 600; width: 15%;">전기 총액(원천)</th>
                    <th style="padding: 10px 14px; text-align: right; color: #a5b4fc; font-weight: 700; width: 15%;">전기 순액(표시)</th>
                </tr>
            `;

            records.forEach(r => {
                const tr = document.createElement('tr');
                const isGroup = r.RowKind === 'group' || r.RowKind === 'total';
                const isSub = r.RowKind === 'subtotal';
                const isContra = r.IsContra;

                let rowBg = 'transparent';
                let fontWeight = '400';
                let textColor = '#e2e8f0';

                if (isGroup) {
                    rowBg = 'rgba(99,102,241,0.15)';
                    fontWeight = '700';
                    textColor = '#a5b4fc';
                } else if (isSub) {
                    rowBg = 'rgba(255,255,255,0.03)';
                    fontWeight = '600';
                    textColor = '#f8fafc';
                } else if (isContra) {
                    textColor = '#f87171';
                }

                tr.style.cssText = `background: ${rowBg}; border-bottom: 1px solid rgba(255,255,255,0.04); font-weight: ${fontWeight};`;

                const fmt = (v) => {
                    if (v === null || v === undefined || isNaN(v)) return '-';
                    if (v === 0) return '0';
                    return Math.round(v).toLocaleString();
                };

                const indent = isContra ? '&nbsp;&nbsp;&nbsp;&nbsp;↳ <b>(-)</b> ' : (isSub ? '&nbsp;&nbsp;' : '');

                tr.innerHTML = `
                    <td style="padding: 7px 16px; color: ${textColor};">${indent}${r.RawAccount || r.Account || '-'}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #94a3b8; font-family: monospace; font-size: 0.85rem;">${fmt(r.CurrentGross)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #34d399; font-weight: 700; font-family: monospace; font-size: 0.85rem;">${fmt(r.CurrentNet !== undefined && r.CurrentNet !== null ? r.CurrentNet : r.Current)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #94a3b8; font-family: monospace; font-size: 0.85rem;">${fmt(r.PriorGross)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #a5b4fc; font-weight: 700; font-family: monospace; font-size: 0.85rem;">${fmt(r.PriorNet !== undefined && r.PriorNet !== null ? r.PriorNet : r.Prior)}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 3. 손익계산서 (Income Statement) 특화 렌더러
        if (dataType === 'income_statement') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 16px; text-align: left; color: #f8fafc; font-weight: 700; width: 50%;">계정과목</th>
                    <th style="padding: 10px 14px; text-align: right; color: #34d399; font-weight: 700; width: 25%;">당기 금액</th>
                    <th style="padding: 10px 14px; text-align: right; color: #a5b4fc; font-weight: 700; width: 25%;">전기 금액</th>
                </tr>
            `;

            records.forEach(r => {
                const tr = document.createElement('tr');
                const isSub = r.RowKind === 'subtotal' || r.RowKind === 'group' || r.RowKind === 'total';
                
                tr.style.cssText = `background: ${isSub ? 'rgba(255,255,255,0.04)' : 'transparent'}; border-bottom: 1px solid rgba(255,255,255,0.04); font-weight: ${isSub ? '700' : '400'};`;

                const fmt = (v) => {
                    if (v === null || v === undefined || isNaN(v)) return '-';
                    if (v === 0) return '0';
                    return Math.round(v).toLocaleString();
                };

                tr.innerHTML = `
                    <td style="padding: 7px 16px; color: ${isSub ? '#f8fafc' : '#cbd5e1'};">${r.RawAccount || r.Account || '-'}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #34d399; font-weight: 600; font-family: monospace; font-size: 0.85rem;">${fmt(r.CurrentNet !== undefined && r.CurrentNet !== null ? r.CurrentNet : r.Current)}</td>
                    <td style="padding: 7px 14px; text-align: right; color: #a5b4fc; font-weight: 600; font-family: monospace; font-size: 0.85rem;">${fmt(r.PriorNet !== undefined && r.PriorNet !== null ? r.PriorNet : r.Prior)}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 4. 분개장 (Journal Entries) 특화 렌더러
        if (dataType === 'journal_entries') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 12px; text-align: center; color: #f8fafc; font-weight: 700; width: 10%;">전표일자</th>
                    <th style="padding: 10px 10px; text-align: center; color: #94a3b8; font-weight: 600; width: 7%;">전표번호</th>
                    <th style="padding: 10px 10px; text-align: center; color: #cbd5e1; font-weight: 600; width: 7%;">구분</th>
                    <th style="padding: 10px 10px; text-align: center; color: #a5b4fc; font-weight: 600; width: 7%;">Code</th>
                    <th style="padding: 10px 14px; text-align: left; color: #f8fafc; font-weight: 700; width: 16%;">계정과목</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 12%;">차변</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 12%;">대변</th>
                    <th style="padding: 10px 14px; text-align: left; color: #cbd5e1; font-weight: 600; width: 15%;">거래처</th>
                    <th style="padding: 10px 14px; text-align: left; color: #94a3b8; font-weight: 400; width: 14%;">적요</th>
                </tr>
            `;

            const fmt = (v) => (v === null || v === undefined || isNaN(v) || v === 0) ? '0' : Math.round(v).toLocaleString();

            records.slice(0, 300).forEach(r => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s;';
                tr.onmouseenter = () => tr.style.background = 'rgba(99,102,241,0.08)';
                tr.onmouseleave = () => tr.style.background = 'transparent';

                const dateVal = r['전표일자'] || r.Date || r.date || '-';
                const voucherVal = r['전표번호'] !== undefined ? r['전표번호'] : (r.VoucherNo || r.voucher_no || '-');
                const typeVal = r['구분'] || r.Type || r.entry_type || '-';
                const codeVal = r.Code !== undefined ? r.Code : (r.AccountCode || r.account_code || '-');
                const accVal = r['계정과목'] || r.AccountName || r.account_name || '-';
                const debitVal = r['차변'] !== undefined ? r['차변'] : (r.Debit || r.debit || 0);
                const creditVal = r['대변'] !== undefined ? r['대변'] : (r.Credit || r.credit || 0);
                const custVal = r['거래처'] || r.Customer || r.customer || '-';
                const descVal = r['적요'] || r.Description || r.description || '-';

                tr.innerHTML = `
                    <td style="padding: 6px 12px; text-align: center; color: #94a3b8; font-size: 0.82rem;">${dateVal}</td>
                    <td style="padding: 6px 10px; text-align: center; color: #cbd5e1; font-size: 0.82rem; font-weight: 600;">${voucherVal}</td>
                    <td style="padding: 6px 10px; text-align: center; color: ${typeVal === '차변' ? '#38bdf8' : (typeVal === '대변' ? '#f87171' : '#a78bfa')}; font-size: 0.82rem; font-weight: 600;">${typeVal}</td>
                    <td style="padding: 6px 10px; text-align: center; color: #a5b4fc; font-size: 0.82rem; font-family: monospace;">${codeVal}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #f8fafc; font-weight: 600;">${accVal}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${debitVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(debitVal)}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${creditVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(creditVal)}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #cbd5e1; font-size: 0.85rem;">${custVal}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #94a3b8; font-size: 0.82rem;">${descVal}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 5. 거래처원장 (Subledger) 특화 렌더러
        if (dataType === 'subledger') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 10px; text-align: center; color: #a5b4fc; font-weight: 600; width: 8%;">거래처코드</th>
                    <th style="padding: 10px 14px; text-align: left; color: #f8fafc; font-weight: 700; width: 18%;">거래처명</th>
                    <th style="padding: 10px 10px; text-align: center; color: #94a3b8; font-weight: 600; width: 7%;">코드</th>
                    <th style="padding: 10px 14px; text-align: left; color: #cbd5e1; font-weight: 700; width: 17%;">계정과목명</th>
                    <th style="padding: 10px 12px; text-align: right; color: #94a3b8; font-weight: 600; width: 12%;">전기(월)이월</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 13%;">차변</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 13%;">대변</th>
                    <th style="padding: 10px 14px; text-align: right; color: #34d399; font-weight: 700; width: 12%;">잔액</th>
                </tr>
            `;

            const fmt = (v) => (v === null || v === undefined || isNaN(v) || v === 0) ? '0' : Math.round(v).toLocaleString();

            records.slice(0, 300).forEach(r => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s;';
                tr.onmouseenter = () => tr.style.background = 'rgba(99,102,241,0.08)';
                tr.onmouseleave = () => tr.style.background = 'transparent';

                const custCode = r['거래처코드'] !== undefined ? r['거래처코드'] : (r.CustCode || r.cust_code || '-');
                const custName = r['거래처명'] || r.CustName || r.cust_name || '-';
                const accCode = r['코드'] !== undefined ? r['코드'] : (r.AccountCode || r.account_code || '-');
                const accName = r['계정과목명'] || r['계정과목'] || r.AccountName || r.account_name || '-';
                const priorVal = r['전기(월)이월'] !== undefined ? r['전기(월)이월'] : (r.PriorBalance || r.prior_balance || 0);
                const debitVal = r['차변'] !== undefined ? r['차변'] : (r.Debit || r.debit || 0);
                const creditVal = r['대변'] !== undefined ? r['대변'] : (r.Credit || r.credit || 0);
                const balVal = r['잔액'] !== undefined ? r['잔액'] : (r.EndBalance || r.end_balance || 0);

                tr.innerHTML = `
                    <td style="padding: 6px 10px; text-align: center; color: #a5b4fc; font-family: monospace; font-size: 0.82rem;">${custCode}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #f8fafc; font-weight: 600;">${custName}</td>
                    <td style="padding: 6px 10px; text-align: center; color: #94a3b8; font-family: monospace; font-size: 0.82rem;">${accCode}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #cbd5e1;">${accName}</td>
                    <td style="padding: 6px 12px; text-align: right; color: #94a3b8; font-family: monospace; font-size: 0.85rem;">${fmt(priorVal)}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${debitVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(debitVal)}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${creditVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(creditVal)}</td>
                    <td style="padding: 6px 14px; text-align: right; color: #34d399; font-weight: 700; font-family: monospace; font-size: 0.85rem;">${fmt(balVal)}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 6. 계정별원장 (General Ledger / Account Ledger) 특화 렌더러
        if (dataType === 'account_ledger') {
            thead.innerHTML = `
                <tr style="background: rgba(15,23,42,0.85); border-bottom: 2px solid rgba(99,102,241,0.4);">
                    <th style="padding: 10px 10px; text-align: center; color: #a5b4fc; font-weight: 600; width: 7%;">과목코드</th>
                    <th style="padding: 10px 14px; text-align: left; color: #f8fafc; font-weight: 700; width: 15%;">계정과목</th>
                    <th style="padding: 10px 12px; text-align: center; color: #94a3b8; font-weight: 600; width: 10%;">날짜</th>
                    <th style="padding: 10px 14px; text-align: left; color: #cbd5e1; font-weight: 600; width: 17%;">적요란</th>
                    <th style="padding: 10px 10px; text-align: center; color: #94a3b8; font-weight: 600; width: 7%;">코드</th>
                    <th style="padding: 10px 14px; text-align: left; color: #cbd5e1; font-weight: 600; width: 14%;">거래처</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 10%;">차변</th>
                    <th style="padding: 10px 12px; text-align: right; color: #38bdf8; font-weight: 700; width: 10%;">대변</th>
                    <th style="padding: 10px 14px; text-align: right; color: #34d399; font-weight: 700; width: 10%;">잔액</th>
                </tr>
            `;

            const fmt = (v) => (v === null || v === undefined || isNaN(v) || v === 0) ? '0' : Math.round(v).toLocaleString();

            records.slice(0, 300).forEach(r => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s;';
                tr.onmouseenter = () => tr.style.background = 'rgba(99,102,241,0.08)';
                tr.onmouseleave = () => tr.style.background = 'transparent';

                const accCode = r['계정과목코드'] !== undefined ? r['계정과목코드'] : (r.AccountCode || r.account_code || '-');
                const accName = r['계정과목'] || r.AccountName || r.account_name || '-';
                const dateVal = r['날짜'] || r.Date || r.date || '-';
                const descVal = r['적요란'] || r['적요'] || r.Description || r.description || '-';
                const custCode = r['코드'] !== undefined ? r['코드'] : (r.Code || r.code || '-');
                const custVal = r['거래처'] || r.Customer || r.customer || '-';
                const debitVal = r['차변'] !== undefined ? r['차변'] : (r.Debit || r.debit || 0);
                const creditVal = r['대변'] !== undefined ? r['대변'] : (r.Credit || r.credit || 0);
                const balVal = r['잔액'] !== undefined ? r['잔액'] : (r.Balance || r.balance || 0);

                tr.innerHTML = `
                    <td style="padding: 6px 10px; text-align: center; color: #a5b4fc; font-family: monospace; font-size: 0.82rem;">${accCode}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #f8fafc; font-weight: 600;">${accName}</td>
                    <td style="padding: 6px 12px; text-align: center; color: #94a3b8; font-size: 0.82rem;">${dateVal}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #cbd5e1; font-size: 0.85rem;">${descVal}</td>
                    <td style="padding: 6px 10px; text-align: center; color: #94a3b8; font-family: monospace; font-size: 0.82rem;">${custCode}</td>
                    <td style="padding: 6px 14px; text-align: left; color: #cbd5e1; font-size: 0.85rem;">${custVal}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${debitVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(debitVal)}</td>
                    <td style="padding: 6px 12px; text-align: right; color: ${creditVal > 0 ? '#38bdf8' : '#64748b'}; font-family: monospace; font-size: 0.85rem;">${fmt(creditVal)}</td>
                    <td style="padding: 6px 14px; text-align: right; color: #34d399; font-weight: 700; font-family: monospace; font-size: 0.85rem;">${fmt(balVal)}</td>
                `;
                tbody.appendChild(tr);
            });
            return;
        }

        // 7. 일반 원장/전표 범용 폴백 렌더러
        const headers = Object.keys(records[0] || {});
        const trHead = document.createElement('tr');
        trHead.style.background = 'rgba(15,23,42,0.85)';
        headers.forEach(h => {
            const th = document.createElement('th');
            th.style.cssText = 'padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); color: #94a3b8;';
            th.textContent = h;
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        records.slice(0, 150).forEach(r => {
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

    // 9. 실시간 회계 데이터 아카이브 & 업로드 이력 관리 센터 로직
    async function loadRealtimeUploadHistory(companyName = '') {
        const tbody = document.getElementById('realtime-upload-history-tbody');
        if (!tbody) return;

        let url = '/master/api/upload-history';
        if (companyName) {
            url += `?company_name=${encodeURIComponent(companyName)}`;
        }

        try {
            const data = await safeFetchJson(url, {}, '업로드 이력 조회에 실패했습니다.');
            const historyList = data.history || [];

            if (historyList.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px; color: #64748b;">저장된 업로드 이력이 없습니다.</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            historyList.forEach(item => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'border-bottom: 1px solid rgba(255,255,255,0.06); transition: background 0.2s;';
                tr.onmouseenter = () => tr.style.background = 'rgba(99,102,241,0.08)';
                tr.onmouseleave = () => tr.style.background = 'transparent';

                const cName = item.company_name || '미지정';
                const fy = item.fiscal_year || 2025;
                const savedAt = item.saved_at || '-';
                const score = item.integrity_score !== undefined ? item.integrity_score : 100;
                const sessId = item.session_id || '';
                const ledgers = item.ledgers_collected || {};

                // 6대 장부 뱃지 구성
                const ledgerBadges = [
                    { key: 'balance_sheet', label: 'BS', active: ledgers.balance_sheet },
                    { key: 'income_statement', label: 'IS', active: ledgers.income_statement },
                    { key: 'trial_balance', label: 'TB', active: ledgers.trial_balance },
                    { key: 'journal_entries', label: '분개', active: ledgers.journal_entries },
                    { key: 'subledger', label: '거래처', active: ledgers.subledger },
                    { key: 'account_ledger', label: '계정원장', active: ledgers.account_ledger }
                ].map(l => {
                    const bg = l.active ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.15)';
                    const color = l.active ? '#34d399' : '#64748b';
                    const border = l.active ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.06)';
                    return `<span style="display: inline-block; padding: 2px 6px; font-size: 0.7rem; font-weight: 600; border-radius: 4px; background: ${bg}; color: ${color}; border: 1px solid ${border};">${l.label}</span>`;
                }).join(' ');

                const scoreColor = score >= 90 ? '#34d399' : (score >= 70 ? '#fbbf24' : '#f87171');

                tr.innerHTML = `
                    <td style="padding: 10px 12px; font-weight: 600; color: #f8fafc;">${cName}</td>
                    <td style="padding: 10px 12px; text-align: center; color: #a5b4fc;">${fy}년</td>
                    <td style="padding: 10px 12px; font-size: 0.78rem; color: #94a3b8;">${savedAt}</td>
                    <td style="padding: 10px 12px;"><div style="display: flex; gap: 4px; flex-wrap: wrap;">${ledgerBadges}</div></td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: ${scoreColor};">${score}점</td>
                    <td style="padding: 10px 12px; text-align: center;">
                        <div style="display: flex; gap: 6px; justify-content: center; align-items: center;">
                            <button type="button" class="btn-view-health" data-company="${cName}" data-fy="${fy}" style="padding: 4px 8px; font-size: 0.75rem; background: rgba(16,185,129,0.2); border: 1px solid rgba(16,185,129,0.4); border-radius: 4px; color: #34d399; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="6대 장부 수집 대시보드 및 인스펙터 열기">
                                <span>👁️ 현황 보기</span>
                            </button>
                            <button type="button" class="btn-restore-history" data-company="${cName}" data-session="${sessId}" style="padding: 4px 10px; font-size: 0.75rem; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); border-radius: 4px; color: #a5b4fc; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                                <span>⚡ 0.01초 분석</span>
                            </button>
                            <button type="button" class="btn-download-history-zip" data-company="${cName}" data-session="${sessId}" style="padding: 4px 8px; font-size: 0.75rem; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; color: #cbd5e1; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="업로드된 원본 엑셀 ZIP 다운로드">
                                <span>📥 ZIP</span>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // 현황 보기 이벤트 바인딩
            tbody.querySelectorAll('.btn-view-health').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const c = e.currentTarget.getAttribute('data-company');
                    const fy = e.currentTarget.getAttribute('data-fy') || '2025';
                    if (!c) return;
                    
                    const compSelect = document.getElementById('ingest-company-select');
                    const nameInput = document.getElementById('analytics-direct-company-name');
                    const fySelect = document.getElementById('ingest-fiscal-year');

                    if (nameInput) nameInput.value = c;
                    if (fySelect) fySelect.value = fy;
                    if (compSelect) {
                        for (let i = 0; i < compSelect.options.length; i++) {
                            if (compSelect.options[i].value === c) {
                                compSelect.selectedIndex = i;
                                break;
                            }
                        }
                    }

                    window.loadMasterLakehouseHealthMatrix(c, fy);
                    window.scrollTo({ top: document.getElementById('analytics-health-container')?.offsetTop - 80 || 0, behavior: 'smooth' });
                });
            });

            // 복원 및 다운로드 이벤트 바인딩
            tbody.querySelectorAll('.btn-restore-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const c = e.currentTarget.getAttribute('data-company');
                    const s = e.currentTarget.getAttribute('data-session');
                    if (!c || !s) return;
                    
                    // 1. 기업 정밀 분석 탭으로 자동 이동
                    document.querySelector('.master-menu-item[data-menu="analytics-hub"]')?.click();

                    const loading = document.getElementById('analytics-loading');
                    const wrapper = document.getElementById('analytics-results-wrapper');
                    if (loading) loading.style.display = 'block';
                    if (wrapper) wrapper.style.display = 'none';

                    try {
                        // 2. 0.01초 즉시 복원 데이터 로드 및 렌더링
                        const payload = await safeFetchJson(`/master/api/upload-history/restore?company_name=${encodeURIComponent(c)}&session_id=${encodeURIComponent(s)}`);
                        renderAnalyticsPayload(payload);
                        
                        // 3. 셀렉트 박스 동기화
                        const compSel = document.getElementById('analytics-company-select');
                        if (compSel) {
                            for (let i = 0; i < compSel.options.length; i++) {
                                if (compSel.options[i].value === c) {
                                    compSel.selectedIndex = i;
                                    break;
                                }
                            }
                        }
                        window.scrollTo({ top: document.getElementById('analytics-results-wrapper')?.offsetTop || 0, behavior: 'smooth' });
                    } catch (err) {
                        alert(`복원 실패: ${err.message}`);
                    } finally {
                        if (loading) loading.style.display = 'none';
                    }
                });
            });

            tbody.querySelectorAll('.btn-download-history-zip').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const c = e.currentTarget.getAttribute('data-company');
                    const s = e.currentTarget.getAttribute('data-session');
                    if (!c || !s) return;
                    window.location.href = `/master/api/upload-history/download-raw?company_name=${encodeURIComponent(c)}&session_id=${encodeURIComponent(s)}`;
                });
            });

        } catch (err) {
            console.error('[MASTER_ANALYTICS:HISTORY_LOAD_ERROR]', err);
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: #f87171;">이력 로드 실패: ${err.message}</td></tr>`;
        }
    }

    // 10-0. 사내 Lakehouse Health Matrix 및 데이터셋 원본 자동 로드 함수
    window.loadMasterLakehouseHealthMatrix = async function (companyName, fiscalYear) {
        const healthContainer = document.getElementById('analytics-health-container');
        const badgeStatus = document.getElementById('health-lakehouse-status-badge');
        if (healthContainer) healthContainer.style.display = 'block';

        const safeComp = String(companyName || '').trim();
        const rawFy = fiscalYear || document.getElementById('ingest-fiscal-year')?.value || '2025';
        const curFy = String(rawFy).replace(/[^0-9]/g, '') || '2025';
        const priorFy = String(Number(curFy) - 1);

        if (!safeComp) {
            if (badgeStatus) {
                badgeStatus.innerHTML = `<span>⚪ 기업을 선택해 주세요</span>`;
                badgeStatus.style.color = '#94a3b8';
                badgeStatus.style.borderColor = 'rgba(255,255,255,0.15)';
            }
            return;
        }

        if (badgeStatus) {
            badgeStatus.innerHTML = `<span>⏳ [${safeComp}] 사내 MinIO 데이터 확인 중...</span>`;
            badgeStatus.style.color = '#fbbf24';
            badgeStatus.style.borderColor = 'rgba(245,158,11,0.4)';
        }

        try {
            console.log(`[MASTER_LAKEHOUSE:FETCH] 당기(${curFy}) 및 전기(${priorFy}) Lakehouse 데이터 병렬 조회: company=${safeComp}`);
            
            const [curRes, priorRes] = await Promise.all([
                fetch(`/api/company/normalized-dataset/${encodeURIComponent(safeComp)}?fiscal_year=${encodeURIComponent(curFy)}`).then(r => r.ok ? r.json() : null).catch(() => null),
                fetch(`/api/company/normalized-dataset/${encodeURIComponent(safeComp)}?fiscal_year=${encodeURIComponent(priorFy)}`).then(r => r.ok ? r.json() : null).catch(() => null)
            ]);

            console.log('[MASTER_LAKEHOUSE:RES]', { curRes, priorRes });

            const curDataObj = curRes && curRes.success ? curRes.data : null;
            const priorDataObj = priorRes && priorRes.success ? priorRes.data : null;

            if (!curDataObj && !priorDataObj) {
                console.log(`[MASTER_LAKEHOUSE:MISS] ${safeComp} 기업의 Lakehouse 데이터 없음.`);
                if (badgeStatus) {
                    badgeStatus.innerHTML = `<span>⚪ [${safeComp}] 사내 MinIO 미수집 (자료 업로드 필요)</span>`;
                    badgeStatus.style.color = '#94a3b8';
                    badgeStatus.style.borderColor = 'rgba(255,255,255,0.15)';
                }
                renderIngestionHealthBlock({
                    integrity_score: 0,
                    current_year: curFy,
                    prior_year: priorFy,
                    current: {
                        balance_sheet: { status: 'missing' },
                        income_statement: { status: 'missing' },
                        trial_balance: { status: 'missing' },
                        journal_entries: { status: 'missing' },
                        subledger: { status: 'missing' },
                        account_ledger: { status: 'missing' }
                    },
                    prior: {
                        balance_sheet: { status: 'missing' },
                        income_statement: { status: 'missing' },
                        trial_balance: { status: 'missing' },
                        journal_entries: { status: 'missing' },
                        subledger: { status: 'missing' },
                        account_ledger: { status: 'missing' }
                    }
                }, {});
                return;
            }

            // 1. 당기 데이터 객체 구성
            const curSt = (curDataObj && curDataObj.statements) || {};
            const curAf = (curDataObj && curDataObj.active_source_files) || {};
            const curItg = (curDataObj && curDataObj.integrity) || {};
            const curBs = curSt.balance_sheet || [];
            const curIs = curSt.income_statement || [];
            const curTb = curSt.trial_balance || [];
            const curJe = curSt.journal_entries || [];
            const curSl = curSt.subledger || [];
            const curGl = curSt.account_ledger || [];

            // 2. 전기 데이터 객체 구성
            const priSt = (priorDataObj && priorDataObj.statements) || {};
            const priAf = (priorDataObj && priorDataObj.active_source_files) || {};
            const priItg = (priorDataObj && priorDataObj.integrity) || {};
            const priBs = priSt.balance_sheet || [];
            const priIs = priSt.income_statement || [];
            const priTb = priSt.trial_balance || [];
            const priJe = priSt.journal_entries || [];
            const priSl = priSt.subledger || [];
            const priGl = priSt.account_ledger || [];

            const totalAccts = curBs.length + curIs.length + curTb.length + curJe.length + curSl.length + curGl.length +
                               priBs.length + priIs.length + priTb.length + priJe.length + priSl.length + priGl.length;

            const ingestionHealth = {
                integrity_score: (curItg.is_balanced !== false && (priItg.is_balanced !== false)) ? 100 : 85,
                current_year: curFy,
                prior_year: priorFy,
                current: {
                    balance_sheet: {
                        status: (curBs.length > 0 || curAf.bs) ? 'ready' : 'missing',
                        count: curBs.length,
                        filename: curAf.bs ? curAf.bs.filename : '',
                        is_balanced: curItg.is_balanced !== false
                    },
                    income_statement: {
                        status: (curIs.length > 0 || curAf.is) ? 'ready' : 'missing',
                        count: curIs.length,
                        filename: curAf.is ? curAf.is.filename : '',
                        is_balanced: true
                    },
                    trial_balance: {
                        status: (curTb.length > 0 || curAf.tb) ? 'ready' : 'missing',
                        count: curTb.length,
                        filename: curAf.tb ? curAf.tb.filename : '',
                        is_balanced: curItg.is_balanced !== false
                    },
                    journal_entries: {
                        status: (curJe.length > 0 || curAf.je) ? 'ready' : 'missing',
                        count: curJe.length > 0 ? `${curJe.length.toLocaleString()}건` : (curAf.je ? '전표수집완료' : 0),
                        filename: curAf.je ? curAf.je.filename : '',
                        is_balanced: true
                    },
                    subledger: {
                        status: (curSl.length > 0 || curAf.sl) ? 'ready' : 'missing',
                        count: curSl.length > 0 ? `${curSl.length.toLocaleString()}건` : (curAf.sl ? '원장수집완료' : 0),
                        filename: curAf.sl ? curAf.sl.filename : '',
                        is_balanced: true
                    },
                    account_ledger: {
                        status: (curGl.length > 0 || curAf.gl) ? 'ready' : 'missing',
                        count: curGl.length > 0 ? `${curGl.length.toLocaleString()}건` : (curAf.gl ? '총계정원장완료' : 0),
                        filename: curAf.gl ? curAf.gl.filename : '',
                        is_balanced: true
                    }
                },
                prior: {
                    balance_sheet: {
                        status: (priBs.length > 0 || priAf.bs) ? 'ready' : 'missing',
                        count: priBs.length,
                        filename: priAf.bs ? priAf.bs.filename : '',
                        is_balanced: priItg.is_balanced !== false
                    },
                    income_statement: {
                        status: (priIs.length > 0 || priAf.is) ? 'ready' : 'missing',
                        count: priIs.length,
                        filename: priAf.is ? priAf.is.filename : '',
                        is_balanced: true
                    },
                    trial_balance: {
                        status: (priTb.length > 0 || priAf.tb) ? 'ready' : 'missing',
                        count: priTb.length,
                        filename: priAf.tb ? priAf.tb.filename : '',
                        is_balanced: priItg.is_balanced !== false
                    },
                    journal_entries: {
                        status: (priJe.length > 0 || priAf.je) ? 'ready' : 'missing',
                        count: priJe.length > 0 ? `${priJe.length.toLocaleString()}건` : (priAf.je ? '전표수집완료' : 0),
                        filename: priAf.je ? priAf.je.filename : '',
                        is_balanced: true
                    },
                    subledger: {
                        status: (priSl.length > 0 || priAf.sl) ? 'ready' : 'missing',
                        count: priSl.length > 0 ? `${priSl.length.toLocaleString()}건` : (priAf.sl ? '원장수집완료' : 0),
                        filename: priAf.sl ? priAf.sl.filename : '',
                        is_balanced: true
                    },
                    account_ledger: {
                        status: (priGl.length > 0 || priAf.gl) ? 'ready' : 'missing',
                        count: priGl.length > 0 ? `${priGl.length.toLocaleString()}건` : (priAf.gl ? '총계정원장완료' : 0),
                        filename: priAf.gl ? priAf.gl.filename : '',
                        is_balanced: true
                    }
                }
            };

            const normalizedBundle = {
                balance_sheet: curBs.length > 0 ? curBs : priBs,
                income_statement: curIs.length > 0 ? curIs : priIs,
                trial_balance: curTb.length > 0 ? curTb : priTb,
                raw_datasets: {
                    balance_sheet: curBs.length > 0 ? curBs : priBs,
                    income_statement: curIs.length > 0 ? curIs : priIs,
                    trial_balance: curTb.length > 0 ? curTb : priTb,
                    journal_entries: curJe.length > 0 ? curJe : priJe,
                    subledger: curSl.length > 0 ? curSl : priSl,
                    account_ledger: curGl.length > 0 ? curGl : priGl
                }
            };

            // Lakehouse 연도별 전역 저장소에 캐시 등록
            window.masterLakehouseStore[curFy] = curDataObj || {};
            window.masterLakehouseStore[priorFy] = priorDataObj || {};

            currentAnalyticsData = {
                company_name: safeComp,
                normalized_bundle: normalizedBundle,
                ingestion_health: ingestionHealth,
                integrity: curItg
            };

            renderIngestionHealthBlock(ingestionHealth, normalizedBundle);

            if (badgeStatus) {
                const elapsed = (curRes && curRes.elapsed_ms) || '13.5';
                badgeStatus.innerHTML = `<span>🟢 [${safeComp}] 사내 MinIO 실시간 연동 (${totalAccts}개 계정 / ${elapsed}ms)</span>`;
                badgeStatus.style.color = '#34d399';
                badgeStatus.style.borderColor = 'rgba(16,185,129,0.35)';
            }

        } catch (err) {
            console.error('[MASTER_LAKEHOUSE:FATAL]', err);
            if (badgeStatus) {
                badgeStatus.innerHTML = `<span>⚠️ [${safeComp}] 데이터 로드 실패: ${err.message}</span>`;
                badgeStatus.style.color = '#f87171';
                badgeStatus.style.borderColor = 'rgba(239,68,68,0.35)';
            }
        }
    };

    // 10-1. [📂 회계자료 수집 & 보관소] 탭 전용 초기화 함수
    window.initDataIngestion = function () {
        console.log('[MASTER_INGEST] Data Ingestion & Repository 센터 초기화 시작');

        // 1. 등록 파트너사 선택 시 기업명 입력란 자동 채우기 & Lakehouse 자동 로드 연동
        const compSelect = document.getElementById('ingest-company-select');
        const nameInput = document.getElementById('analytics-direct-company-name');
        const fySelect = document.getElementById('ingest-fiscal-year');

        if (compSelect && nameInput) {
            compSelect.addEventListener('change', () => {
                if (compSelect.value) {
                    nameInput.value = compSelect.value;
                    window.loadMasterLakehouseHealthMatrix(compSelect.value, fySelect ? fySelect.value : '2025');
                } else {
                    window.loadMasterLakehouseHealthMatrix('', '');
                }
            });
        }

        if (fySelect) {
            fySelect.addEventListener('change', () => {
                const comp = (compSelect && compSelect.value) || (nameInput && nameInput.value);
                if (comp) {
                    window.loadMasterLakehouseHealthMatrix(comp, fySelect.value);
                }
            });
        }

        if (nameInput) {
            nameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && nameInput.value.trim()) {
                    window.loadMasterLakehouseHealthMatrix(nameInput.value.trim(), fySelect ? fySelect.value : '2025');
                }
            });
        }

        // 1-1. Health Matrix 내 DB 재동기화 버튼 바인딩
        const rebuildBtn = document.getElementById('btn-rebuild-health-lakehouse');
        if (rebuildBtn) {
            rebuildBtn.onclick = async function () {
                const comp = (compSelect && compSelect.value) || (nameInput && nameInput.value);
                const fy = fySelect ? fySelect.value : '2025';
                if (!comp) {
                    alert('재동기화할 기업을 선택해 주세요.');
                    return;
                }
                const originalText = rebuildBtn.innerHTML;
                rebuildBtn.innerHTML = '<span>⏳ 재동기화 중...</span>';
                rebuildBtn.disabled = true;
                try {
                    const res = await safeFetchJson('/api/company/rebuild-normalized', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ company: comp, fiscal_year: fy })
                    }, '재동기화에 실패했습니다.');
                    alert(`✓ [${comp}] 사내 MinIO 정규화 DB가 성공적으로 재구축되었습니다! (${res.accounts_count}개 계정 동기화)`);
                    window.loadMasterLakehouseHealthMatrix(comp, fy);
                } catch (err) {
                    alert(`재동기화 오류: ${err.message}`);
                } finally {
                    rebuildBtn.innerHTML = originalText;
                    rebuildBtn.disabled = false;
                }
            };
        }

        // 2. 파일 드롭존 바인딩
        const dropzone = document.getElementById('analytics-dropzone');
        const fileInput = document.getElementById('analytics-file-input');

        if (dropzone && fileInput) {
            dropzone.onclick = function (e) {
                if (e.target !== fileInput) {
                    fileInput.click();
                }
            };

            dropzone.ondragover = function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.style.borderColor = '#818cf8';
                dropzone.style.background = 'rgba(99,102,241,0.15)';
            };

            dropzone.ondragleave = function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (window.selectedDirectFiles && window.selectedDirectFiles.length > 0) {
                    dropzone.style.borderColor = '#10b981';
                    dropzone.style.background = 'rgba(16,185,129,0.08)';
                } else {
                    dropzone.style.borderColor = 'rgba(99,102,241,0.6)';
                    dropzone.style.background = 'rgba(99,102,241,0.05)';
                }
            };

            dropzone.ondrop = function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    Array.from(e.dataTransfer.files).forEach(f => {
                        if (!window.selectedDirectFiles.some(existing => existing.name === f.name)) {
                            window.selectedDirectFiles.push(f);
                        }
                    });
                    window.renderSelectedFilesChips();
                }
            };

            fileInput.onchange = function (e) {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(f => {
                        if (!window.selectedDirectFiles.some(existing => existing.name === f.name)) {
                            window.selectedDirectFiles.push(f);
                        }
                    });
                    window.renderSelectedFilesChips();
                    fileInput.value = '';
                }
            };
        }

        // 3. 수집 실행 버튼 바인딩
        const runIngestBtn = document.getElementById('btn-run-ingest');
        if (runIngestBtn) {
            runIngestBtn.onclick = function () {
                window.handleIngestFiles();
            };
        }

        // 3-1. 수동 데이터 조회 버튼 바인딩
        const queryLakehouseBtn = document.getElementById('btn-query-lakehouse');
        if (queryLakehouseBtn) {
            queryLakehouseBtn.onclick = function () {
                const comp = (compSelect && compSelect.value) || (nameInput && nameInput.value.trim());
                const fy = fySelect ? fySelect.value : '2025';
                if (!comp) {
                    alert('조회할 기업을 선택하거나 입력해 주세요.');
                    return;
                }
                window.loadMasterLakehouseHealthMatrix(comp, fy);
            };
        }

        // 4. 실시간 이력 새로고침 버튼 바인딩
        const refreshHistBtn = document.getElementById('btn-refresh-upload-history');
        if (refreshHistBtn) {
            refreshHistBtn.onclick = function () {
                loadRealtimeUploadHistory();
            };
        }

        // 초기 이력 목록 로드
        loadRealtimeUploadHistory();

        // 초기 기업이 선택되어 있거나 첫 번째 유효 기업이 있다면 Lakehouse 즉시 감지 로드
        const activeComp = (compSelect && compSelect.value) || (nameInput && nameInput.value.trim());
        if (activeComp) {
            window.loadMasterLakehouseHealthMatrix(activeComp, fySelect ? fySelect.value : '2025');
        } else if (compSelect && compSelect.options.length > 1) {
            for (let i = 0; i < compSelect.options.length; i++) {
                if (compSelect.options[i].value) {
                    compSelect.selectedIndex = i;
                    if (nameInput) nameInput.value = compSelect.options[i].value;
                    window.loadMasterLakehouseHealthMatrix(compSelect.options[i].value, fySelect ? fySelect.value : '2025');
                    break;
                }
            }
        }

        console.log('[MASTER_INGEST] Data Ingestion & Repository 센터 초기화 완료');
    };

    // 10-2. [🧠 기업 정밀 분석 허브] 탭 전용 초기화 함수
    window.initAnalyticsHub = function () {
        console.log('[MASTER_ANALYTICS] Analytics Hub 컨트롤러 초기화');

        // 저장본 분석 실행 버튼 바인딩
        const runStoredBtn = document.getElementById('btn-run-stored-analysis');
        if (runStoredBtn) {
            runStoredBtn.onclick = () => handleStoredAnalysis();
        }

        // 기업 선택 시 보관 이력 타임스탬프 목록 로드
        const compSelect = document.getElementById('analytics-company-select');
        if (compSelect) {
            compSelect.onchange = () => {
                fetchLocalArchiveHistory(compSelect.value);
            };
            if (compSelect.value) {
                fetchLocalArchiveHistory(compSelect.value);
            }
        }

        // 보고서 복사 / 다운로드 / DB 저장 바인딩
        document.getElementById('btn-save-current-analysis')?.addEventListener('click', handleSaveAnalysis);
        document.getElementById('btn-copy-report-md')?.addEventListener('click', handleCopyMarkdown);
        document.getElementById('btn-download-report-md')?.addEventListener('click', handleDownloadMarkdown);

        // 데이터 인스펙터 모달 이벤트
        document.querySelectorAll('.btn-inspect-data').forEach(btn => {
            btn.onclick = (e) => {
                const dtype = e.currentTarget.getAttribute('data-type');
                openDataInspector(dtype);
            };
        });

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

    // =========================================================================
    // 🏢 마스터 포털: 회사별 Job Assign(감사팀 및 계정 배정) 관리 모듈
    // =========================================================================
    let masterAssignmentsCache = [];

    window.loadMasterJobAssignments = async function () {
        const tbody = document.getElementById('master-assign-table-body');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 25px; color: var(--text-secondary);">
                    ⏳ 배정 데이터를 불러오는 중입니다...
                </td>
            </tr>
        `;

        try {
            const data = await safeFetchJson('/api/audit/assignments');
            if (data.success && data.assignments) {
                masterAssignmentsCache = data.assignments;
                renderJobAssignTable(data.assignments);
            }
        } catch (err) {
            console.error('[ASSIGN:LOAD_ERR]', err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 25px; color: #f87171;">
                        ❌ 배정 목록 로드 실패: ${err.message}
                    </td>
                </tr>
            `;
        }
    };

    function renderJobAssignTable(assignments) {
        const tbody = document.getElementById('master-assign-table-body');
        if (!tbody) return;

        if (!assignments || assignments.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 30px; color: var(--text-secondary);">
                        등록된 감사 배정 내역이 없습니다. 상단 [➕ 신규 감사 배정] 버튼으로 등록하세요.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = assignments.map(a => {
            const memberNames = (a.members || []).map(m => m.name || m.email).join(', ') || '-';
            const accCounts = Object.keys(a.account_assignments || {}).length;
            const statusBadge = a.status === 'in_progress'
                ? '<span style="color: #38bdf8; background: rgba(56,189,248,0.15); padding: 3px 8px; border-radius: 4px; font-size: 0.78rem;">실증감사 진행중</span>'
                : '<span style="color: #a855f7; background: rgba(168,85,247,0.15); padding: 3px 8px; border-radius: 4px; font-size: 0.78rem;">' + (a.status_label || '기획/계획 단계') + '</span>';

            const safeComp = (a.company_name || '').replace(/'/g, "\\'");
            return `
                <tr>
                    <td class="col-company"><strong>${a.company_name}</strong></td>
                    <td><span class="badge" style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">${a.fiscal_year}년</span></td>
                    <td>
                        <div style="font-weight: 600; color: #f8fafc; font-size: 0.88rem;">${a.in_charge_name || '미지정'}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">${a.in_charge_email || ''}</div>
                    </td>
                    <td style="font-size: 0.84rem; color: #cbd5e1;">${memberNames}</td>
                    <td>
                        <span class="badge-tag" style="background: rgba(16,185,129,0.15); color: #34d399; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px;">
                            ${accCounts}개 계정 지정
                        </span>
                    </td>
                    <td>${statusBadge}</td>
                    <td style="font-size: 0.82rem; color: #94a3b8;">${a.target_report_date || '-'}</td>
                    <td>
                        <button type="button" onclick="openJobAssignModal('${safeComp}')" class="btn-submit" style="padding: 4px 12px; font-size: 0.8rem; width: auto;">
                            ✏️ 배정 수정
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    window.openJobAssignModal = function (companyName = '') {
        const modal = document.getElementById('modal-job-assign');
        if (!modal) return;

        const form = document.getElementById('form-job-assign');
        if (form) form.reset();

        const titleEl = document.getElementById('job-assign-modal-title');
        const compInput = document.getElementById('assign-company-name');
        const yearSelect = document.getElementById('assign-fiscal-year');
        const inchargeEmail = document.getElementById('assign-incharge-email');
        const inchargeName = document.getElementById('assign-incharge-name');
        const partnerName = document.getElementById('assign-partner-name');
        const statusSelect = document.getElementById('assign-status');

        if (companyName) {
            titleEl.textContent = `[${companyName}] 감사팀 및 계정 배정 수정`;
            const found = masterAssignmentsCache.find(a => a.company_name === companyName);
            if (found) {
                compInput.value = found.company_name || '';
                compInput.readOnly = true;
                yearSelect.value = String(found.fiscal_year || 2025);
                inchargeEmail.value = found.in_charge_email || '';
                inchargeName.value = found.in_charge_name || '';
                partnerName.value = found.partner_name || '';
                statusSelect.value = found.status || 'in_progress';

                const accMap = found.account_assignments || {};
                const accA = document.getElementById('assign-acc-A-0');
                const accC = document.getElementById('assign-acc-C-0');
                const accE = document.getElementById('assign-acc-E-0');
                const accG = document.getElementById('assign-acc-G-0');
                if (accA) accA.value = accMap['A-0'] || '';
                if (accC) accC.value = accMap['C-0'] || '';
                if (accE) accE.value = accMap['E-0'] || '';
                if (accG) accG.value = accMap['G-0'] || '';
            }
        } else {
            titleEl.textContent = '➕ 신규 감사팀 및 계정 배정 등록';
            compInput.readOnly = false;
            compInput.value = '';
            yearSelect.value = '2025';
            inchargeEmail.value = 'cpaeastsun@gmail.com';
            inchargeName.value = '김동선';
            partnerName.value = '이진우 파트너';
            statusSelect.value = 'planned';
        }

        modal.style.display = 'flex';
    };

    window.closeJobAssignModal = function () {
        const modal = document.getElementById('modal-job-assign');
        if (modal) modal.style.display = 'none';
    };

    window.handleSaveJobAssignment = async function (e) {
        e.preventDefault();
        const compName = document.getElementById('assign-company-name').value.trim();
        const fiscalYear = parseInt(document.getElementById('assign-fiscal-year').value, 10) || 2025;
        const inchargeEmail = document.getElementById('assign-incharge-email').value.trim();
        const inchargeName = document.getElementById('assign-incharge-name').value.trim();
        const partnerName = document.getElementById('assign-partner-name').value.trim();
        const status = document.getElementById('assign-status').value;

        const statusLabels = {
            'planned': '기획/계획 단계',
            'interim': '사전/중간 감사',
            'in_progress': '실증감사 진행중',
            'final_review': '감사완결 및 심리',
            'completed': '보고서 발행완료'
        };

        const accMap = {};
        const accA = document.getElementById('assign-acc-A-0')?.value.trim();
        const accC = document.getElementById('assign-acc-C-0')?.value.trim();
        const accE = document.getElementById('assign-acc-E-0')?.value.trim();
        const accG = document.getElementById('assign-acc-G-0')?.value.trim();

        if (accA) accMap['A-0'] = accA;
        if (accC) accMap['C-0'] = accC;
        if (accE) accMap['E-0'] = accE;
        if (accG) accMap['G-0'] = accG;

        const members = [];
        if (inchargeEmail) {
            members.push({ name: inchargeName || 'In-Charge', email: inchargeEmail, role: 'In-charge' });
        }
        [accA, accC, accE, accG].forEach(em => {
            if (em && !members.some(m => m.email === em)) {
                members.push({ name: em.split('@')[0], email: em, role: 'Staff CPA' });
            }
        });

        const payload = {
            company_name: compName,
            fiscal_year: fiscalYear,
            in_charge_name: inchargeName,
            in_charge_email: inchargeEmail,
            partner_name: partnerName,
            members: members,
            account_assignments: accMap,
            status: status,
            status_label: statusLabels[status] || '진행중',
            target_report_date: '2026-03-20'
        };

        try {
            const res = await safeFetchJson('/api/audit/assignments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.success) {
                alert(`✓ [${compName}] 감사팀 및 계정 배정이 성공적으로 저장되었습니다.`);
                closeJobAssignModal();
                loadMasterJobAssignments();
            } else {
                alert(`배정 저장 실패: ${res.error || '알 수 없는 오류'}`);
            }
        } catch (err) {
            console.error('[ASSIGN:SAVE_ERR]', err);
            alert(`배정 저장 중 오류가 발생했습니다: ${err.message}`);
        }
    };

    // DOM 로드 완료 시 기본 초기화
    document.addEventListener('DOMContentLoaded', () => {
        window.initDataIngestion();
        window.initAnalyticsHub();
    });

})();


