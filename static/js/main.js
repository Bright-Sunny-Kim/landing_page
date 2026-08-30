// Premium Interaction JavaScript

document.addEventListener('DOMContentLoaded', () => {
    if (typeof marked === 'undefined') {
        const script = document.createElement('script');
        script.src = "https://cdn.jsdelivr.net/npm/marked/marked.min.js";
        document.head.appendChild(script);
    }

    // 1. 로그인 폼 동적 제어 로직
    const loginForm = document.getElementById('login-form');
    const emailInput = document.getElementById('email');
    const emailStatusMsg = document.getElementById('email-status-msg');
    const passwordGroup = document.getElementById('password-group');
    const passwordInput = document.getElementById('password');
    const passwordLabel = document.getElementById('password-label');
    const rememberGroup = document.getElementById('remember-group');
    const rememberCheckbox = document.getElementById('remember');
    const additionalFields = document.getElementById('additional-fields');
    const submitBtn = document.getElementById('btn-submit');

    // 추가 필드 요소들
    const corporateNumberInput = document.getElementById('corporate_number');
    const companyInput = document.getElementById('company');
    const usernameInput = document.getElementById('username');
    const taskInput = document.getElementById('task_type');

    let isExistingUser = false; // DB 등록 여부 플래그
    let isEmailChecking = false;

    // 이메일 유효성 체크 함수
    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    // 법인등록번호 유효성 체크 함수
    const validateCorporateNumber = (num) => {
        const regex = /^\d{6}-\d{7}$/;
        return regex.test(num);
    };

    if (emailInput && emailStatusMsg && additionalFields && passwordGroup && submitBtn) {
        
        // 실시간 이메일 DB 체크 함수
        const checkEmailDb = async () => {
            const emailValue = emailInput.value.trim();

            if (!emailValue) {
                emailStatusMsg.textContent = '';
                emailStatusMsg.className = 'email-status-msg';
                additionalFields.classList.remove('show');
                setFieldsRequired(false);
                submitBtn.querySelector('span').textContent = '로그인';
                return;
            }

            if (!validateEmail(emailValue)) {
                emailStatusMsg.textContent = '올바른 이메일 주소 형식을 입력해 주세요.';
                emailStatusMsg.className = 'email-status-msg error';
                additionalFields.classList.remove('show');
                setFieldsRequired(false);
                submitBtn.querySelector('span').textContent = '로그인';
                return;
            }

            if (isEmailChecking) return;
            isEmailChecking = true;

            try {
                // 백엔드 비동기 API 호출
                const response = await fetch('/check-email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email: emailValue })
                });

                if (response.ok) {
                    const result = await response.json();
                    
                    if (result.exists) {
                        isExistingUser = true;
                        
                        // 기존 비밀번호 설정 유무에 따라 헬퍼 메시지 가변 처리
                        if (result.has_password) {
                            emailStatusMsg.textContent = '✓ 등록된 파트너사 이메일입니다. 비밀번호를 입력하세요.';
                            emailStatusMsg.className = 'email-status-msg success';
                            passwordLabel.textContent = '비밀번호';
                        } else {
                            // 기존 회원이지만 패스워드 신설 전인 상태
                            emailStatusMsg.textContent = '✦ 최초 비밀번호 설정이 필요합니다. 사용할 비밀번호를 입력하세요.';
                            emailStatusMsg.className = 'email-status-msg info';
                            passwordLabel.textContent = '신규 비밀번호 설정';
                        }
                        
                        // 추가 정보 필드는 숨기기
                        additionalFields.classList.remove('show');
                        
                        setFieldsRequired(false);
                        passwordInput.required = true;
                        
                        submitBtn.querySelector('span').textContent = '로그인';
                    } else {
                        isExistingUser = false;
                        emailStatusMsg.textContent = '✦ 신규 파트너사 등록이 필요합니다. 상세 정보를 입력해 주세요.';
                        emailStatusMsg.className = 'email-status-msg info';
                        passwordLabel.textContent = '비밀번호 설정';
                        
                        // 추가 정보 필드 노출
                        additionalFields.classList.add('show');
                        
                        setFieldsRequired(true);
                        passwordInput.required = true;
                        
                        submitBtn.querySelector('span').textContent = '신규 등록 및 로그인';
                    }
                }
            } catch (error) {
                console.error('Email check failed:', error);
            } finally {
                isEmailChecking = false;
            }
        };

        // 추가 필드 필수 여부 동적 설정 함수
        const setFieldsRequired = (isRequired) => {
            if (corporateNumberInput) corporateNumberInput.required = isRequired;
            if (companyInput) companyInput.required = isRequired;
            if (usernameInput) usernameInput.required = isRequired;
            if (taskInput) taskInput.required = isRequired;
        };

        // 포커스 아웃(blur) 및 입력 이벤트 감지
        emailInput.addEventListener('blur', checkEmailDb);
        
        let emailDebounceTimer;
        emailInput.addEventListener('input', () => {
            clearTimeout(emailDebounceTimer);
            emailDebounceTimer = setTimeout(checkEmailDb, 600);
        });

        // 자동 로그인 유지 체크박스 복원 및 이메일 자동 채우기
        const rememberedEmail = localStorage.getItem('remembered_email');
        if (rememberedEmail) {
            emailInput.value = rememberedEmail;
            if (rememberCheckbox) rememberCheckbox.checked = true;
            // 폼 렌더링 후 약간의 딜레이를 주어 이메일 자동 조회 수행
            setTimeout(checkEmailDb, 300);
        }
    }

    // 로그인 폼 제출 유효성 검사
    if (loginForm && submitBtn && emailInput) {
        loginForm.addEventListener('submit', (e) => {
            const emailValue = emailInput.value.trim();
            const passwordValue = passwordInput.value.trim();

            if (!emailValue || !validateEmail(emailValue)) {
                e.preventDefault();
                alert('올바른 이메일 주소를 입력해 주세요.');
                return;
            }

            if (!passwordValue) {
                e.preventDefault();
                alert('비밀번호를 입력해 주세요.');
                return;
            }

            // 신규 사용자인데 추가 정보가 입력되지 않은 경우 방지
            if (!isExistingUser) {
                const corpNum = corporateNumberInput.value.trim();
                if (!corpNum || !companyInput.value.trim() || !usernameInput.value.trim() || !taskInput.value) {
                    e.preventDefault();
                    alert('신규 파트너사 등록을 위해 모든 항목을 입력해 주세요.');
                    return;
                }
                if (!validateCorporateNumber(corpNum)) {
                    e.preventDefault();
                    alert('법인등록번호는 000000-0000000 형식으로 입력해야 합니다.');
                    return;
                }
            }

            // 로그인 상태 유지가 체크되어 있다면 로컬스토리지에 이메일 저장
            if (rememberCheckbox && rememberCheckbox.checked) {
                localStorage.setItem('remembered_email', emailValue);
            } else {
                localStorage.removeItem('remembered_email');
            }

            // 제출 시 비주얼 피드백
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.8';
            submitBtn.querySelector('span').textContent = '인증 처리 중...';
        });
    }

    // 2. 모의 소셜 로그인 (Mock OAuth) 핸들러
    const btnGoogle = document.getElementById('btn-google');
    const btnNaver = document.getElementById('btn-naver');
    const oauthModal = document.getElementById('oauth-modal');
    const oauthModalClose = document.getElementById('oauth-modal-close');
    const oauthModalTitle = document.getElementById('oauth-modal-title');
    const oauthLogo = document.getElementById('oauth-logo');
    const oauthEmailInput = document.getElementById('oauth-email');
    const oauthAdditionalFields = document.getElementById('oauth-additional-fields');
    const btnOauthSubmit = document.getElementById('btn-oauth-submit');
    
    // 소셜 입력 필드들
    const oauthCorporateNumber = document.getElementById('oauth-corporate_number');
    const oauthCompany = document.getElementById('oauth-company');
    const oauthUsername = document.getElementById('oauth-username');
    const oauthTask = document.getElementById('oauth-task_type');
    
    let currentProvider = ''; // 'google' or 'naver'
    
    const openOauthModal = (provider) => {
        if (!oauthModal) return;
        currentProvider = provider;
        oauthEmailInput.value = '';
        if (oauthCorporateNumber) oauthCorporateNumber.value = '';
        oauthCompany.value = '';
        oauthUsername.value = '';
        oauthTask.value = '';
        oauthAdditionalFields.classList.remove('show');
        
        // 필드 필수 해제
        setOauthFieldsRequired(false);
        
        if (provider === 'google') {
            oauthModalTitle.textContent = 'Google 계정으로 로그인';
            oauthLogo.textContent = 'G';
            oauthLogo.className = 'oauth-provider-logo google-theme';
        } else {
            oauthModalTitle.textContent = 'Naver 계정으로 로그인';
            oauthLogo.textContent = 'N';
            oauthLogo.className = 'oauth-provider-logo naver-theme';
        }
        
        oauthModal.classList.remove('hidden');
    };
    
    const closeOauthModal = () => {
        if (oauthModal) oauthModal.classList.add('hidden');
    };
    
    const setOauthFieldsRequired = (isRequired) => {
        if (oauthCorporateNumber) oauthCorporateNumber.required = isRequired;
        oauthCompany.required = isRequired;
        oauthUsername.required = isRequired;
        oauthTask.required = isRequired;
    };
    
    if (btnGoogle) btnGoogle.addEventListener('click', () => openOauthModal('google'));
    if (btnNaver) btnNaver.addEventListener('click', () => openOauthModal('naver'));
    if (oauthModalClose) oauthModalClose.addEventListener('click', closeOauthModal);
    
    // 모달 바깥 영역 클릭 시 닫기
    if (oauthModal) {
        oauthModal.addEventListener('click', (e) => {
            if (e.target === oauthModal) closeOauthModal();
        });
    }
    
    if (btnOauthSubmit && oauthEmailInput) {
        btnOauthSubmit.addEventListener('click', async () => {
            const email = oauthEmailInput.value.trim();
            if (!email || !validateEmail(email)) {
                alert('올바른 이메일 주소를 입력하세요.');
                return;
            }
            
            const isNeedRegister = oauthAdditionalFields.classList.contains('show');
            let requestData = {
                email: email,
                provider: currentProvider,
                remember: rememberCheckbox ? rememberCheckbox.checked : false
            };
            
            if (isNeedRegister) {
                const corpNum = oauthCorporateNumber ? oauthCorporateNumber.value.trim() : '';
                const company = oauthCompany.value.trim();
                const username = oauthUsername.value.trim();
                const task = oauthTask.value;
                
                if (!corpNum || !company || !username || !task) {
                    alert('신규 소셜 파트너사 등록을 위해 모든 항목을 입력해 주세요.');
                    return;
                }
                
                if (!validateCorporateNumber(corpNum)) {
                    alert('법인등록번호는 000000-0000000 형식으로 입력해야 합니다.');
                    return;
                }
                
                requestData.corporate_number = corpNum;
                requestData.company = company;
                requestData.username = username;
                requestData.task_type = task;
            }
            
            btnOauthSubmit.disabled = true;
            btnOauthSubmit.querySelector('span').textContent = '소셜 인증 중...';
            
            try {
                const response = await fetch('/login/social', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    if (result.need_registration) {
                        // 최초 로그인 시 추가 가입 양식 노출
                        alert('✦ 등록되지 않은 소셜 계정입니다. 파트너사 정보를 추가로 입력해 주세요.');
                        oauthAdditionalFields.classList.add('show');
                        setOauthFieldsRequired(true);
                        btnOauthSubmit.disabled = false;
                        btnOauthSubmit.querySelector('span').textContent = '정보 등록 및 로그인';
                    } else if (result.success && result.redirect) {
                        // 로그인 성공 시 리다이렉트
                        if (rememberCheckbox && rememberCheckbox.checked) {
                            localStorage.setItem('remembered_email', email);
                        } else {
                            localStorage.removeItem('remembered_email');
                        }
                        
                        btnOauthSubmit.querySelector('span').textContent = '인증 완료! 이동 중...';
                        window.location.href = result.redirect;
                    } else if (result.error) {
                        alert(result.error);
                        btnOauthSubmit.disabled = false;
                        btnOauthSubmit.querySelector('span').textContent = '인증 및 로그인';
                    }
                } else {
                    alert('소셜 로그인 처리 중 서버 오류가 발생했습니다.');
                    btnOauthSubmit.disabled = false;
                    btnOauthSubmit.querySelector('span').textContent = '인증 및 로그인';
                }
            } catch (error) {
                console.error('Social login failed:', error);
                alert('소셜 네트워크 연결 중 오류가 발생했습니다.');
                btnOauthSubmit.disabled = false;
                btnOauthSubmit.querySelector('span').textContent = '인증 및 로그인';
            }
        });
    }

    // 3. 감사 제출 파일 실시간 미리보기 및 폼 유효성 체크
    const requestForm = document.getElementById('request-form');
    const miniFileInputs = document.querySelectorAll('.mini-file-input');
    const requestSubmitBtn = document.getElementById('btn-request-submit');

    if (miniFileInputs.length > 0) {
        miniFileInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                const label = document.getElementById(`label-${input.id}`);
                if (label) {
                    if (e.target.files && e.target.files.length > 0) {
                        const name = e.target.files[0].name;
                        const textSpan = label.querySelector('.file-text');
                        if (textSpan) textSpan.textContent = name;
                        label.classList.add('has-file');
                        
                        // 아이콘을 체크표시로 교체
                        const iconSpan = label.querySelector('.upload-icon');
                        if (iconSpan) iconSpan.textContent = '✓';
                    } else {
                        const textSpan = label.querySelector('.file-text');
                        if (textSpan) textSpan.textContent = '파일 선택';
                        label.classList.remove('has-file');
                        
                        const iconSpan = label.querySelector('.upload-icon');
                        if (iconSpan) iconSpan.textContent = '↑';
                    }
                }
            });
        });
    }

    if (requestForm && requestSubmitBtn) {
        requestForm.addEventListener('submit', (e) => {
            const helpText = document.getElementById('help_text').value.trim();
            
            // 16개 파일 인풋 중 하나라도 파일이 올라갔는지 확인
            let hasAnyFile = false;
            miniFileInputs.forEach(input => {
                if (input.files && input.files.length > 0) {
                    hasAnyFile = true;
                }
            });

            if (!helpText && !hasAnyFile) {
                e.preventDefault();
                alert('추가 요청사항을 작성하거나 1개 이상의 감사 서류 파일을 첨부해 주세요.');
                return;
            }
            
            // 로딩 상태 표시
            requestSubmitBtn.disabled = true;
            requestSubmitBtn.style.opacity = '0.8';
            const btnSpan = requestSubmitBtn.querySelector('span');
            if (btnSpan) btnSpan.textContent = '업로드 중...';
        });
    }

    // 4. 마스터 관리자 사이드바 클릭 상호작용 및 3대 메인 탭 전환 로직
    const sidebarMenuItems = document.querySelectorAll('.master-menu-item');
    const masterMainContent = document.getElementById('master-main-content');
    const homeDashboardView = document.getElementById('home-dashboard-view');
    const detailDashboardView = document.getElementById('detail-dashboard-view');

    // 각 메뉴명에 대응하는 한글 정보 및 설명 정의 (부가 기능용)
    const menuMockData = {
        calendar: {
            title: '📅 세무 일정 캘린더',
            desc: '법인세, 부가가치세, 원천세 신고 등 월별 주요 국가 세무 일정표와 각 파트너사 담당자와의 세무 대면 상담 및 법인 회계 감사 방문 실사 스케줄을 한눈에 관리하는 통합 세무 캘린더입니다.',
            icon: '📅',
            placeholder: '국세청 세무 신고 스케줄러 & 방문 상담 캘린더'
        },
        chat: {
            title: '💬 실시간 자문 상담',
            desc: '비즈니스 파트너사 담당자가 실시간으로 문의하는 세무/회계 관련 일상 자문 건에 대해 회계사가 즉시 답변하고 자료 조회를 제공하는 실시간 질의응답 아카이브 및 채팅 관리 패널입니다.',
            icon: '💬',
            placeholder: '1:1 파트너사 실시간 세무 자문 채팅창'
        },
        billing: {
            title: '💳 수수료 및 청구 관리',
            desc: '매월 발생하는 기장 서비스 수수료, 연간 세무조정 수수료, 인수합병(M&A) 및 재무 감사 실사 용역 비용 청구서를 안전하게 발행하고 완납/미납 결제 여부를 통합 대조하는 빌링 대시보드입니다.',
            icon: '💳',
            placeholder: '기업 수수료 청구서 및 정기 기장료 수납 추적기'
        },
        settings: {
            title: '⚙️ 포털 시스템 설정',
            desc: '최고 관리자(Master) 계정 관리 및 추가 부회계사 권한 부여, 파트너사 포털 접근 차단/해제 IP 제어, 시스템 보안 감사 로그 모니터링 및 PWA 설치형 웹 사이트의 캐시 리프레시 설정을 관리하는 시스템 패널입니다.',
            icon: '⚙️',
            placeholder: '보안 접근 제어 및 서브 관리자 권한 설정 센터'
        }
    };

    // 서브탭 전환 공통 함수
    window.switchMasterSubtab = function(containerId, targetSubtabId) {
        try {
            const container = document.getElementById(containerId) || document;
            const subtabBtns = container.querySelectorAll('.master-subtab-btn');
            const subtabPanes = container.querySelectorAll('.master-subtab-pane');

            subtabBtns.forEach(btn => {
                const target = btn.getAttribute('data-subtab');
                if (target === targetSubtabId) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            subtabPanes.forEach(pane => {
                if (pane.id === targetSubtabId) {
                    pane.classList.add('active');
                    pane.style.display = 'block';
                } else {
                    pane.classList.remove('active');
                    pane.style.display = 'none';
                }
            });

            console.log(`[SUBTAB] 서브 탭 전환 완료 -> (${containerId} > ${targetSubtabId})`);
        } catch (err) {
            console.error('[ERROR] 서브탭 전환 중 오류:', err);
        }
    };

    // 서브탭 클릭 이벤트 위임
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.master-subtab-btn');
        if (btn) {
            e.preventDefault();
            const targetSubtab = btn.getAttribute('data-subtab');
            const navContainer = btn.closest('.master-subnav-container');
            const parentView = btn.closest('.master-card') || document;
            
            console.log(`[SUBTAB] 서브 탭 전환 시도: ${targetSubtab}`);
            
            if (navContainer) {
                navContainer.querySelectorAll('.master-subtab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            }
            
            if (parentView && targetSubtab) {
                parentView.querySelectorAll('.master-subtab-pane').forEach(p => {
                    if (p.id === targetSubtab) {
                        p.classList.add('active');
                        p.style.display = 'block';
                    } else {
                        p.classList.remove('active');
                        p.style.display = 'none';
                    }
                });
            }
        }
    });

    if (sidebarMenuItems.length > 0 && masterMainContent) {
        let currentActiveMenu = 'home';

        sidebarMenuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const menu = item.getAttribute('data-menu');
                const menuLabel = item.querySelector('span')?.textContent.trim() || 'Master Portal';
                const prevMenu = currentActiveMenu;

                console.log(`[NAV] 탭 전환 시작 (${prevMenu} -> ${menu})`);

                // URL 해시 및 브라우저 타이틀 동기화
                history.replaceState(null, '', `#tab-${menu}`);
                document.title = `${menuLabel} | Hyean Master Portal`;
                sidebarMenuItems.forEach(i => i.removeAttribute('aria-current'));
                item.setAttribute('aria-current', 'page');
                
                // 상세 페이지(master_detail.html)에서 다른 메뉴 클릭 시 /master 로 이동
                if (detailDashboardView && menu !== 'partners') {
                    return;
                }
                
                e.preventDefault();
                currentActiveMenu = menu;

                // 사이드바 active 갱신
                sidebarMenuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');

                // 모든 마스터 카드 및 mock 뷰 숨김/제거
                masterMainContent.querySelectorAll('.master-card').forEach(card => {
                    card.style.display = 'none';
                });
                const activeMocks = masterMainContent.querySelectorAll('.mock-dashboard');
                activeMocks.forEach(m => m.remove());

                // 1. [대시보드 홈]
                if (menu === 'home') {
                    const homeView = document.getElementById('home-dashboard-view');
                    if (homeView) {
                        homeView.style.display = 'block';
                        console.log('[RENDER] 대시보드 홈 UI 컴포넌트 렌더링 완료');
                    }
                    return;
                }

                // 2. [파트너사 관리]
                if (menu === 'partners') {
                    const partnersView = document.getElementById('partners-dashboard-view') || document.getElementById('home-dashboard-view');
                    if (partnersView) {
                        partnersView.style.display = 'block';
                        console.log('[RENDER] 파트너사 관리 뷰 렌더링 완료');
                    }
                    return;
                }

                // 3. [회계감사] (기존 finance-inquiry 포함)
                if (menu === 'audit' || menu === 'finance-inquiry') {
                    const auditView = document.getElementById('audit-dashboard-view') || document.getElementById('finance-dashboard-view');
                    if (auditView) {
                        auditView.style.display = 'block';
                        console.log('[RENDER] 회계감사 관리 뷰 렌더링 완료');
                    }
                    return;
                }

                // 4. [세무 일정 캘린더]
                if (menu === 'calendar') {
                    const calendarDashboardView = document.getElementById('calendar-dashboard-view');
                    if (calendarDashboardView) {
                        calendarDashboardView.style.display = 'block';
                        window.loadNotionCalendar?.();
                        console.log('[RENDER] 세무 일정 캘린더 렌더링 완료');
                    }
                    return;
                }

                // 5. [기업 정밀 분석 허브]
                if (menu === 'analytics-hub') {
                    const hubView = document.getElementById('analytics-hub-view');
                    if (hubView) {
                        hubView.style.display = 'block';
                        window.initAnalyticsHub?.();
                        console.log('[RENDER] 기업 정밀 분석 허브 렌더링 완료');
                    }
                    return;
                }

                // 6. [시스템 통계 및 리포트]
                if (menu === 'analytics') {
                    const analyticsDashboardView = document.getElementById('analytics-dashboard-view');
                    if (analyticsDashboardView) {
                        analyticsDashboardView.style.display = 'block';
                        console.log('[RENDER] 시스템 통계 리포트 렌더링 완료');
                    }
                    return;
                }

                // 7. 기타 Mock 화면 렌더링
                const data = menuMockData[menu];
                if (data) {
                    const mockHtml = `
                        <div class="mock-dashboard">
                            <header class="mock-header">
                                <h1 class="mock-title">${data.title}</h1>
                            </header>
                            
                            <div class="glass-card dashboard-card master-card mock-placeholder-card" style="display:block;">
                                <span class="mock-placeholder-icon">${data.icon}</span>
                                <h3 class="mock-placeholder-title">${data.placeholder}</h3>
                                <p class="mock-placeholder-desc">${data.desc}</p>
                                <div class="status-badge" style="background: rgba(167, 139, 250, 0.08); border-color: rgba(167, 139, 250, 0.2); color: #a78bfa; margin-top: 10px; margin-bottom: 0;">
                                    <span class="pulse-dot" style="background: #a78bfa; box-shadow: 0 0 0 0 rgba(167, 139, 250, 0.4);"></span>
                                    <span>회계법인 혜안 통합 포털에서 제공 중인 기능입니다</span>
                                </div>
                            </div>
                        </div>
                    `;
                    masterMainContent.insertAdjacentHTML('beforeend', mockHtml);
                    console.log(`[RENDER] Mock View (${menu}) 렌더링 완료`);
                }
            });
        });
    }
});

// ==========================================
// [Step 6] 파트너사 관리 > 업무 요청 관리 모듈 로직
// ==========================================
let allMasterRequestsCache = [];
let currentRequestStatusFilter = '';

window.loadMasterRequests = async function() {
    const tbody = document.getElementById('master-requests-tbody');
    if (!tbody) return;

    try {
        console.log('[REQUEST] GET /api/requests 요청 전송 (모든 파트너사 업무 요청 목록)');
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: var(--text-secondary);">
                    <span class="pulse-dot" style="display:inline-block; margin-right:6px;"></span>
                    데이터를 실시간 동기화 중입니다...
                </td>
            </tr>
        `;

        const res = await fetch('/api/requests');
        const data = await res.json();
        
        if (!res.ok || !data.success) {
            throw new Error(data.error || '요청 목록을 불러오지 못했습니다.');
        }

        allMasterRequestsCache = data.requests || [];
        console.log(`[RENDER] 업무 요청 데이터 ${allMasterRequestsCache.length}건 수신 완료`);
        renderMasterRequestsTable();
    } catch (err) {
        console.error('[ERROR] 업무 요청 목록 로딩 실패:', err);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: #f87171;">
                    ⚠️ 데이터를 불러오는 중 오류가 발생했습니다: ${err.message}
                </td>
            </tr>
        `;
    }
};

window.filterMasterRequests = function(status) {
    currentRequestStatusFilter = status;
    console.log(`[ACTION] 업무 요청 상태 필터 변경 -> '${status || '전체'}'`);
    
    // 필터 버튼 active 상태 갱신
    document.querySelectorAll('.btn-filter-req').forEach(btn => {
        if ((status === '' && btn.textContent.trim() === '전체') || btn.textContent.trim() === status) {
            btn.classList.add('active');
            btn.style.background = 'rgba(99,102,241,0.2)';
            btn.style.borderColor = 'rgba(99,102,241,0.4)';
            btn.style.color = '#fff';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'rgba(255,255,255,0.05)';
            btn.style.borderColor = 'rgba(255,255,255,0.1)';
            btn.style.color = 'var(--text-secondary)';
        }
    });

    renderMasterRequestsTable();
};

function renderMasterRequestsTable() {
    const tbody = document.getElementById('master-requests-tbody');
    if (!tbody) return;

    let filtered = allMasterRequestsCache;
    if (currentRequestStatusFilter) {
        filtered = filtered.filter(item => {
            const st = (item.status || '대기중').trim();
            return st === currentRequestStatusFilter;
        });
    }

    // 대기 건수 배지 갱신
    const pendingCount = allMasterRequestsCache.filter(item => (item.status || '대기중') === '대기중').length;
    const reqBadge = document.getElementById('partner-requests-badge');
    if (reqBadge) reqBadge.textContent = pendingCount;

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 30px; color: var(--text-secondary);">
                    조회된 업무 요청 내역이 없습니다.
                </td>
            </tr>
        `;
        return;
    }

    const statusColors = {
        '대기중': 'background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3);',
        '확인중': 'background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3);',
        '승인완료': 'background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);',
        '반려': 'background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);'
    };

    tbody.innerHTML = filtered.map(req => {
        const curStatus = req.status || '대기중';
        const stStyle = statusColors[curStatus] || 'background: rgba(255,255,255,0.05); color: #e2e8f0;';
        const dateStr = req.created_at ? req.created_at.slice(0, 10) : '-';
        const fileLink = req.file_url ? 
            `<a href="${req.file_url}" target="_blank" class="partner-link" style="font-size:0.85rem;">📥 다운로드</a>` : 
            `<span style="color:var(--text-secondary); font-size:0.8rem;">-</span>`;

        return `
            <tr>
                <td class="col-date">${dateStr}</td>
                <td class="col-company">
                    <strong>${req.company_name || '-'}</strong>
                </td>
                <td>${req.file_name || req.category || '기본 서류'}</td>
                <td>
                    <span style="display:inline-block; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; ${stStyle}">
                        ${curStatus}
                    </span>
                </td>
                <td>${fileLink}</td>
                <td>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <button type="button" class="btn-logout" onclick="updateMasterRequestStatus('${req.id}', '승인완료')" style="padding: 3px 8px; font-size: 0.78rem; background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.3); color: #34d399;">승인</button>
                        <button type="button" class="btn-logout" onclick="updateMasterRequestStatus('${req.id}', '확인중')" style="padding: 3px 8px; font-size: 0.78rem; background: rgba(99,102,241,0.1); border-color: rgba(99,102,241,0.3); color: #818cf8;">확인중</button>
                        <button type="button" class="btn-logout" onclick="updateMasterRequestStatus('${req.id}', '반려')" style="padding: 3px 8px; font-size: 0.78rem; background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.3); color: #f87171;">반려</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    console.log(`[RENDER] 업무 요청 테이블 렌더링 완료 (${filtered.length}건 표시)`);
}

window.updateMasterRequestStatus = async function(requestId, newStatus) {
    if (!requestId) return;
    
    console.log(`[ACTION] 업무 요청 상태 변경 시도 (ID: ${requestId} -> ${newStatus})`);
    
    try {
        console.log(`[REQUEST] POST /api/requests/update-status (id: ${requestId}, status: ${newStatus})`);
        const res = await fetch('/api/requests/update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: requestId, status: newStatus })
        });
        
        const result = await res.json();
        if (!res.ok || !result.success) {
            throw new Error(result.error || '상태 변경에 실패했습니다.');
        }

        console.log(`[ACTION] 업무 요청 상태 변경 성공 (ID: ${requestId} -> ${newStatus})`);
        
        // 캐시 업데이트 및 재렌더링
        const target = allMasterRequestsCache.find(r => String(r.id) === String(requestId));
        if (target) target.status = newStatus;
        renderMasterRequestsTable();
    } catch (err) {
        console.error('[ERROR] 업무 요청 상태 업데이트 오류:', err);
        alert(`상태 변경 중 오류가 발생했습니다: ${err.message}`);
    }
};

// 파트너사 관리 탭 진입 시 초기 요청 목록 로드 트리거
document.addEventListener('click', (e) => {
    const subtabBtn = e.target.closest('.master-subtab-btn[data-subtab="subtab-partner-requests"]');
    if (subtabBtn) {
        window.loadMasterRequests();
    }
});

// ==========================================
// [Step 7] 파트너사 관리 > 공지 및 알림 관리 모듈 로직
// ==========================================
let allMasterNoticesCache = [];

window.loadMasterNotices = async function() {
    const tbody = document.getElementById('master-notices-tbody');
    if (!tbody) return;

    try {
        console.log('[REQUEST] GET /api/notices (공지 및 알림 목록 조회)');
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: var(--text-secondary);">
                    <span class="pulse-dot" style="display:inline-block; margin-right:6px;"></span>
                    공지 데이터를 실시간 동기화 중입니다...
                </td>
            </tr>
        `;

        const res = await fetch('/api/notices');
        const data = await res.json();

        if (!res.ok || !data.success) {
            throw new Error(data.error || '공지 목록을 불러오지 못했습니다.');
        }

        allMasterNoticesCache = data.notices || [];
        console.log(`[RENDER] 공지 및 알림 데이터 ${allMasterNoticesCache.length}건 수신 완료`);
        renderMasterNoticesTable();
    } catch (err) {
        console.error('[ERROR] 공지 목록 로딩 실패:', err);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: #f87171;">
                    ⚠️ 공지 내역을 불러오지 못했습니다: ${err.message}
                </td>
            </tr>
        `;
    }
};

function renderMasterNoticesTable() {
    const tbody = document.getElementById('master-notices-tbody');
    if (!tbody) return;

    if (allMasterNoticesCache.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 30px; color: var(--text-secondary);">
                    등록된 공지 및 알림 내역이 없습니다.
                </td>
            </tr>
        `;
        return;
    }

    const badgeStyles = {
        'urgent': 'background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);',
        'popup': 'background: rgba(167, 139, 250, 0.15); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.3);',
        'normal': 'background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3);'
    };
    const badgeLabels = { 'urgent': '🚨 긴급', 'popup': '🔔 팝업', 'normal': '📢 일반' };

    tbody.innerHTML = allMasterNoticesCache.map(notice => {
        const imp = notice.importance || 'normal';
        const stStyle = badgeStyles[imp] || badgeStyles.normal;
        const impLabel = badgeLabels[imp] || '📢 일반';
        const targetLabel = notice.target_company_name || (notice.target_company === 'all' ? '전체 파트너사' : notice.target_company);
        const dateStr = notice.created_at || '-';

        return `
            <tr>
                <td class="col-date">${dateStr}</td>
                <td><strong>${targetLabel}</strong></td>
                <td>
                    <span style="display:inline-block; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; ${stStyle}">
                        ${impLabel}
                    </span>
                </td>
                <td><strong>${notice.title || '-'}</strong></td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); font-size: 0.85rem;">
                    ${notice.content || '-'}
                </td>
                <td>
                    <button type="button" class="btn-logout" onclick="deleteMasterNotice('${notice.id}')" style="padding: 3px 8px; font-size: 0.78rem; background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.3); color: #f87171;">삭제</button>
                </td>
            </tr>
        `;
    }).join('');

    console.log(`[RENDER] 공지 및 알림 테이블 렌더링 완료 (${allMasterNoticesCache.length}건 표시)`);
}

window.handleSendMasterNotice = async function(event) {
    event.preventDefault();

    const titleInput = document.getElementById('notice-input-title');
    const targetInput = document.getElementById('notice-input-target');
    const impInput = document.getElementById('notice-input-importance');
    const contentInput = document.getElementById('notice-input-content');
    const submitBtn = document.getElementById('btn-submit-notice');

    const payload = {
        title: titleInput.value.trim(),
        target_company: targetInput.value,
        importance: impInput.value,
        content: contentInput.value.trim()
    };

    console.log('[ACTION] 공지 및 알림 발송 시도:', payload);

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.7';
        }

        console.log('[REQUEST] POST /api/notices 요청 전송');
        const res = await fetch('/api/notices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        if (!res.ok || !result.success) {
            throw new Error(result.error || '공지 발송에 실패했습니다.');
        }

        console.log('[ACTION] 공지 및 알림 발송 성공:', result.notice);
        alert('공지 및 알림이 성공적으로 등록/발송되었습니다.');

        // 폼 초기화 및 목록 갱신
        titleInput.value = '';
        contentInput.value = '';
        allMasterNoticesCache.unshift(result.notice);
        renderMasterNoticesTable();
    } catch (err) {
        console.error('[ERROR] 공지 발송 오류:', err);
        alert(`공지 발송 중 오류가 발생했습니다: ${err.message}`);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
        }
    }
};

window.deleteMasterNotice = async function(noticeId) {
    if (!noticeId || !confirm('이 공지사항을 삭제하시겠습니까?')) return;

    console.log(`[ACTION] 공지 삭제 시도 (ID: ${noticeId})`);

    try {
        console.log(`[REQUEST] DELETE /api/notices/${noticeId}`);
        const res = await fetch(`/api/notices/${noticeId}`, { method: 'DELETE' });
        const result = await res.json();

        if (!res.ok || !result.success) {
            throw new Error(result.error || '공지 삭제에 실패했습니다.');
        }

        console.log(`[ACTION] 공지 삭제 완료 (ID: ${noticeId})`);
        allMasterNoticesCache = allMasterNoticesCache.filter(n => String(n.id) !== String(noticeId));
        renderMasterNoticesTable();
    } catch (err) {
        console.error('[ERROR] 공지 삭제 오류:', err);
        alert(`삭제 중 오류가 발생했습니다: ${err.message}`);
    }
};

// 공지/알림 서브탭 클릭 시 데이터 로드 트리거
document.addEventListener('click', (e) => {
    const subtabBtn = e.target.closest('.master-subtab-btn[data-subtab="subtab-partner-notices"]');
    if (subtabBtn) {
        window.loadMasterNotices();
    }
});

// ==========================================
// [Step 10] 파트너사 문서함 기업 검색 필터 함수
// ==========================================
window.filterPartnerDocs = function(keyword) {
    const term = (keyword || '').toLowerCase().trim();
    const rows = document.querySelectorAll('#partner-docs-table .partner-doc-row');
    rows.forEach(row => {
        const company = row.getAttribute('data-company') || '';
        if (!term || company.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
};

// PWA Service Worker Registration & Install Prompt Logic
let deferredPrompt = null;

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('PWA ServiceWorker registered with scope: ', registration.scope);
            })
            .catch(err => {
                console.warn('PWA ServiceWorker registration failed: ', err);
            });
    });
}

// Handle PWA Install Prompt for Mobile & Desktop
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // Check if user already dismissed install banner in this session
    if (sessionStorage.getItem('pwa-dismissed')) {
        return;
    }

    // Create & Inject Install Banner if not exists
    let banner = document.getElementById('pwa-install-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-banner-icon">✨</div>
            <div class="pwa-banner-text">
                <div class="pwa-banner-title">혜안 앱 설치하기</div>
                <div class="pwa-banner-desc">스마트폰 홈 화면에서 앱처럼 편리하게 이용하세요</div>
            </div>
            <div class="pwa-banner-actions">
                <button class="pwa-btn-install" id="pwa-btn-install-trigger">설치</button>
                <button class="pwa-btn-close" id="pwa-btn-install-close" aria-label="닫기">✕</button>
            </div>
        `;
        document.body.appendChild(banner);

        const installBtn = document.getElementById('pwa-btn-install-trigger');
        const closeBtn = document.getElementById('pwa-btn-install-close');

        if (installBtn) {
            installBtn.addEventListener('click', async () => {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    console.log(`PWA install choice: ${outcome}`);
                    deferredPrompt = null;
                }
                banner.classList.remove('show');
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                banner.classList.remove('show');
                sessionStorage.setItem('pwa-dismissed', 'true');
            });
        }
    }

    // Trigger animation
    setTimeout(() => {
        banner.classList.add('show');
    }, 1500);
});

window.addEventListener('appinstalled', () => {
    console.log('PWA was successfully installed.');
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.remove('show');
    deferredPrompt = null;
});

// ==========================================
// Master Portal Sub-tabs & Pipeline Interactions
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const subTabBtns = document.querySelectorAll('.sub-tab-btn');
    const metricsView = document.getElementById('subtab-metrics-view');
    const pipelineView = document.getElementById('subtab-pipeline-view');

    if (subTabBtns.length > 0 && metricsView && pipelineView) {
        subTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                subTabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const subtab = btn.getAttribute('data-subtab');
                if (subtab === 'metrics') {
                    metricsView.style.display = 'block';
                    pipelineView.style.display = 'none';
                } else {
                    metricsView.style.display = 'none';
                    pipelineView.style.display = 'block';
                }
            });
        });
    }
});

// Accordion Toggle for Pipeline Cards
window.toggleNodeDetails = (stepId) => {
    const details = document.getElementById(`details-${stepId}`);
    const card = document.getElementById(`node-${stepId}`);
    if (details && card) {
        if (details.style.display === 'none') {
            details.style.display = 'block';
            card.classList.add('expanded');
        } else {
            details.style.display = 'none';
            card.classList.remove('expanded');
        }
    }
};

// Mock Ping Connection Test
window.runPingTest = (stepId) => {
    const indicator = document.getElementById(`ping-res-${stepId}`);
    if (indicator) {
        indicator.textContent = '🔌 연결 테스트 중...';
        indicator.style.color = '#a78bfa';
        indicator.className = 'test-result-indicator pinging';
        
        setTimeout(() => {
            indicator.className = 'test-result-indicator';
            if (stepId === 'p1') {
                indicator.textContent = '✓ 연결 성공 (n8n Webhook OK - HTTP 200)';
                indicator.style.color = '#10b981';
            } else if (stepId === 'p3') {
                indicator.textContent = '✓ 인증 성공 (Dify API Key Active)';
                indicator.style.color = '#10b981';
            } else {
                indicator.textContent = '⚠ 연결 실패 (인증 정보가 비어 있거나 유효하지 않습니다)';
                indicator.style.color = '#ef4444';
            }
        }, 1200);
    }
};

// ==========================================
// Partner Portal Sidebar Interactions
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const partnerMenuItems = document.querySelectorAll('.master-menu-item[data-menu^="partner-"]');
    const partnerViews = [
        'partner-home-view',
        'partner-history-view',
        'partner-inquiry-view',
        'partner-consulting-view',
        'partner-billing-view',
        'partner-settings-view'
    ];

    if (partnerMenuItems.length > 0) {
        partnerMenuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const menu = item.getAttribute('data-menu');
                
                // 사이드바 active 클래스 토글
                partnerMenuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                
                // 모든 파트너 뷰 숨기기
                partnerViews.forEach(viewId => {
                    const viewEl = document.getElementById(viewId);
                    if (viewEl) viewEl.style.display = 'none';
                });
                
                // 선택한 뷰 보이기
                const targetView = document.getElementById(menu + '-view');
                if (targetView) {
                    targetView.style.display = 'block';
                    if (menu === 'partner-consulting' && typeof window.loadClientCompanyChat === 'function') {
                        window.loadClientCompanyChat();
                    }
                }
            });
        });
    }
});

// ==========================================
// Master Portal Task Filter Interaction
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const taskFilter = document.getElementById('task-filter');
    const partnerRows = document.querySelectorAll('.partner-row');
    const visibleCountEl = document.getElementById('visible-partner-count');

    if (taskFilter && partnerRows.length > 0) {
        taskFilter.addEventListener('change', (e) => {
            const selectedTask = e.target.value;
            let visibleCount = 0;
            
            partnerRows.forEach(row => {
                const rowTask = row.getAttribute('data-task');
                if (selectedTask === 'all' || rowTask === selectedTask || (selectedTask === '기타' && !['회계감사', '세무자문', '기장대리'].includes(rowTask))) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            if (visibleCountEl) {
                visibleCountEl.textContent = visibleCount;
            }
        });
    }
});

// ==========================================
// Drag and Drop & Multiple File Upload Logic
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const uploadBoxes = document.querySelectorAll('.mini-upload-box');

    uploadBoxes.forEach(box => {
        const input = box.querySelector('input[type="file"]');
        const labelText = box.querySelector('.file-text');

        if (!input || !labelText) return;

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            box.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            box.addEventListener(eventName, () => {
                box.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            box.addEventListener(eventName, () => {
                box.classList.remove('dragover');
            }, false);
        });

        // Handle dropped files
        box.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files && files.length > 0) {
                input.files = files;
                updateLabelText(input.files, labelText);
            }
        });

        // Handle selected files via click
        input.addEventListener('change', (e) => {
            updateLabelText(input.files, labelText);
        });
        
        function updateLabelText(files, label) {
            if (files.length > 1) {
                label.textContent = `${files.length}개 파일 선택됨`;
            } else if (files.length === 1) {
                label.textContent = files[0].name;
            } else {
                label.textContent = '파일 선택';
            }
        }
    });
});

// ==========================================
// AI FAQ Chat Logic
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('btn-faq-submit');
    const inputArea = document.getElementById('faq-question-input');
    const categorySelect = document.getElementById('faq-category-select');
    const messagesContainer = document.getElementById('faq-chat-messages');

    if (submitBtn && inputArea && messagesContainer) {
        let currentConversationId = "";
        
        // Enter 키로도 전송 (Shift+Enter는 줄바꿈)
        inputArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitBtn.click();
            }
        });

        submitBtn.addEventListener('click', async () => {
            const question = inputArea.value.trim();
            const category = categorySelect ? categorySelect.value : '전체';

            if (!question) return;

            // 1. 유저 메시지 화면에 추가
            appendMessage('user', question);
            inputArea.value = '';
            
            // 2. 로딩 애니메이션 추가
            const loadingId = 'loading-' + Date.now();
            appendLoading(loadingId);
            
            // 스크롤 맨 아래로
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            try {
                // 3. 백엔드 API 호출
                const response = await fetch('/api/faq/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question, category, conversation_id: currentConversationId })
                });

                // 4. 로딩 애니메이션 제거
                const loadingEl = document.getElementById(loadingId);
                if (loadingEl) loadingEl.remove();

                if (!response.ok) {
                    appendMessage('ai', '오류가 발생했습니다: 서버 에러');
                    return;
                }

                // 5. 스트리밍(SSE) 읽기
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let fullText = '';
                const contentP = appendMessage('ai', '', []);

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.substring(6).trim();
                            if (!dataStr) continue;
                            try {
                                const data = JSON.parse(dataStr);
                                if (data.event === 'message' || data.event === 'agent_message') {
                                    fullText += data.answer;
                                    if (contentP) {
                                        contentP.innerHTML = typeof marked !== 'undefined' ? marked.parse(fullText) : fullText.replace(/\n/g, '<br>');
                                    }
                                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                                }
                                if (data.conversation_id) {
                                    currentConversationId = data.conversation_id;
                                }
                            } catch (e) {
                                // JSON 파싱 에러 무시
                            }
                        }
                    }
                }

            } catch (error) {
                const loadingEl = document.getElementById(loadingId);
                if (loadingEl) loadingEl.remove();
                appendMessage('ai', '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            }

            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });

        function appendMessage(role, text, sources = []) {
            const bubble = document.createElement('div');
            bubble.className = `chat-bubble ${role}-bubble`;
            
            let avatar = role === 'ai' ? '🤖' : 'P';
            let formattedText = '';
            if (text) {
                formattedText = (role === 'ai' && typeof marked !== 'undefined') ? marked.parse(text) : text.replace(/\n/g, '<br>');
            }
            
            let sourcesHtml = '';
            if (sources && sources.length > 0) {
                sourcesHtml = '<div class="faq-sources"><div class="faq-sources-title">참조 기준:</div>';
                sources.forEach(src => {
                    sourcesHtml += `<span class="faq-source-tag">${src}</span>`;
                });
                sourcesHtml += '</div>';
            }

            bubble.innerHTML = `
                <div class="bubble-avatar">${avatar}</div>
                <div class="bubble-content">
                    <div class="message-text-container">${formattedText}</div>
                    ${sourcesHtml}
                </div>
            `;
            messagesContainer.appendChild(bubble);
            return bubble.querySelector('.message-text-container');
        }

        function appendLoading(id) {
            const bubble = document.createElement('div');
            bubble.className = `chat-bubble ai-bubble`;
            bubble.id = id;
            bubble.innerHTML = `
                <div class="bubble-avatar">🤖</div>
                <div class="bubble-content">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            messagesContainer.appendChild(bubble);
        }
    }
});

//   ȯ  (ȸ谨  )
window.switchSubTab = function(tabId) {
    //  ư Ȱȭ 
    document.querySelectorAll('.sub-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if(btn.dataset.subtab === tabId) btn.classList.add('active');
    });
    
    //   ü 
    document.querySelectorAll('.sub-tab-pane').forEach(pane => {
        pane.style.display = 'none';
        if(pane.id === tabId) pane.style.display = 'block';
    });
};


// ==========================================
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
                <td>${isPaper ? '서면조회' : '전자조회'}</td>
                <td><span class="status-badge" style="background: rgba(99,102,241,0.1); color: #818cf8; padding: 4px 8px;">${statusStr}</span></td>
                <td>${actionBtn}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // 마법사 열기
        window.showInquiryWizard = function() {
        const financeDashboard = document.getElementById('ext-finance-dashboard');
        const financeWizard = document.getElementById('ext-finance-wizard');
        financeDashboard.style.display = 'none';
        financeWizard.style.display = 'block';
        
        // 폼 초기화
        document.getElementById('bank-search-input').value = '';
        document.querySelector('input[name="inquiry_type_filter"][value="all"]').checked = true;
        document.getElementById('bank-search-results').innerHTML = '';
        
        const detailsForm = document.getElementById('application-details-form');
        if (detailsForm) detailsForm.style.display = 'none';
        
        searchBanks();
    };

    window.hideInquiryWizard = function() {
        financeWizard.style.display = 'none';
        financeDashboard.style.display = 'block';
        loadInquiryStatus();
    };

    window.searchBanks = function() {
        const query = document.getElementById('bank-search-input').value.trim();
        const filterEl = document.querySelector('input[name="inquiry_type_filter"]:checked');
        const filterType = filterEl ? filterEl.value : 'all';
        const resultsDiv = document.getElementById('bank-search-results');
        resultsDiv.innerHTML = '';
        const detailsForm = document.getElementById('application-details-form');
        if (detailsForm) detailsForm.style.display = 'none';
        resultsDiv.style.display = 'grid';
        
        const banner = document.getElementById('online-redirect-banner');
        const searchContainer = document.getElementById('bank-search-container');
        const helpTextContainer = document.getElementById('help-text-container');
        
        const paperBox = document.getElementById('paper-guide-box');
        
        if (filterType === 'online') {
            if (banner) banner.style.display = 'block';
            if (paperBox) paperBox.style.display = 'none';
            if (searchContainer) searchContainer.style.display = 'none';
            if (helpTextContainer) helpTextContainer.style.display = 'none';
            return;
        } else if (filterType === 'paper') {
            if (banner) banner.style.display = 'none';
            if (paperBox) paperBox.style.display = 'block';
            if (searchContainer) searchContainer.style.display = 'none';
            if (helpTextContainer) helpTextContainer.style.display = 'none';
            return;
        } else {
            if (banner) banner.style.display = 'none';
            if (paperBox) paperBox.style.display = 'none';
            if (searchContainer) searchContainer.style.display = 'block';
            if (helpTextContainer) helpTextContainer.style.display = 'block';
        }

        const filtered = allBanks.filter(b => {
            const matchName = b.institution_name.includes(query) || b.institution_code.includes(query);
            const matchType = (filterType === 'all') || (b.inquiry_type === filterType);
            return matchName && matchType;
        });
        
        if(filtered.length === 0) {
            resultsDiv.innerHTML = '<p style="color: var(--text-secondary);">검색 결과가 없습니다.</p>';
            return;
        }

        filtered.forEach(b => {
            const div = document.createElement('div');
            div.style.cssText = 'padding: 15px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; transition: all 0.2s;';
            div.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">${b.institution_name}</div>
                <div style="font-size: 0.8rem; color: #a78bfa;">[${b.institution_code}] ${b.inquiry_type === 'online' ? '전자조회' : '서면조회'}</div>
            `;
            div.onmouseover = () => div.style.borderColor = '#818cf8';
            div.onmouseout = () => div.style.borderColor = 'rgba(255,255,255,0.1)';
            div.onclick = () => window.selectBank(b);
            resultsDiv.appendChild(div);
        });
    };

    // 은행 선택
    window.selectBank = function(bank) {
        document.getElementById('selected-bank-id').value = bank.id;
        document.getElementById('selected-bank-type').value = bank.inquiry_type;
        document.getElementById('selected-bank-name').textContent = `${bank.institution_name} (${bank.inquiry_type === 'online' ? '전자조회' : '서면조회'})`;
        
        document.getElementById('bank-search-results').style.display = 'none';
        document.getElementById('application-details-form').style.display = 'block';
        
        if(bank.inquiry_type === 'online') {
            document.getElementById('online-guide-box').style.display = 'block';
        } else {
            document.getElementById('online-guide-box').style.display = 'none';
        }
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
                alert(`신청이 완료되었습니다.\n요청번호: ${data.request_id}`);
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
// 관리자 (Admin) - 회계감사 & 금융기관 외부조회 신청 관리
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const adminAuditMenu = document.querySelector('.master-menu-item[data-menu="audit"]') || 
                           document.querySelector('.master-menu-item[data-menu="finance-inquiry"]');
    const adminAuditView = document.getElementById('audit-dashboard-view') || 
                           document.getElementById('finance-inquiry-view');
    const homeDashboardView = document.getElementById('home-dashboard-view');
    
    if (adminAuditMenu && adminAuditView) {
        adminAuditMenu.addEventListener('click', (e) => {
            e.preventDefault();
            const allCards = document.querySelectorAll('.master-card');
            allCards.forEach(c => c.style.display = 'none');
            document.querySelectorAll('.mock-dashboard').forEach(view => view.remove());
            
            const allMenus = document.querySelectorAll('.master-menu-item');
            allMenus.forEach(m => m.classList.remove('active'));
            
            adminAuditView.style.display = 'block';
            adminAuditMenu.classList.add('active');
            
            console.log('[ACTION] 회계감사 탭 클릭 -> 금융기관 조회 데이터 로딩 시작');
            window.loadAdminInquiryStatus?.();
        });
        
        const homeMenu = document.querySelector('.master-menu-item[data-menu="home"]');
        if (homeMenu) {
            homeMenu.addEventListener('click', () => {
                if (adminAuditView) adminAuditView.style.display = 'none';
                if (homeDashboardView) homeDashboardView.style.display = 'block';
            });
        }
        
        // 수수료 및 청구 관리 (Billing) 뷰 확장
        const adminBillingMenu = document.querySelector('.master-menu-item[data-menu="billing"]');
        const adminBillingView = document.getElementById('billing-dashboard-view');
        
        if (adminBillingMenu && adminBillingView) {
            adminBillingMenu.addEventListener('click', (e) => {
                e.preventDefault();
                const allCards = document.querySelectorAll('.master-card');
                allCards.forEach(c => c.style.display = 'none');
                document.querySelectorAll('.mock-dashboard').forEach(view => view.remove());
                
                const allMenus = document.querySelectorAll('.master-menu-item');
                allMenus.forEach(m => m.classList.remove('active'));
                
                adminBillingView.style.display = 'block';
                adminBillingMenu.classList.add('active');
                
                window.loadBillingDocs();
            });
            
            if(homeMenu) {
                homeMenu.addEventListener('click', () => {
                    if(adminBillingView) adminBillingView.style.display = 'none';
                });
            }
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
            let msg = `[요청 ID: ${requestId}] 진행 이력\n\n`;
            data.forEach(h => {
                msg += `- ${h.created_at}: ${h.previous_status} -> ${h.new_status} (${h.changed_by})\n`;
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


    // PDF 생성 기능
    window.generatePDF = async function() {
        const formType = document.getElementById('pdf-form-type').value;
        const bankName = document.getElementById('pdf-bank-name').value || '';
        const branchName = document.getElementById('pdf-branch-name').value || '';
        
        // 새로운 회계법인 및 환급계좌 정보
        const cpaFirm = document.getElementById('pdf-cpa-firm') ? document.getElementById('pdf-cpa-firm').value : '';
        const cpaBiznum = document.getElementById('pdf-cpa-biznum') ? document.getElementById('pdf-cpa-biznum').value : '';
        const cpaName = document.getElementById('pdf-cpa-name') ? document.getElementById('pdf-cpa-name').value : '';
        const cpaPhone = document.getElementById('pdf-cpa-phone') ? document.getElementById('pdf-cpa-phone').value : '';
        const cpaFax = document.getElementById('pdf-cpa-fax') ? document.getElementById('pdf-cpa-fax').value : '';
        const cpaEmail = document.getElementById('pdf-cpa-email') ? document.getElementById('pdf-cpa-email').value : '';
        const refundBank = document.getElementById('pdf-refund-bank') ? document.getElementById('pdf-refund-bank').value : '';
        const refundOwner = document.getElementById('pdf-refund-owner') ? document.getElementById('pdf-refund-owner').value : '';
        const refundAccount = document.getElementById('pdf-refund-account') ? document.getElementById('pdf-refund-account').value : '';
        
        const companyName = document.getElementById('pdf-company-name').value || '';
        const ceoName = document.getElementById('pdf-ceo-name').value || '';
        
        const inquiryDateStr = document.getElementById('pdf-inquiry-date').value;
        const baseDateStr = document.getElementById('pdf-base-date').value;
        
        const targetStartStr = document.getElementById('pdf-target-start') ? document.getElementById('pdf-target-start').value : '';
        const targetEndStr = document.getElementById('pdf-target-end') ? document.getElementById('pdf-target-end').value : '';
        
        let iYear = '20__', iMonth = '__', iDay = '__';
        if(inquiryDateStr) {
            const d = new Date(inquiryDateStr);
            iYear = d.getFullYear(); iMonth = (d.getMonth() + 1).toString().padStart(2, '0'); iDay = d.getDate().toString().padStart(2, '0');
        }
        
        let bYear = '20__', bMonth = '__', bDay = '__';
        let eYear = '20__', eMonth = '__', eDay = '__';
        
        if(baseDateStr) {
            const d = new Date(baseDateStr);
            bYear = d.getFullYear(); bMonth = (d.getMonth() + 1).toString().padStart(2, '0'); bDay = d.getDate().toString().padStart(2, '0');
            
            // 요구서 유효기간: 조회기준일로부터 3개월 후
            const ed = new Date(baseDateStr);
            ed.setMonth(ed.getMonth() + 3);
            eYear = ed.getFullYear(); eMonth = (ed.getMonth() + 1).toString().padStart(2, '0'); eDay = ed.getDate().toString().padStart(2, '0');
        }
        
        let targetPeriod = '';
        if (targetStartStr && targetEndStr) {
            targetPeriod = `${targetStartStr.replace(/-/g, '.')} ~ ${targetEndStr.replace(/-/g, '.')}`;
        }

        try {
            const btn = document.querySelector('.btn-submit');
            let originalBtnText = "[PDF 다운로드]";
            if(btn) {
                originalBtnText = btn.textContent;
                btn.textContent = "서식 생성 중...";
                btn.disabled = true;
            }

            const response = await fetch(`/static/pdf_templates/${encodeURIComponent(formType)}.html`);
            if(!response.ok) throw new Error("Template not found");
            const htmlText = await response.text();
            
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');
            
            let fields = {
                'p-bank-name': bankName, 'p-branch-name': branchName,
                'p-current-year': iYear, 'p-current-month': iMonth, 'p-current-day': iDay,
                
                // 페이지 1 CPA 및 환급정보
                'p-cpa-firm': cpaFirm,
                'p-cpa-biznum': cpaBiznum,
                'p-cpa-name': cpaName,
                'p-cpa-phone': cpaPhone,
                'p-cpa-fax': cpaFax,
                'p-cpa-email': cpaEmail,
                'p-refund-bank': refundBank,
                'p-refund-owner': refundOwner,
                'p-refund-account': refundAccount,
                
                'p-company-name': companyName, 'p-ceo-name': ceoName,
                'p2-bank-name': bankName, 'p2-branch-name': branchName,
                'p2-current-year': iYear, 'p2-current-month': iMonth, 'p2-current-day': iDay,
                'p2-cpa-firm': cpaFirm, 
                'p2-company-name': companyName, 'p2-ceo-name': ceoName,
                'p2-company-name-sign': companyName,
                
                'p-base-year': bYear, 'p-base-month': bMonth, 'p-base-day': bDay,
                
                // 만료일
                'p-expire-year': eYear, 'p-expire-month': eMonth, 'p-expire-day': eDay,
                'p-target-period': targetPeriod
            };
            
            // 3~8페이지 상단 (t1~t6, index 1~6)
            for(let i=1; i<=6; i++) {
                fields[`p3-cpa-firm-top-${i}`] = cpaFirm;
                fields[`p3-company-name-${i}`] = companyName;
                fields[`p3-base-year-${i}`] = bYear;
                fields[`p3-base-month-${i}`] = bMonth;
                fields[`p3-base-day-${i}`] = bDay;
            }
            
            for (const [id, val] of Object.entries(fields)) {
                const els = doc.querySelectorAll('#' + id);
                els.forEach(el => {
                    if(el) el.textContent = val;
                });
            }
            
            const finalHtmlString = doc.documentElement.outerHTML;
            
            const printWindow = window.open('', '_blank');
            if (printWindow) {
                printWindow.document.open();
                printWindow.document.write(finalHtmlString);
                printWindow.document.close();
            } else {
                alert("팝업 차단이 설정되어 있습니다. 팝업 차단을 해제한 후 다시 시도해 주세요.");
            }
            
            if(btn) {
                btn.textContent = originalBtnText;
                btn.disabled = false;
            }
            
        } catch(e) {
            console.error(e);
            alert("서식을 불러오거나 화면을 생성하는 중 오류가 발생했습니다.\n상세: " + e.message);
            
            const btn = document.querySelector('.btn-submit');
            if(btn) {
                btn.textContent = "[PDF 다운로드]";
                btn.disabled = false;
            }
        }
    };

// ==========================================
// 문서 자동화 (견적/제안/청구) 관련 함수
// ==========================================
window.billingDocsData = []; // 데이터 전역 저장용

window.loadBillingDocs = async function() {
    try {
        const res = await fetch('/api/billing/docs');
        if(res.ok) {
            const json = await res.json();
            window.billingDocsData = json.data || [];
            renderBillingDocList(window.billingDocsData);
        }
    } catch(e) {
        console.error(e);
    }
};

// 문서번호 자동 생성 함수
function generateBillingDocNumber(type) {
    const codeMap = { 'quote': '02A', 'proposal': '02B', 'invoice': '02C' };
    const code = codeMap[type] || '000';
    
    const now = new Date();
    const yy = String(now.getFullYear()).substring(2,4);
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const dateStr = yy + mm + dd;
    
    const prefix = `HyeAn${code}${dateStr}`;
    
    let count = 0;
    if(window.billingDocsData) {
        window.billingDocsData.forEach(doc => {
            if(doc.type === type && doc.doc_number && doc.doc_number.startsWith(prefix)) {
                count++;
            }
        });
    }
    
    const seq = String(count + 1).padStart(3, '0');
    return prefix + seq;
}

function renderBillingDocList(data) {
    const tbody = document.getElementById('billing-doc-list');
    if(!tbody) return;
    
    tbody.innerHTML = '';
    if(data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-secondary);">생성된 문서가 없습니다.</td></tr>';
        return;
    }
    
    const typeMap = { 'quote': '견적서', 'proposal': '제안서', 'invoice': '청구서' };
    
    // 최근 3개만 표시
    const displayData = data.slice(0, 3);
    
    displayData.forEach(item => {
        const tr = document.createElement('tr');
        const dateStr = item.created_at ? item.created_at.split('T')[0] : '';
        const tStr = typeMap[item.type] || item.type;
        const amt = Number(item.total_amount).toLocaleString();
        
        tr.innerHTML = `
            <td>${dateStr}</td>
            <td><span class="status-badge" style="background:rgba(167,139,250,0.1); color:#a78bfa;">${tStr}</span></td>
            <td>${item.doc_number}</td>
            <td style="font-weight:bold;">${item.client_name}</td>
            <td>${item.title}</td>
            <td style="text-align:right;">${amt} 원</td>
            <td>
                <button class="btn-submit" style="padding:4px 8px; font-size:0.8rem;" onclick="printBillingDoc('${item.id}', '${item.type}')">PDF 인쇄</button>
                <button class="btn-logout" style="padding:4px 8px; font-size:0.8rem; background: rgba(239, 68, 68, 0.2); color: #ef4444;" onclick="deleteBillingDoc('${item.id}')">삭제</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.deleteBillingDoc = async function(docId) {
    if(!confirm('해당 문서를 정말 삭제하시겠습니까?')) return;
    try {
        const res = await fetch('/api/billing/docs/' + docId, { method: 'DELETE' });
        if(res.ok) {
            alert('삭제되었습니다.');
            loadBillingDocs();
        } else {
            alert('삭제 실패');
        }
    } catch(err) {
        console.error(err);
        alert('오류 발생');
    }
};

window.openBillingDocForm = function(type) {
    document.getElementById('billing-doc-form-container').style.display = 'block';
    document.getElementById('billing-doc-type').value = type;
    const typeMap = { 'quote': '견적서', 'proposal': '제안서', 'invoice': '청구서' };
    document.getElementById('billing-form-title').innerText = '새 ' + typeMap[type] + ' 작성';
    
    // 자동 문서 번호 입력 및 폼 초기화
    document.getElementById('billing-doc-number').value = generateBillingDocNumber(type);
    document.getElementById('billing-client-name').value = '';
    document.getElementById('billing-doc-title').value = '';
    document.getElementById('billing-items-body').innerHTML = '';
    addBillingItem();
};

window.closeBillingDocForm = function() {
    document.getElementById('billing-doc-form-container').style.display = 'none';
};

window.addBillingItem = function() {
    const tbody = document.getElementById('billing-items-body');
    const tr = document.createElement('tr');
    tr.className = 'billing-item-row';
    tr.innerHTML = `
        <td><input type="text" class="input-field item-category" placeholder="항목명" required></td>
        <td><input type="number" class="input-field item-unit-price" placeholder="0" onchange="calcBillingRow(this)" required></td>
        <td><input type="number" class="input-field item-qty" placeholder="1" value="1" onchange="calcBillingRow(this)" required></td>
        <td><input type="text" class="input-field item-total" readonly placeholder="0"></td>
        <td><button type="button" class="btn-logout" style="padding:4px 8px;" onclick="this.closest('tr').remove()">X</button></td>
    `;
    tbody.appendChild(tr);
};

window.calcBillingRow = function(el) {
    const tr = el.closest('tr');
    const price = parseFloat(tr.querySelector('.item-unit-price').value) || 0;
    const qty = parseFloat(tr.querySelector('.item-qty').value) || 0;
    tr.querySelector('.item-total').value = price * qty;
};

document.addEventListener('DOMContentLoaded', () => {
    const docForm = document.getElementById('billing-doc-form');
    if(docForm) {
        docForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const type = document.getElementById('billing-doc-type').value;
            const doc_number = document.getElementById('billing-doc-number').value;
            const client_name = document.getElementById('billing-client-name').value;
            const title = document.getElementById('billing-doc-title').value;
            
            const rows = document.querySelectorAll('.billing-item-row');
            const items = [];
            rows.forEach(r => {
                items.push({
                    category: r.querySelector('.item-category').value,
                    unit_price: parseFloat(r.querySelector('.item-unit-price').value) || 0,
                    quantity: parseFloat(r.querySelector('.item-qty').value) || 0,
                    total_price: parseFloat(r.querySelector('.item-total').value) || 0
                });
            });
            
            const payload = { type, doc_number, client_name, title, items };
            
            try {
                const res = await fetch('/api/billing/docs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if(res.ok) {
                    alert('저장되었습니다.');
                    closeBillingDocForm();
                    loadBillingDocs();
                } else {
                    alert('저장 실패');
                }
            } catch(err) {
                console.error(err);
                alert('오류 발생');
            }
        });
    }
});

window.printBillingDoc = function(docId, type) {
    window.open('/print/docs/' + type + '?id=' + docId, '_blank');
};

// ==========================================
// Notion Todo Calendar
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const calendarView = document.getElementById('calendar-dashboard-view');
    const calendarGrid = document.getElementById('calendar-grid');
    if (!calendarView || !calendarGrid) return;

    const monthTitle = document.getElementById('calendar-month-title');
    const statusBox = document.getElementById('calendar-status');
    const detailPanel = document.getElementById('calendar-detail');
    const today = new Date();
    let visibleMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    let events = [];
    let lastRangeKey = '';
    let isLoading = false;

    const escapeHtml = (value) => String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');

    const toDateKey = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    const eventDateKey = (value) => value ? value.slice(0, 10) : '';

    const getCalendarRange = () => {
        const monthStart = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
        const gridStart = new Date(monthStart);
        gridStart.setDate(gridStart.getDate() - gridStart.getDay());
        const gridEnd = new Date(gridStart);
        gridEnd.setDate(gridEnd.getDate() + 42);
        return { gridStart, gridEnd };
    };

    const eventFlags = (event) => {
        const flags = [];
        if (event.urgent) flags.push('<span class="calendar-event-flag urgent">긴급</span>');
        if (event.important) flags.push('<span class="calendar-event-flag important">중요</span>');
        if (event.must_do) flags.push('<span class="calendar-event-flag must-do">필수</span>');
        return flags.join('');
    };

    const showDetail = (event) => {
        const start = event.start ? new Date(event.start).toLocaleString('ko-KR', { dateStyle: 'long', timeStyle: event.start.includes('T') ? 'short' : undefined }) : '-';
        const end = event.end ? new Date(event.end).toLocaleString('ko-KR', { dateStyle: 'long', timeStyle: event.end.includes('T') ? 'short' : undefined }) : '';
        detailPanel.innerHTML = `
            <div class="calendar-detail-head">
                <span class="calendar-detail-kicker">${escapeHtml(event.category || '일정')}</span>
                <h3>${escapeHtml(event.title)}</h3>
            </div>
            <div class="calendar-detail-flags">${eventFlags(event) || '<span class="calendar-event-flag neutral">일반</span>'}</div>
            <dl class="calendar-detail-list">
                <div><dt>날짜</dt><dd>${escapeHtml(start)}${end ? ` ~ ${escapeHtml(end)}` : ''}</dd></div>
                <div><dt>상태</dt><dd>${escapeHtml(event.status || '미지정')}</dd></div>
                <div><dt>분류</dt><dd>${escapeHtml(event.category || '미지정')}</dd></div>
                <div><dt>상세 내용</dt><dd class="calendar-description">${escapeHtml(event.description || '등록된 상세 내용이 없습니다.')}</dd></div>
            </dl>
            ${event.url ? `<a class="calendar-notion-link" href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">Notion에서 열기 ↗</a>` : ''}
        `;
    };

    const renderCalendar = () => {
        monthTitle.textContent = `${visibleMonth.getFullYear()}년 ${visibleMonth.getMonth() + 1}월`;
        const { gridStart } = getCalendarRange();
        const todayKey = toDateKey(today);
        const cells = [];

        for (let index = 0; index < 42; index += 1) {
            const cellDate = new Date(gridStart);
            cellDate.setDate(gridStart.getDate() + index);
            const dateKey = toDateKey(cellDate);
            const dayEvents = events.filter(event => eventDateKey(event.start) === dateKey);
            const isOutside = cellDate.getMonth() !== visibleMonth.getMonth();
            const eventButtons = dayEvents.slice(0, 4).map((event) => {
                const eventIndex = events.indexOf(event);
                const priorityClass = event.urgent ? 'urgent' : event.must_do ? 'must-do' : event.important ? 'important' : '';
                return `<button type="button" class="calendar-event ${priorityClass}" data-event-index="${eventIndex}" title="${escapeHtml(event.title)}">${eventFlags(event)}<span>${escapeHtml(event.title)}</span></button>`;
            }).join('');
            const more = dayEvents.length > 4 ? `<button type="button" class="calendar-more" data-date="${dateKey}">+${dayEvents.length - 4}개 더보기</button>` : '';
            cells.push(`
                <div class="calendar-day${isOutside ? ' outside' : ''}${dateKey === todayKey ? ' today' : ''}" data-date="${dateKey}">
                    <span class="calendar-day-number">${cellDate.getDate()}</span>
                    <div class="calendar-events">${eventButtons}${more}</div>
                </div>
            `);
        }
        calendarGrid.innerHTML = cells.join('');
    };

    const loadCalendar = async (force = false) => {
        if (isLoading) return;
        const { gridStart, gridEnd } = getCalendarRange();
        const rangeKey = `${toDateKey(gridStart)}:${toDateKey(gridEnd)}`;
        if (!force && rangeKey === lastRangeKey) {
            renderCalendar();
            return;
        }

        isLoading = true;
        statusBox.className = 'calendar-status loading';
        statusBox.textContent = 'Notion 일정을 불러오는 중입니다…';
        try {
            const response = await fetch(`/api/master/calendar?start=${toDateKey(gridStart)}&end=${toDateKey(gridEnd)}`);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || '일정을 불러오지 못했습니다.');
            events = Array.isArray(result.events) ? result.events : [];
            lastRangeKey = rangeKey;
            statusBox.className = 'calendar-status success';
            statusBox.textContent = events.length ? `${events.length}개의 일정을 동기화했습니다.` : '이 기간에 등록된 일정이 없습니다.';
            renderCalendar();
        } catch (error) {
            events = [];
            statusBox.className = 'calendar-status error';
            statusBox.textContent = error.message;
            renderCalendar();
        } finally {
            isLoading = false;
        }
    };

    window.loadNotionCalendar = () => loadCalendar(false);

    calendarGrid.addEventListener('click', (event) => {
        const eventButton = event.target.closest('[data-event-index]');
        if (eventButton) {
            showDetail(events[Number(eventButton.dataset.eventIndex)]);
            return;
        }
        const moreButton = event.target.closest('[data-date]');
        if (moreButton) {
            const dayEvents = events.filter(item => eventDateKey(item.start) === moreButton.dataset.date);
            detailPanel.innerHTML = `<div class="calendar-detail-head"><span class="calendar-detail-kicker">일정 목록</span><h3>${escapeHtml(moreButton.dataset.date)}</h3></div><div class="calendar-day-list">${dayEvents.map(item => `<button type="button" data-detail-id="${escapeHtml(item.id)}">${eventFlags(item)}<span>${escapeHtml(item.title)}</span></button>`).join('')}</div>`;
        }
    });

    detailPanel.addEventListener('click', (event) => {
        const button = event.target.closest('[data-detail-id]');
        if (button) showDetail(events.find(item => item.id === button.dataset.detailId));
    });

    document.getElementById('calendar-prev').addEventListener('click', () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1);
        loadCalendar();
    });
    document.getElementById('calendar-next').addEventListener('click', () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1);
        loadCalendar();
    });
    document.getElementById('calendar-today').addEventListener('click', () => {
        visibleMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        loadCalendar();
    });
    document.getElementById('calendar-refresh').addEventListener('click', () => loadCalendar(true));

    renderCalendar();
    if (window.location.hash === '#calendar') {
        document.querySelector('.master-menu-item[data-menu="calendar"]')?.click();
    }
});

// Restore any sidebar tab from its URL hash and set the initial browser title.
document.addEventListener('DOMContentLoaded', () => {
    let hash = window.location.hash.slice(1);
    if (!hash) hash = 'home';
    
    // tab- prefix 제거 및 alias 매핑
    let requestedMenu = hash.replace(/^tab-/, '');
    if (requestedMenu === 'dashboard') requestedMenu = 'home';
    if (requestedMenu === 'finance-inquiry') requestedMenu = 'audit';

    const requestedItem = document.querySelector(`.master-menu-item[data-menu="${CSS.escape(requestedMenu)}"]`) ||
                          document.querySelector(`.master-menu-item[data-tab="tab-${CSS.escape(requestedMenu)}"]`);
    if (requestedItem) {
        requestedItem.click();
    }
});
