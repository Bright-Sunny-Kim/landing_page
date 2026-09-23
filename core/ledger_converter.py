# -*- coding: utf-8 -*-
"""
6대 회계장부(분개장, 거래처원장, 계정별원장) JSON 고정밀 변환기
- 회계 프로그램(더존 Smart A, 위하고, 세무사랑 등) 엑셀 내보내기 포맷 완벽 지원
- 전표일자(Date), 전표번호(int), 계정코드(int), 차변/대변(int), 계정과목/거래처/적요(str) 엄격 타입 변환
"""

import os
import re
import json
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from core.extensions import logger


def _parse_date_str(val: Any) -> str:
    """날짜 데이터를 'YYYY-MM-DD' 표준 문자열로 안전하게 변환"""
    if pd.isna(val) or val is None or str(val).strip() in ['', 'nan', 'NaT', 'None']:
        return ""
    if isinstance(val, (datetime.date, datetime.datetime, pd.Timestamp)):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    if ' ' in s:
        s = s.split(' ')[0]
    # YYYY.MM.DD 또는 YYYY/MM/DD -> YYYY-MM-DD
    s = re.sub(r'[./]', '-', s)
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s


def _to_int(val: Any, default: int = 0) -> int:
    """숫자/문자열을 정수(int)로 안전하게 변환"""
    if pd.isna(val) or val is None:
        return default
    s = str(val).replace(',', '').strip()
    if not s or s in ['-', 'nan', 'None']:
        return default
    try:
        return int(round(float(s)))
    except (ValueError, TypeError):
        nums = re.findall(r'[-+]?\d+', s)
        if nums:
            return int(nums[0])
        return default


def _to_clean_str(val: Any) -> str:
    """문자열 공백 및 결측치 정제"""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'nat']:
        return ""
    return s


def parse_journal_entries(
    file_or_df: Union[str, pd.DataFrame],
    output_json_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    분개장 엑셀/데이터프레임을 엄격한 규격의 JSON 레코드 목록으로 변환합니다.

    규격:
      - 전표일자 (date): 'YYYY-MM-DD'
      - 전표번호 (voucher_no): int
      - 구분 (entry_type): str (예: '차변', '대변', '출금', '입금')
      - 계정코드 (account_code): int
      - 계정과목 (account_name): str
      - 차변 (debit): int
      - 대변 (credit): int
      - 거래처 (customer): str
      - 거래처코드 (customer_code): str
      - 적요 (description): str
    """
    logger.info("[JOURNAL_CONVERTER] 분개장 파싱 시작: %s", type(file_or_df))
    
    if isinstance(file_or_df, str):
        if not os.path.exists(file_or_df):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_or_df}")
        if file_or_df.endswith('.csv'):
            df = pd.read_csv(file_or_df, header=None, dtype=str)
        else:
            df = pd.read_excel(file_or_df, header=None, dtype=str)
    else:
        df = file_or_df.copy()

    # 1. 헤더 행 및 컬럼 매핑 자동 탐색
    header_row = -1
    col_map = {
        "date": -1,
        "voucher_no": -1,
        "entry_type": -1,
        "account_code": -1,
        "account_name": -1,
        "debit": -1,
        "credit": -1,
        "customer": -1,
        "customer_code": -1,
        "description": -1
    }

    for r in range(min(15, len(df))):
        row_cells = [_to_clean_str(x).replace(" ", "").lower() for x in df.iloc[r].tolist()]
        temp_map = {}
        for idx, cell in enumerate(row_cells):
            if any(k in cell for k in ["전표일자", "일자", "날짜", "date"]):
                temp_map["date"] = idx
            elif any(k in cell for k in ["전표번호", "번호", "voucherno", "vouchernum"]):
                temp_map["voucher_no"] = idx
            elif cell in ["구분", "대차", "type"]:
                temp_map["entry_type"] = idx
            elif cell in ["code", "코드", "계정코드"]:
                # D열(앞쪽 Code)은 계정코드
                if "account_code" not in temp_map:
                    temp_map["account_code"] = idx
                else:
                    temp_map["customer_code"] = idx
            elif any(k in cell for k in ["계정과목", "과목", "계정명", "account"]):
                temp_map["account_name"] = idx
            elif any(k in cell for k in ["차변", "차변금액", "debit"]):
                temp_map["debit"] = idx
            elif any(k in cell for k in ["대변", "대변금액", "credit"]):
                temp_map["credit"] = idx
            elif any(k in cell for k in ["거래처", "거래처명", "customer", "vendor"]):
                temp_map["customer"] = idx
            elif any(k in cell for k in ["적요", "내역", "비고", "description", "memo"]):
                temp_map["description"] = idx

        # 계정과목과 (차변 또는 대변)이 식별되면 헤더 행으로 확정
        if "account_name" in temp_map and ("debit" in temp_map or "credit" in temp_map):
            header_row = r
            col_map.update(temp_map)
            break

    # 헤더 행을 찾지 못한 경우 위치 기반 기본값(0:일자, 1:전표, 2:구분, 3:코드, 4:과목, 5:차변, 6:대변, 7:거래처, 8:거래처코드, 9:적요)
    if header_row == -1:
        header_row = 0
        col_map = {
            "date": 0,
            "voucher_no": 1,
            "entry_type": 2,
            "account_code": 3,
            "account_name": 4,
            "debit": 5,
            "credit": 6,
            "customer": 7,
            "customer_code": 8 if len(df.columns) > 8 else -1,
            "description": 9 if len(df.columns) > 9 else (8 if len(df.columns) > 8 else -1)
        }

    records: List[Dict[str, Any]] = []
    prev_date = ""
    prev_voucher_no = 0

    for i in range(header_row + 1, len(df)):
        # 계정과목 확인
        raw_acc = df.iat[i, col_map["account_name"]] if 0 <= col_map["account_name"] < len(df.columns) else None
        acc_name = _to_clean_str(raw_acc)
        if not acc_name or acc_name in ["계정과목", "합계", "소계", "총계", "누계", "월계", "연계"]:
            continue

        # 전표일자 (공백 시 직전 전표일자 상속 지원)
        raw_date = df.iat[i, col_map["date"]] if 0 <= col_map["date"] < len(df.columns) else None
        date_str = _parse_date_str(raw_date)
        if not date_str and prev_date:
            date_str = prev_date
        elif date_str:
            prev_date = date_str

        # 전표번호 (int)
        raw_voucher = df.iat[i, col_map["voucher_no"]] if 0 <= col_map["voucher_no"] < len(df.columns) else None
        voucher_int = _to_int(raw_voucher, default=0)
        if voucher_int == 0 and prev_voucher_no > 0 and date_str == prev_date:
            voucher_int = prev_voucher_no
        elif voucher_int > 0:
            prev_voucher_no = voucher_int

        # 구분
        raw_type = df.iat[i, col_map["entry_type"]] if 0 <= col_map["entry_type"] < len(df.columns) else ""
        entry_type_str = _to_clean_str(raw_type)

        # Code (계정코드: int)
        raw_code = df.iat[i, col_map["account_code"]] if 0 <= col_map["account_code"] < len(df.columns) else None
        account_code_int = _to_int(raw_code, default=0)

        # 차변, 대변 (int)
        raw_debit = df.iat[i, col_map["debit"]] if 0 <= col_map["debit"] < len(df.columns) else 0
        raw_credit = df.iat[i, col_map["credit"]] if 0 <= col_map["credit"] < len(df.columns) else 0
        debit_int = _to_int(raw_debit, default=0)
        credit_int = _to_int(raw_credit, default=0)

        # 거래처, 거래처코드, 적요 (str)
        raw_cust = df.iat[i, col_map["customer"]] if 0 <= col_map["customer"] < len(df.columns) else ""
        customer_str = _to_clean_str(raw_cust)

        raw_cust_code = df.iat[i, col_map["customer_code"]] if 0 <= col_map["customer_code"] < len(df.columns) else ""
        customer_code_str = _to_clean_str(raw_cust_code)

        raw_desc = df.iat[i, col_map["description"]] if 0 <= col_map["description"] < len(df.columns) else ""
        desc_str = _to_clean_str(raw_desc)

        # 레코드 구성
        item = {
            "전표일자": date_str,
            "전표번호": voucher_int,
            "구분": entry_type_str,
            "Code": account_code_int,
            "계정과목": acc_name,
            "차변": debit_int,
            "대변": credit_int,
            "거래처": customer_str,
            "거래처Code": customer_code_str,
            "적요": desc_str
        }
        records.append(item)

    logger.info("[JOURNAL_CONVERTER] 분개장 변환 완료: 총 %d건 추출", len(records))

    if output_json_path:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info("[JOURNAL_CONVERTER] JSON 파일 저장 완료: %s", output_json_path)

    return records


def convert_journal_excel_to_json(excel_path: str, output_json_path: Optional[str] = None) -> str:
    """
    분개장 엑셀 파일을 읽어 JSON 문자열로 변환(및 파일 저장)하는 편의 함수
    """
    records = parse_journal_entries(excel_path, output_json_path)
    return json.dumps(records, ensure_ascii=False, indent=2)


def parse_general_ledger_entries(
    file_or_df: Union[str, pd.DataFrame],
    default_year: Optional[str] = None,
    output_json_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    계정별원장(다중 계정과목 포함) 엑셀/데이터프레임을 표준 규격의 JSON 레코드 목록으로 변환합니다.

    규격:
      - 계정과목 (account_name): str (모든 행의 맨 앞에 표시)
      - 날짜 (date): 'YYYY-MM-DD'
      - 적요란 (description): str
      - 코드 (code): int (거래처/계정 코드)
      - 거래처 (customer): str
      - 차변 (debit): int
      - 대변 (credit): int
      - 잔액 (balance): int

    특징:
      - 상단 G열 등에 배치된 '계정과목 : [103] 보통예금'을 자동 감지하여 모든 하위 거래에 일괄 매핑
      - '월계', '누계', '[전기이월]' 등 소계/누계 행은 자동 제거
    """
    logger.info("[GL_CONVERTER] 계정별원장 파싱 시작: %s", type(file_or_df))

    if isinstance(file_or_df, str):
        if not os.path.exists(file_or_df):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_or_df}")
        if file_or_df.endswith('.csv'):
            df = pd.read_csv(file_or_df, header=None, dtype=str)
        else:
            df = pd.read_excel(file_or_df, header=None, dtype=str)
    else:
        df = file_or_df.copy()

    # 1. 회계연도 감지 (예: 2025.01.01 ~ 2025.12.31)
    detected_year = default_year or ""
    if not detected_year:
        for r in range(min(10, len(df))):
            row_text = " ".join([_to_clean_str(x) for x in df.iloc[r].tolist()])
            m_year = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', row_text)
            if m_year:
                detected_year = m_year.group(1)
                break
    if not detected_year:
        detected_year = "2025"

    records: List[Dict[str, Any]] = []
    current_account_name = ""
    current_account_code = 0

    # 컬럼 인덱스 매핑 기본값 (-1: 미탐색)
    col_map = {
        "date": -1,
        "description": -1,
        "code": -1,
        "customer": -1,
        "debit": -1,
        "credit": -1,
        "balance": -1
    }

    for i in range(len(df)):
        row_list = df.iloc[i].tolist()
        row_str = " ".join([_to_clean_str(x) for x in row_list])

        # A. 계정과목 헤더 블록 감지: "계정과목 : [103] 보통예금" 또는 "계정과목: 보통예금"
        acc_match = re.search(r"계정과목\s*:\s*(?:\[(\d+)\]\s*)?([^\n\r\t]+)", row_str)
        if acc_match:
            c_code = acc_match.group(1)
            c_name = acc_match.group(2).strip()
            # 뒤에 다른 컬럼 텍스트가 붙은 경우 정제
            c_name = re.split(r'\s{2,}', c_name)[0].strip()
            # 앞의 [코드] 패턴이 텍스트에 남아있는 경우 추가 제거
            c_name = re.sub(r'^\[\d+\]\s*', '', c_name).strip()
            
            if c_code:
                current_account_code = int(c_code)
            else:
                # 텍스트 내에서 [코드] 탐색
                inner_code = re.search(r'\[(\d+)\]', acc_match.group(0))
                current_account_code = int(inner_code.group(1)) if inner_code else 0

            current_account_name = c_name
            continue

        # B. 테이블 헤더 감지 ("날짜", "적요란", "코드", "거래처", "차변", "대변", "잔액")
        row_cells = [_to_clean_str(x).replace(" ", "") for x in row_list]
        if any("날짜" in c or "일자" in c for c in row_cells) and any("적요" in c for c in row_cells):
            for idx, c in enumerate(row_cells):
                if any(k in c for k in ["날짜", "일자", "date"]):
                    col_map["date"] = idx
                elif any(k in c for k in ["적요란", "적요", "내역", "비고", "memo"]):
                    col_map["description"] = idx
                elif any(k in c for k in ["코드", "code"]):
                    col_map["code"] = idx
                elif any(k in c for k in ["거래처", "거래처명", "customer"]):
                    col_map["customer"] = idx
                elif any(k in c for k in ["차변", "차변금액", "debit"]):
                    col_map["debit"] = idx
                elif any(k in c for k in ["대변", "대변금액", "credit"]):
                    col_map["credit"] = idx
                elif any(k in c for k in ["잔액", "기말잔액", "balance"]):
                    col_map["balance"] = idx
            continue

        # 헤더 매핑 폴백 (기본 0:날짜, 1:적요, 2:코드, 3:거래처, 4:차변, 5:대변, 6:잔액)
        d_idx = col_map["date"] if col_map["date"] != -1 else 0
        desc_idx = col_map["description"] if col_map["description"] != -1 else 1
        code_idx = col_map["code"] if col_map["code"] != -1 else 2
        cust_idx = col_map["customer"] if col_map["customer"] != -1 else 3
        deb_idx = col_map["debit"] if col_map["debit"] != -1 else 4
        crd_idx = col_map["credit"] if col_map["credit"] != -1 else 5
        bal_idx = col_map["balance"] if col_map["balance"] != -1 else 6

        if d_idx >= len(row_list):
            continue

        raw_date_val = _to_clean_str(row_list[d_idx])
        raw_desc_val = _to_clean_str(row_list[desc_idx]) if desc_idx < len(row_list) else ""

        # C. 제외 조건: '월계', '누계', '전기이월', '[전기이월]', '합계', '소계'
        combined_check = (raw_date_val + " " + raw_desc_val).replace(" ", "")
        if any(skip_word in combined_check for skip_word in ["월계", "누계", "전기이월", "이월", "소계", "합계", "총계", "날짜"]):
            continue

        # D. 유효 날짜 검증 (예: '01-31', '2025-01-31', '1/31', '2025.01.31')
        if not raw_date_val:
            continue

        date_clean = raw_date_val.replace('.', '-').replace('/', '-')
        # 1) 'MM-DD' 형식인 경우 (예: 01-31)
        m_mmdd = re.search(r'^(\d{1,2})-(\d{1,2})$', date_clean)
        if m_mmdd:
            full_date = f"{int(detected_year):04d}-{int(m_mmdd.group(1)):02d}-{int(m_mmdd.group(2)):02d}"
        else:
            # 2) 'YYYY-MM-DD' 형식이거나 날짜 파서 적용
            full_date = _parse_date_str(date_clean)
            if not full_date:
                # 숫자+날짜 조합 탐색
                m_any = re.search(r'(\d{1,2})-(\d{1,2})', date_clean)
                if m_any:
                    full_date = f"{int(detected_year):04d}-{int(m_any.group(1)):02d}-{int(m_any.group(2)):02d}"

        if not full_date:
            continue

        # E. 데이터 추출 및 타입 변환
        raw_code = row_list[code_idx] if code_idx < len(row_list) else None
        code_int = _to_int(raw_code, default=0)

        raw_cust = row_list[cust_idx] if cust_idx < len(row_list) else ""
        customer_str = _to_clean_str(raw_cust)

        raw_debit = row_list[deb_idx] if deb_idx < len(row_list) else 0
        raw_credit = row_list[crd_idx] if crd_idx < len(row_list) else 0
        raw_balance = row_list[bal_idx] if bal_idx < len(row_list) else 0

        debit_int = _to_int(raw_debit, default=0)
        credit_int = _to_int(raw_credit, default=0)
        balance_int = _to_int(raw_balance, default=0)

        # 레코드 구성: 계정과목코드, 계정과목을 맨 앞열에 배치
        item = {
            "계정과목코드": current_account_code,
            "계정과목": current_account_name or "미분류계정",
            "날짜": full_date,
            "적요란": raw_desc_val,
            "코드": code_int,
            "거래처": customer_str,
            "차변": debit_int,
            "대변": credit_int,
            "잔액": balance_int
        }
        records.append(item)

    logger.info("[GL_CONVERTER] 계정별원장 변환 완료: 총 %d건 추출", len(records))

    if output_json_path:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info("[GL_CONVERTER] JSON 파일 저장 완료: %s", output_json_path)

    return records


def convert_general_ledger_excel_to_json(excel_path: str, output_json_path: Optional[str] = None) -> str:
    """
    계정별원장 엑셀 파일을 읽어 JSON 문자열로 변환(및 파일 저장)하는 편의 함수
    """
    records = parse_general_ledger_entries(excel_path, output_json_path=output_json_path)
    return json.dumps(records, ensure_ascii=False, indent=2)


def parse_subledger_entries(
    file_or_df: Union[str, pd.DataFrame],
    output_json_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    거래처원장(총괄잔액 다중 거래처 블록 포함) 엑셀/데이터프레임을 표준 규격의 JSON 레코드 목록으로 변환합니다.

    규격:
      - 거래처코드: int (예: 110)
      - 거래처명: str (예: '유진산업')
      - 계정과목코드: int (예: 135)
      - 계정과목명: str (예: '부가세대급금')
      - 전기(월)이월: int (예: 0)
      - 차변: int (예: 1582000)
      - 대변: int (예: 0)
      - 잔액: int (예: 1582000)

    특징:
      - 상단 G열 등에 배치된 '거래처 : [000110] 유진산업'을 자동 감지하여 모든 하위 계정 행에 매핑
      - '[합계]', '[소계]', '[누계]' 등 합계 행은 자동 제거
    """
    logger.info("[SUBLEDGER_CONVERTER] 거래처원장 파싱 시작: %s", type(file_or_df))

    if isinstance(file_or_df, str):
        if not os.path.exists(file_or_df):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_or_df}")
        if file_or_df.endswith('.csv'):
            df = pd.read_csv(file_or_df, header=None, dtype=str)
        else:
            df = pd.read_excel(file_or_df, header=None, dtype=str)
    else:
        df = file_or_df.copy()

    records: List[Dict[str, Any]] = []
    current_cust_code = 0
    current_cust_name = ""

    # 컬럼 인덱스 매핑 기본값
    col_map = {
        "acc_code": -1,
        "acc_name": -1,
        "prior": -1,
        "debit": -1,
        "credit": -1,
        "balance": -1
    }

    for i in range(len(df)):
        row_list = df.iloc[i].tolist()
        row_str = " ".join([_to_clean_str(x) for x in row_list])

        # A. 거래처 헤더 블록 감지: "거래처 : [000110] 유진산업" 또는 "거래처: 유진산업"
        cust_match = re.search(r"거래처\s*:\s*(?:\[(\w+)\]\s*)?([^\n\r\t]+)", row_str)
        if cust_match:
            c_code = cust_match.group(1)
            c_name = cust_match.group(2).strip()
            c_name = re.split(r'\s{2,}', c_name)[0].strip()
            c_name = re.sub(r'^\[\w+\]\s*', '', c_name).strip()

            if c_code:
                current_cust_code = _to_int(c_code, default=0)
            else:
                inner_code = re.search(r'\[(\w+)\]', cust_match.group(0))
                current_cust_code = _to_int(inner_code.group(1), default=0) if inner_code else 0

            current_cust_name = c_name
            continue

        # B. 테이블 헤더 감지 ("코드", "계정과목명", "전기(월)이월", "차변", "대변", "잔액")
        row_cells = [_to_clean_str(x).replace(" ", "") for x in row_list]
        if any("코드" in c for c in row_cells) and any("계정과목" in c or "과목" in c for c in row_cells):
            for idx, c in enumerate(row_cells):
                if any(k in c for k in ["코드", "계정코드", "code"]):
                    col_map["acc_code"] = idx
                elif any(k in c for k in ["계정과목명", "계정과목", "과목명", "과목", "account"]):
                    col_map["acc_name"] = idx
                elif any(k in c for k in ["전기(월)이월", "전기이월", "전월이월", "이월", "기초", "prior"]):
                    col_map["prior"] = idx
                elif any(k in c for k in ["차변", "차변금액", "debit"]):
                    col_map["debit"] = idx
                elif any(k in c for k in ["대변", "대변금액", "credit"]):
                    col_map["credit"] = idx
                elif any(k in c for k in ["잔액", "기말잔액", "balance"]):
                    col_map["balance"] = idx
            continue

        # 헤더 매핑 폴백 (기본 0:코드, 1:과목명, 2:이월, 3:차변, 4:대변, 5:잔액)
        code_idx = col_map["acc_code"] if col_map["acc_code"] != -1 else 0
        name_idx = col_map["acc_name"] if col_map["acc_name"] != -1 else 1
        prior_idx = col_map["prior"] if col_map["prior"] != -1 else 2
        deb_idx = col_map["debit"] if col_map["debit"] != -1 else 3
        crd_idx = col_map["credit"] if col_map["credit"] != -1 else 4
        bal_idx = col_map["balance"] if col_map["balance"] != -1 else 5

        if code_idx >= len(row_list) or name_idx >= len(row_list):
            continue

        raw_code_val = _to_clean_str(row_list[code_idx])
        raw_name_val = _to_clean_str(row_list[name_idx])

        # C. 제외 조건: '[합계]', '[소계]', '[누계]', '합계', '소계', '코드'
        combined_check = (raw_code_val + " " + raw_name_val).replace(" ", "")
        if any(skip_word in combined_check for skip_word in ["합계", "소계", "총계", "누계", "월계", "코드", "계정과목"]):
            continue

        # D. 계정코드 확인 (3자리 이상 숫자 또는 유효 계정코드)
        acc_code_int = _to_int(raw_code_val, default=0)
        if acc_code_int == 0 and not raw_name_val:
            continue

        if not raw_name_val:
            continue

        # E. 데이터 추출 및 타입 변환
        raw_prior = row_list[prior_idx] if prior_idx < len(row_list) else 0
        raw_debit = row_list[deb_idx] if deb_idx < len(row_list) else 0
        raw_credit = row_list[crd_idx] if crd_idx < len(row_list) else 0
        raw_balance = row_list[bal_idx] if bal_idx < len(row_list) else 0

        prior_int = _to_int(raw_prior, default=0)
        debit_int = _to_int(raw_debit, default=0)
        credit_int = _to_int(raw_credit, default=0)
        balance_int = _to_int(raw_balance, default=0)

        # 레코드 구성
        item = {
            "거래처코드": current_cust_code,
            "거래처명": current_cust_name or "미분류거래처",
            "코드": acc_code_int,
            "계정과목명": raw_name_val,
            "전기(월)이월": prior_int,
            "차변": debit_int,
            "대변": credit_int,
            "잔액": balance_int
        }
        records.append(item)

    logger.info("[SUBLEDGER_CONVERTER] 거래처원장 변환 완료: 총 %d건 추출", len(records))

    if output_json_path:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info("[SUBLEDGER_CONVERTER] JSON 파일 저장 완료: %s", output_json_path)

    return records


def convert_subledger_excel_to_json(excel_path: str, output_json_path: Optional[str] = None) -> str:
    """
    거래처원장 엑셀 파일을 읽어 JSON 문자열로 변환(및 파일 저장)하는 편의 함수
    """
    records = parse_subledger_entries(excel_path, output_json_path=output_json_path)
    return json.dumps(records, ensure_ascii=False, indent=2)


