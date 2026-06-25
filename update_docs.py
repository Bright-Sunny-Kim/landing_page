import codecs

update_text = """
## [2026-06-25] 파트너사 포털(제출 내역 조회 탭) 고도화 및 레이아웃 렌더링 버그 수정
- **UI 구조 결함 해결 (`company.html`)**: 이전 작업 중 '회계감사' 탭에서 서브 탭 컨테이너 닫힘 태그(`</div>`)가 누락되어 '제출 내역 조회' 및 'AI 회계사 문의' 탭 전체가 하위 요소로 잘못 종속(Nested)되던 버그를 해결. 원본 구조 복구 후 각 탭이 정상적인 형제(Sibling) 관계로 렌더링되도록 수정 (탭 클릭 시 빈화면 노출 현상 완벽 조치).
- **'제출 내역 조회' 탭 고도화 및 업로드 기능 통합 (`company.html`)**: 
  - 상단에 진척도(Progress) 요약 대시보드(퍼센트 게이지 바) 및 카테고리별 미제출 내역 리스트 표출.
  - 기존 '회계감사' 탭에 혼재되어 있던 항목별 자료 제출 기능(회사기본사항, 서면제출자료, 외부조회(금융/거래처))을 서브 탭 형태로 '제출 내역 조회' 탭 내부로 통합 이관하여 UX를 개선.
- **백엔드 분류/적재 로직 연동 (`app.py`)**: 
  - '제출 내역 조회' 탭 내의 새로운 단일 업로드 폼 형식(Hidden 필드로 Category 전달)을 파싱할 수 있도록 `company_upload` 로직 확장.
  - 제출된 카테고리와 세부 항목명(예: `current_fs`, `finance_bank_balance`)에 따라 `P-File`, `Temp/Temp_P`, `Temp/Temp_L`, `Ext_F`, `Ext_C` 명칭의 연도별(year_folder) 폴더 구조를 자동 판별하여 MinIO 및 DB에 맞춤형 적재 처리 구현 완료.
"""

with codecs.open('docs/project_master.md', 'a', 'utf-8') as f:
    f.write(update_text)
print("Updated project_master.md")
