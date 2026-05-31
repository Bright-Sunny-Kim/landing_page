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

    // 3. 파일 첨부명 실시간 미리보기 및 업무 요청 폼 조건부 유효성 체크
    const requestForm = document.getElementById('request-form');
    const fileInput = document.getElementById('file');
    const fileNamePreview = document.getElementById('file-name-preview');
    const requestSubmitBtn = document.getElementById('btn-request-submit');

    if (fileInput && fileNamePreview) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const name = e.target.files[0].name;
                fileNamePreview.textContent = name;
                fileNamePreview.style.color = '#a78bfa';
                fileNamePreview.style.fontWeight = '500';
            } else {
                fileNamePreview.textContent = '선택된 파일 없음';
                fileNamePreview.style.color = 'var(--text-secondary)';
                fileNamePreview.style.fontWeight = 'normal';
            }
        });
    }

    if (requestForm && requestSubmitBtn) {
        requestForm.addEventListener('submit', (e) => {
            const helpText = document.getElementById('help_text').value.trim();
            const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;

            if (!helpText && !hasFile) {
                e.preventDefault();
                alert('문의 사항을 작성하거나 파일을 첨부해 주세요.');
                return;
            }

            requestSubmitBtn.disabled = true;
            requestSubmitBtn.style.opacity = '0.8';
            requestSubmitBtn.querySelector('span').textContent = 'Submitting...';
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
