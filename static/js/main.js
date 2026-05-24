// Premium Interaction JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const submitBtn = document.getElementById('btn-submit');

    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', (e) => {
            const emailInput = document.getElementById('email');
            const companyInput = document.getElementById('company');
            const usernameInput = document.getElementById('username');

            // 기본 유효성 체크
            if (!emailInput.value.trim() || !companyInput.value.trim() || !usernameInput.value.trim()) {
                e.preventDefault();
                alert('모든 필드를 입력해 주세요.');
                return;
            }

            // 이메일 정규식 유효성 체크
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailInput.value.trim())) {
                e.preventDefault();
                alert('올바른 이메일 주소를 입력해 주세요.');
                return;
            }

            // 제출 시 마이크로 애니메이션 및 상태 변경
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.8';
            submitBtn.querySelector('span').textContent = '데이터 처리 중...';
            
            const svgIcon = submitBtn.querySelector('svg');
            if (svgIcon) {
                svgIcon.style.transform = 'translateX(10px)';
            }
        });
    }

    // 인풋 필드에 포커스 되었을 때 추가 비주얼 효과가 필요하다면 여기에 추가 작성 가능
});
