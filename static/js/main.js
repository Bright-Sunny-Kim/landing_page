// Premium Interaction JavaScript

document.addEventListener('DOMContentLoaded', () => {
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

    if (emailInput && emailStatusMsg && additionalFields && passwordGroup && submitBtn) {
        
        // 실시간 이메일 DB 체크 함수
        const checkEmailDb = async () => {
            const emailValue = emailInput.value.trim();

            if (!emailValue) {
                emailStatusMsg.textContent = '';
                emailStatusMsg.className = 'email-status-msg';
                additionalFields.classList.remove('show');
                passwordGroup.classList.remove('show');
                rememberGroup.classList.remove('show');
                setFieldsRequired(false);
                submitBtn.disabled = true;
                submitBtn.querySelector('span').textContent = '이메일을 입력하세요';
                return;
            }

            if (!validateEmail(emailValue)) {
                emailStatusMsg.textContent = '올바른 이메일 주소 형식을 입력해 주세요.';
                emailStatusMsg.className = 'email-status-msg error';
                additionalFields.classList.remove('show');
                passwordGroup.classList.remove('show');
                rememberGroup.classList.remove('show');
                setFieldsRequired(false);
                submitBtn.disabled = true;
                submitBtn.querySelector('span').textContent = '이메일 형식 오류';
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
                        
                        // 추가 정보 필드는 숨기고 비밀번호 및 로그인 유지 토글 노출
                        additionalFields.classList.remove('show');
                        passwordGroup.classList.add('show');
                        rememberGroup.classList.add('show');
                        
                        setFieldsRequired(false);
                        passwordInput.required = true;
                        
                        submitBtn.disabled = false;
                        submitBtn.style.opacity = '1';
                        submitBtn.querySelector('span').textContent = '로그인';
                    } else {
                        isExistingUser = false;
                        emailStatusMsg.textContent = '✦ 신규 파트너사 등록이 필요합니다. 상세 정보를 입력해 주세요.';
                        emailStatusMsg.className = 'email-status-msg info';
                        passwordLabel.textContent = '비밀번호 설정';
                        
                        // 추가 정보 필드 및 비밀번호, 로그인 유지 토글 모두 노출
                        additionalFields.classList.add('show');
                        passwordGroup.classList.add('show');
                        rememberGroup.classList.add('show');
                        
                        setFieldsRequired(true);
                        passwordInput.required = true;
                        
                        submitBtn.disabled = false;
                        submitBtn.style.opacity = '1';
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
                if (!companyInput.value.trim() || !usernameInput.value.trim() || !taskInput.value) {
                    e.preventDefault();
                    alert('신규 파트너사 등록을 위해 모든 항목을 입력해 주세요.');
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
    const oauthCompany = document.getElementById('oauth-company');
    const oauthUsername = document.getElementById('oauth-username');
    const oauthTask = document.getElementById('oauth-task_type');
    
    let currentProvider = ''; // 'google' or 'naver'
    
    const openOauthModal = (provider) => {
        if (!oauthModal) return;
        currentProvider = provider;
        oauthEmailInput.value = '';
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
                const company = oauthCompany.value.trim();
                const username = oauthUsername.value.trim();
                const task = oauthTask.value;
                
                if (!company || !username || !task) {
                    alert('신규 소셜 파트너사 등록을 위해 모든 항목을 입력해 주세요.');
                    return;
                }
                
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

    // 4. 마스터 관리자 사이드바 클릭 상호작용 및 Mock 화면 렌더링
    const sidebarMenuItems = document.querySelectorAll('.master-menu-item');
    const masterMainContent = document.getElementById('master-main-content');
    const homeDashboardView = document.getElementById('home-dashboard-view');
    const detailDashboardView = document.getElementById('detail-dashboard-view');

    // 각 메뉴명에 대응하는 한글 정보 및 설명 정의
    const menuMockData = {
        requests: {
            title: '📥 업무 요청 관리',
            desc: '모든 파트너사에서 요청한 실시간 감사, 세무 자문 및 기장 대행 건을 진행 상태별로 필터링하고 일괄 관리할 수 있는 통합 관리 보드입니다. 실시간 업무 현황을 간편하게 제어하세요.',
            icon: '📥',
            placeholder: '모든 파트너사 요청 실시간 모니터링 준비 중'
        },
        repository: {
            title: '📂 통합 문서 보관함',
            desc: '각 기업 파트너사가 업로드한 증빙 서류 파일 및 세무조정계산서, 재무제표 등 완료 보고서를 Supabase Storage 버킷과 동기화하여 보안 보관하고 다운로드할 수 있는 문서 전용 드라이브 공간입니다.',
            icon: '📂',
            placeholder: '기업별 보안 문서 보관 및 공유 드라이브 준비 중'
        },
        announcements: {
            title: '📢 공지 및 알림 관리',
            desc: '회계법인 혜안 파트너 포털에 접속하는 기업 회원들을 대상으로 긴급 세무 일정 알림, 시스템 공지사항, 팝업 메시지를 등록하고 우선순위별로 편집하여 일괄 게시하는 중앙 알림 컨트롤러입니다.',
            icon: '📢',
            placeholder: '파트너사 타겟팅 긴급 공지 등록기 준비 중'
        },
        calendar: {
            title: '📅 세무 일정 캘린더',
            desc: '법인세, 부가가치세, 원천세 신고 등 월별 주요 국가 세무 일정표와 각 파트너사 담당자와의 세무 대면 상담 및 법인 회계 감사 방문 실사 스케줄을 한눈에 관리하는 통합 세무 캘린더입니다.',
            icon: '📅',
            placeholder: '국세청 세무 신고 스케줄러 & 방문 상담 캘린더 준비 중'
        },
        chat: {
            title: '💬 실시간 자문 상담',
            desc: '비즈니스 파트너사 담당자가 실시간으로 문의하는 세무/회계 관련 일상 자문 건에 대해 회계사가 즉시 답변하고 자료 조회를 제공하는 실시간 질의응답 아카이브 및 채팅 관리 패널입니다.',
            icon: '💬',
            placeholder: '1:1 파트너사 실시간 세무 자문 채팅창 준비 중'
        },
        billing: {
            title: '💳 수수료 및 청구 관리',
            desc: '매월 발생하는 기장 서비스 수수료, 연간 세무조정 수수료, 인수합병(M&A) 및 재무 감사 실사 용역 비용 청구서를 안전하게 발행하고 완납/미납 결제 여부를 통합 대조하는 빌링 대시보드입니다.',
            icon: '💳',
            placeholder: '기업 수수료 청구서 및 정기 기장료 수납 추적기 준비 중'
        },
        analytics: {
            title: '📈 시스템 통계 및 리포트',
            desc: '연도별/월별 신규 파트너사 유치 통계, 누적 파일 전송 데이터 사용량, 기장 대리 수요 추이 분석 그래프 및 월별 업무 처리 효율성을 다각도로 시각화하여 경영 분석을 돕는 통합 리포트 화면입니다.',
            icon: '📈',
            placeholder: '통합 경영 통계 시각화 및 리포팅 모듈 준비 중'
        },
        settings: {
            title: '⚙️ 포털 시스템 설정',
            desc: '최고 관리자(Master) 계정 관리 및 추가 부회계사 권한 부여, 파트너사 포털 접근 차단/해제 IP 제어, 시스템 보안 감사 로그 모니터링 및 PWA 설치형 웹 사이트의 캐시 리프레시 설정을 관리하는 시스템 패널입니다.',
            icon: '⚙️',
            placeholder: '보안 접근 제어 및 서브 관리자 권한 설정 센터 준비 중'
        }
    };

    if (sidebarMenuItems.length > 0 && masterMainContent) {
        sidebarMenuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const menu = item.getAttribute('data-menu');
                
                // 만약 상세 페이지(master_detail.html)에서 홈이 아닌 다른 Mock 메뉴를 클릭했을 때는 목록 페이지(/master)로 넘어가서 탭이 열리도록 링크 이동 허용
                if (detailDashboardView && menu !== 'partners') {
                    // detail view가 켜져 있으면, href 경로를 타서 목록 페이지로 이동하게 둠 (e.preventDefault 하지 않음)
                    return;
                }
                
                // 1. 홈 대시보드 탭 활성화 처리
                if (menu === 'home' || menu === 'partners') {
                    // 기본 상세 뷰 또는 홈 뷰 활성화
                    if (homeDashboardView) {
                        e.preventDefault();
                        
                        // 사이드바 active 갱신
                        sidebarMenuItems.forEach(i => i.classList.remove('active'));
                        const targetItem = document.querySelector(`.master-menu-item[data-menu="home"]`) || item;
                        targetItem.classList.add('active');
                        
                        // 기존에 로드된 Mock 뷰들 다 제거
                        const activeMocks = masterMainContent.querySelectorAll('.mock-dashboard');
                        activeMocks.forEach(m => m.remove());
                        
                        // 타 대시보드 숨기기
                        const analyticsDashboardView = document.getElementById('analytics-dashboard-view');
                        if (analyticsDashboardView) analyticsDashboardView.style.display = 'none';
                        
                        // 홈 보이기
                        homeDashboardView.style.display = 'block';
                    }
                    return;
                }
                
                // 2. 시스템 통계 및 리포트 (analytics) 분기 처리
                if (menu === 'analytics') {
                    e.preventDefault();
                    
                    sidebarMenuItems.forEach(i => i.classList.remove('active'));
                    item.classList.add('active');
                    
                    if (homeDashboardView) homeDashboardView.style.display = 'none';
                    if (detailDashboardView) detailDashboardView.style.display = 'none';
                    
                    // 기존 Mock 뷰들 다 제거
                    const activeMocks = masterMainContent.querySelectorAll('.mock-dashboard');
                    activeMocks.forEach(m => m.remove());
                    
                    // analytics 뷰 보이기
                    const analyticsDashboardView = document.getElementById('analytics-dashboard-view');
                    if (analyticsDashboardView) {
                        analyticsDashboardView.style.display = 'block';
                    }
                    return;
                }
                
                // 3. Mock 나머지 7개 메뉴 탭 클릭 시 (e.preventDefault로 가상 렌더링)
                e.preventDefault();
                
                // 사이드바 active 클래스 토글
                sidebarMenuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                
                // 기존 대시보드 뷰 숨기기
                if (homeDashboardView) homeDashboardView.style.display = 'none';
                if (detailDashboardView) detailDashboardView.style.display = 'none';
                const analyticsDashboardView = document.getElementById('analytics-dashboard-view');
                if (analyticsDashboardView) analyticsDashboardView.style.display = 'none';
                
                // 기존에 열려있던 다른 Mock 뷰 제거
                const activeMocks = masterMainContent.querySelectorAll('.mock-dashboard');
                activeMocks.forEach(m => m.remove());
                
                // 새 Mock HTML 생성 및 인젝션
                const data = menuMockData[menu];
                if (data && menu !== 'analytics') {
                    const mockHtml = `
                        <div class="mock-dashboard">
                            <header class="mock-header">
                                <h1 class="mock-title">${data.title}</h1>
                            </header>
                            
                            <div class="glass-card dashboard-card master-card mock-placeholder-card">
                                <span class="mock-placeholder-icon">${data.icon}</span>
                                <h3 class="mock-placeholder-title">${data.placeholder}</h3>
                                <p class="mock-placeholder-desc">${data.desc}</p>
                                <div class="status-badge" style="background: rgba(167, 139, 250, 0.08); border-color: rgba(167, 139, 250, 0.2); color: #a78bfa; margin-top: 10px; margin-bottom: 0;">
                                    <span class="pulse-dot" style="background: #a78bfa; box-shadow: 0 0 0 0 rgba(167, 139, 250, 0.4);"></span>
                                    <span>회계법인 혜안 IT 지원팀 개발 예정인 화면입니다</span>
                                </div>
                            </div>
                        </div>
                    `;
                    masterMainContent.insertAdjacentHTML('beforeend', mockHtml);
                }
            });
        });
    }
});

// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            })
            .catch(err => {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

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
            if (stepId === 'step1') {
                indicator.textContent = '✓ 연결 성공 (n8n Webhook OK - HTTP 200)';
                indicator.style.color = '#10b981';
            } else if (stepId === 'step2') {
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


// ==========================================
// AI FAQ Chat Logic
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('btn-faq-submit');
    const inputArea = document.getElementById('faq-question-input');
    const categorySelect = document.getElementById('faq-category-select');
    const messagesContainer = document.getElementById('faq-chat-messages');

    if (submitBtn && inputArea && messagesContainer) {
        
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
                    body: JSON.stringify({ question, category })
                });

                const data = await response.json();
                
                // 4. 로딩 애니메이션 제거
                const loadingEl = document.getElementById(loadingId);
                if (loadingEl) loadingEl.remove();

                if (response.ok) {
                    // 5. AI 답변 추가
                    appendMessage('ai', data.answer, data.sources);
                } else {
                    appendMessage('ai', '오류가 발생했습니다: ' + (data.error || '서버 에러'));
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
            let formattedText = text.replace(/\n/g, '<br>');
            
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
                    <p>${formattedText}</p>
                    ${sourcesHtml}
                </div>
            `;
            messagesContainer.appendChild(bubble);
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
