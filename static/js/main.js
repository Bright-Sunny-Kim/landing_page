// Premium Interaction JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // 1. 로그인 폼 유효성 체크
    const loginForm = document.getElementById('login-form');
    const submitBtn = document.getElementById('btn-submit');

    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', (e) => {
            const emailInput = document.getElementById('email');
            const companyInput = document.getElementById('company');
            const usernameInput = document.getElementById('username');
            const taskInput = document.getElementById('task_type');

            if (!emailInput.value.trim() || !companyInput.value.trim() || !usernameInput.value.trim() || !taskInput.value) {
                e.preventDefault();
                alert('모든 필드를 입력해 주세요.');
                return;
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailInput.value.trim())) {
                e.preventDefault();
                alert('올바른 이메일 주소를 입력해 주세요.');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.8';
            submitBtn.querySelector('span').textContent = '데이터 처리 중...';
            
            const svgIcon = submitBtn.querySelector('svg');
            if (svgIcon) {
                svgIcon.style.transform = 'translateX(10px)';
            }
        });
    }

    // 2. 파일 첨부명 실시간 미리보기 및 업무 요청 폼 조건부 유효성 체크
    const requestForm = document.getElementById('request-form');
    const fileInput = document.getElementById('file');
    const fileNamePreview = document.getElementById('file-name-preview');
    const requestSubmitBtn = document.getElementById('btn-request-submit');

    // 파일 선택 이벤트 연동
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

    // 업무 요청 폼 조건부 제출 검사
    if (requestForm && requestSubmitBtn) {
        requestForm.addEventListener('submit', (e) => {
            const helpText = document.getElementById('help_text').value.trim();
            const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;

            // 문의 글과 첨부파일 둘 다 비어있을 때만 경고 후 전송 차단
            if (!helpText && !hasFile) {
                e.preventDefault();
                alert('문의 사항을 작성하거나 파일을 첨부해 주세요.');
                return;
            }

            // 제출 시 비주얼 피드백
            requestSubmitBtn.disabled = true;
            requestSubmitBtn.style.opacity = '0.8';
            requestSubmitBtn.querySelector('span').textContent = 'Submitting...';
        });
    }
});
