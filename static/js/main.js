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

    // 2. 파일 첨부명 실시간 미리보기 (마이크로 인터랙션)
    const fileInput = document.getElementById('file');
    const fileNamePreview = document.getElementById('file-name-preview');

    if (fileInput && fileNamePreview) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const name = e.target.files[0].name;
                fileNamePreview.textContent = name;
                fileNamePreview.style.color = '#a78bfa'; // 파일이 선택되면 글자색 변경
                fileNamePreview.style.fontWeight = '500';
            } else {
                fileNamePreview.textContent = '선택된 파일 없음';
                fileNamePreview.style.color = 'var(--text-secondary)';
                fileNamePreview.style.fontWeight = 'normal';
            }
        });
    }
});
