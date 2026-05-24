// Premium Interaction JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // 1. 로그인 폼 동적 제어 로직
    const loginForm = document.getElementById('login-form');
    const emailInput = document.getElementById('email');
    const emailStatusMsg = document.getElementById('email-status-msg');
    const additionalFields = document.getElementById('additional-fields');
    const submitBtn = document.getElementById('btn-submit');

    // 추가 필드 요소들
    const companyInput = document.getElementById('company');
    const usernameInput = document.getElementById('username');
    const taskInput = document.getElementById('task_type');

    let isExistingUser = false; // DB 등록 여부 플래그

    if (emailInput && emailStatusMsg && additionalFields) {
        
        // 이메일 유효성 체크 함수
        const validateEmail = (email) => {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        };

        // 실시간 이메일 DB 체크 함수
        const checkEmailDb = async () => {
            const emailValue = emailInput.value.trim();

            if (!emailValue) {
                emailStatusMsg.textContent = '';
                emailStatusMsg.className = 'email-status-msg';
                additionalFields.classList.remove('show');
                setFieldsRequired(false);
                return;
            }

            if (!validateEmail(emailValue)) {
                emailStatusMsg.textContent = '올바른 이메일 주소 형식을 입력해 주세요.';
                emailStatusMsg.className = 'email-status-msg error';
                additionalFields.classList.remove('show');
                setFieldsRequired(false);
                return;
            }

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
                        emailStatusMsg.textContent = '✓ 등록된 파트너십 이메일이 확인되었습니다.';
                        emailStatusMsg.className = 'email-status-msg success';
                        
                        // 추가 필드 숨기기 및 필수 속성 제거
                        additionalFields.classList.remove('show');
                        setFieldsRequired(false);
                        if (submitBtn) {
                            submitBtn.querySelector('span').textContent = '로그인 및 대시보드 입장';
                        }
                    } else {
                        isExistingUser = false;
                        emailStatusMsg.textContent = '✦ 신규 파트너사 등록이 필요합니다. 상세 정보를 입력해 주세요.';
                        emailStatusMsg.className = 'email-status-msg info';
                        
                        // 추가 필드 펼치기 및 필수 속성 부여
                        additionalFields.classList.add('show');
                        setFieldsRequired(true);
                        if (submitBtn) {
                            submitBtn.querySelector('span').textContent = '신규 등록 및 로그인';
                        }
                    }
                }
            } catch (error) {
                console.error('Email check failed:', error);
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
        
        // 입력 도중 실시간 감지를 하되 너무 잦은 API 조회를 막기 위해 릴리즈 타이머(Debounce) 적용
        let emailDebounceTimer;
        emailInput.addEventListener('input', () => {
            clearTimeout(emailDebounceTimer);
            emailDebounceTimer = setTimeout(checkEmailDb, 600);
        });
    }

    // 로그인 폼 제출 유효성 검사
    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', (e) => {
            const emailValue = emailInput.value.trim();

            if (!emailValue || !validateEmail(emailValue)) {
                e.preventDefault();
                alert('올바른 이메일 주소를 입력해 주세요.');
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

            // 제출 시 비주얼 피드백
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.8';
            submitBtn.querySelector('span').textContent = '인증 처리 중...';
        });
    }

    // 2. 파일 첨부명 실시간 미리보기 및 업무 요청 폼 조건부 유효성 체크
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
