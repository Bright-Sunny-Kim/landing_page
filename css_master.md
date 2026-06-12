# HyeAn_DSKim Portal - CSS Master Guide

본 문서는 회계법인 혜안 고객 포털(`HyeAn_DSKim`)의 프리미엄 글래스모피즘(Glassmorphism) 디자인 시스템 가이드입니다. 각 페이지의 CSS 일관성을 유지하고, 향후 기능 추가 및 업데이트 시 통일된 디자인 규칙을 적용하기 위한 표준 설계 규칙을 명시합니다.

---

## 1. 디자인 시스템 토큰 (CSS Variables)

포털 내 모든 요소는 아래 정의된 변수를 기준으로 작성해야 합니다. 개별 하드코딩된 색상이나 폰트는 지양하고 반드시 CSS 변수를 참조하십시오.

```css
:root {
    /* 배경 및 카드 기본 색상 */
    --bg-dark: #09090b;                  /* 심해의 어두운 무채색 */
    --card-bg: rgba(20, 20, 25, 0.4);     /* 투명하고 차분한 어두운 카드 배경 */
    --card-border: rgba(255, 255, 255, 0.07); /* 미세한 광택감을 위한 테두리 선 */
    
    /* 텍스트 시스템 */
    --text-primary: #f4f4f5;              /* 기본 화이트 텍스트 */
    --text-secondary: #a1a1aa;            /* 보조 그레이 텍스트 */
    
    /* 시그니처 오로라 그라데이션 및 포인트 */
    --primary-gradient: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%); /* 보라색 -> 인디고 블루 */
    --hover-gradient: linear-gradient(135deg, #c084fc 0%, #818cf8 100%);   /* 마우스 호버 시 활성화 밝기 */
    --accent-glow: rgba(99, 102, 241, 0.25);                              /* 시그니처 네온 글로우 */
    --accent-color: #6366f1;                                               /* 포인트 강조 색상 */
    --success-color: #10b981;                                              /* 승인 및 완료 초록색 */
    
    /* 표준 타이포그래피 */
    --font-header: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --font-body: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
```

---

## 2. 디자인 핵심 설계 원칙

### ① 프리미엄 글래스모피즘 (Glassmorphism)
포털의 시각적 완성도는 투명 카드 레이아웃에 있습니다. 카드를 추가할 때는 항상 아래 표준 카드 스타일을 베이스로 활용하세요:
```css
.glass-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    backdrop-filter: blur(20px) saturate(140%);
    -webkit-backdrop-filter: blur(20px) saturate(140%);
    border-radius: 24px;
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), 
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

### ② 네온 글로우 및 오로라 이펙트
- 짙은 배경에 신비감을 더하기 위해 그라데이션 광원을 뒷배경에 배치합니다 (`.background-decor` 내부 `.circle-1`, `.circle-2` 등 blur 100px 처리된 배경 요소 활용).
- 중요 버튼 및 상태 배지에는 `--accent-glow`를 사용해 은은한 발광 효과(`box-shadow`)를 제공하여 눈길을 사로잡습니다.

### ③ 마이크로 인터랙션 (호버 애니메이션)
- 사용자의 모든 입력 장치와 상호작용하는 요소(카드, 버튼, 테이블 행)는 부드러운 전환 효과(`transition: all 0.3s ease;`)를 가집니다.
- 호버 시 카드나 버튼은 미세하게 위로 떠오르며(`transform: translateY(-2px ~ -4px);`), 그림자가 넓어지고 테두리 광택이 살아나도록 설계합니다.

### ④ 브랜드 로고 노출 표준
- 포털 내 혜안 로고는 웹과 모바일 환경 모두에서 가시성을 확보하기 위해 충분한 크기를 사용합니다.
- **로고 이미지(`.logo-img`)**: 기본 높이(height) `54px` 유지
- **로고 텍스트(`.logo-text-admin`, `.logo-text-portal`)**: 폰트 사이즈 `18px`, `font-weight: 700` 유지

---

## 3. 레이아웃 및 반응형 표준

### ① 스페이스 및 넓이
- 페이지 진입 시 가장 중요한 액션 카드(예: 로그인 폼, 대시보드 카드)가 시각적 중심을 잡을 수 있게 중앙 정렬 레이아웃을 사용합니다.
- 복수의 서브 섹션이 아래로 이어지는 경우, 세로 스크롤을 부드럽게 유도할 수 있도록 `body`를 아래와 같이 구성합니다:
  ```css
  body {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      padding: 60px 20px;
      overflow-x: hidden;
  }
  ```
- **전체 폭 활용 (Full Width)**: 최신 업데이트를 통해 `.dashboard-container`, `.master-container`, `.glass-card` 내부 요소들이 최대 넓이 제한(`max-width`)을 풀고 화면 넓이에 맞춰 가변적으로(100%) 확장되도록 `!important`를 활용하여 수정되었습니다. 사용자의 넓은 스크린 모니터에서도 여백 낭비 없이 쾌적하게 보이게 합니다.

### ② 반응형 중단점 (Breakpoints)
- **데스크톱 (992px 초과)**: 2열 구조(Split Card) 및 100% 가로 폭 확장 기능을 통해 정보 전달 공간을 넓게 씁니다. 사이드바(`master-sidebar`)는 좌측에 고정됩니다.
- **태블릿 및 모바일 (992px 이하 ~ 800px 이하)**:
  - 데스크톱 전용 좌측 사이드바 구조가 상단 칩셋 형태나 하단 슬라이드 형태로 재배열됩니다.
  - 가로 넓이가 좁은 디바이스 환경에서 여백 패딩을 축소하여 가독성을 높입니다 (`padding: 32px 24px` 혹은 모바일 `padding: 24px 16px`).
- **모바일 (600px 이하)**:
  - 화면에 불필요한 장식용 텍스트나 데코 이미지(예: 랜딩 페이지 인트로의 긴 본문 등)를 `display: none;` 처리하여 불필요한 긴 스크롤을 방지하고 로그인 폼과 핵심 액션에 집중하도록 유도합니다.

---

## 4. 향후 업데이트 규칙

1. **신규 테마 컬러 생성 방지**: 특별한 브랜딩 요구 사항이 없는 한 위에 정의된 시그니처 그라데이션(`--primary-gradient`) 및 색상을 재사용하여 플랫폼 일관성을 고수하십시오.
2. **독립적인 CSS 구조화**: 공용 스타일은 `style.css` 상단에 정의하고, 특정 페이지/도메인(예: `/master`, `/company`)의 요소들은 파일 하단에 주석으로 영역을 확실히 나누어 관리하십시오.
3. **PWA 최적화 주의**: 서비스 워커 및 아이콘의 변화가 있을 때는 캐시 무효화 처리를 적절히 동반해야 테마 스타일시트가 사용자 클라이언트에 정상 즉시 반영됩니다.
