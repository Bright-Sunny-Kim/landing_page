# -*- coding: utf-8 -*-
"""
DSD File Parser & Manager (core/dsd_manager.py)
금융감독원 DART 표준 .dsd (전자공시 감사보고서 패키지) 역추출 및 파싱 엔진

- ZIP 아카이브 해제 (meta.xml, contents.xml)
- UTF-8 / CP949 다중 인코딩 자동 처리
- 비교표시 재무제표 4종 (재무상태표, 손익계산서, 자본변동표, 현금흐름표) 추출
- K-GAAP 주석(Notes 1~N) 텍스트 및 세부 표 데이터 구조화 추출
"""

import io
import re
import zipfile
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def clean_amount(val: Any) -> Optional[int]:
    """
    재무제표 셀 문자열을 정수 금액으로 변환합니다.
    (예: '3,996,872,317' -> 3996872317, '(65,815,843)' -> -65815843, '-' -> 0)
    """
    if val is None:
        return None
    
    if isinstance(val, (int, float)):
        return int(val)
        
    s = str(val).strip().replace(',', '')
    if not s or s == '-' or s == '0':
        return 0
        
    # 괄호로 감싸진 음수 처리
    m = re.match(r'^\((.+)\)$', s)
    if m:
        try:
            return -int(m.group(1))
        except ValueError:
            return None
            
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return None


def extract_dsd_archive(dsd_input: Union[str, bytes, io.BytesIO]) -> Dict[str, bytes]:
    """
    .dsd 파일(경로 또는 bytes/BytesIO)에서 ZIP 압축을 해제하여
    파일명: 바이트 딕셔너리로 반환합니다.
    """
    logger.info("[DSD Parser] Starting DSD archive extraction...")
    extracted_files = {}
    
    try:
        if isinstance(dsd_input, str):
            with zipfile.ZipFile(dsd_input, 'r') as z:
                for name in z.namelist():
                    extracted_files[name] = z.read(name)
        elif isinstance(dsd_input, bytes):
            with zipfile.ZipFile(io.BytesIO(dsd_input), 'r') as z:
                for name in z.namelist():
                    extracted_files[name] = z.read(name)
        elif isinstance(dsd_input, io.BytesIO):
            with zipfile.ZipFile(dsd_input, 'r') as z:
                for name in z.namelist():
                    extracted_files[name] = z.read(name)
        else:
            raise ValueError(f"Unsupported dsd_input type: {type(dsd_input)}")
            
        logger.info("[DSD Parser] Archive extraction successful. Files: %s", list(extracted_files.keys()))
        return extracted_files
    except Exception as e:
        logger.error("[DSD Parser] Failed to extract DSD archive: %s", str(e), exc_info=True)
        raise


def safe_decode_xml(raw_bytes: bytes) -> str:
    """
    XML 바이트를 UTF-8 또는 CP949/EUC-KR로 안전하게 디코딩합니다.
    """
    for enc in ['utf-8', 'cp949', 'euc-kr']:
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    # 최후의 수단: 오류 무시 디코딩
    logger.warning("[DSD Parser] Fallback decoding with ignore errors")
    return raw_bytes.decode('utf-8', errors='ignore')


def parse_meta_xml(meta_bytes_or_str: Union[bytes, str]) -> Dict[str, Any]:
    """
    meta.xml에서 기업명, CIK, 서식 버전 등 메타데이터를 파싱합니다.
    """
    logger.debug("[DSD Parser] Parsing meta.xml...")
    meta_info = {
        "company_name": "",
        "cik": "",
        "doc_ver": "",
        "generator": "",
        "schema": ""
    }
    
    try:
        xml_str = meta_bytes_or_str if isinstance(meta_bytes_or_str, str) else safe_decode_xml(meta_bytes_or_str)
        root = ET.fromstring(xml_str.encode('utf-8'))
        
        doc_header = root.find('.//DOCUMENT-HEADER')
        if doc_header is not None:
            meta_info["company_name"] = doc_header.attrib.get('regname', '')
            meta_info["cik"] = doc_header.attrib.get('regcik', '')
            
        generator = root.find('.//GENERATOR')
        if generator is not None:
            meta_info["generator"] = generator.attrib.get('editver', '')
            meta_info["schema"] = generator.attrib.get('schema', '')
            
        doc_info = root.find('.//DOCUMENT-INFO')
        if doc_info is not None:
            meta_info["doc_ver"] = doc_info.attrib.get('docver', '')
            
        logger.info("[DSD Parser] meta.xml parsed: Company=%s, CIK=%s", meta_info["company_name"], meta_info["cik"])
    except Exception as e:
        logger.error("[DSD Parser] Failed to parse meta.xml: %s", str(e), exc_info=True)
        
    return meta_info


def _parse_table_rows(table_el: ET.Element) -> List[List[str]]:
    """TABLE 엘리먼트 내의 모든 행(TR)과 셀(TH/TD/TE 등) 텍스트를 2차원 리스트로 반환합니다."""
    rows = []
    for tr in table_el.findall('.//TR'):
        row_cells = [''.join(c.itertext()).strip().replace('&cr;', ' ') for c in tr]
        if any(row_cells):
            rows.append(row_cells)
    return rows


def parse_dsd_financial_statements(contents_bytes_or_str: Union[bytes, str]) -> Dict[str, Any]:
    """
    contents.xml에서 4대 재무제표 및 주석을 정밀 추출합니다.
    """
    logger.info("[DSD Parser] Parsing contents.xml financial statements & notes...")
    result = {
        "report_header": {},
        "balance_sheet": {"periods": {}, "items": [], "summary": {}},
        "income_statement": {"periods": {}, "items": [], "summary": {}},
        "changes_in_equity": {"periods": {}, "items": []},
        "cash_flow": {"periods": {}, "items": []},
        "notes": []
    }
    
    try:
        xml_str = contents_bytes_or_str if isinstance(contents_bytes_or_str, str) else safe_decode_xml(contents_bytes_or_str)
        # DART 전용 &cr; 엔티티를 표준 개행문자로 사전 치환하여 XML 파싱 에러 방지
        xml_clean = xml_str.replace('&cr;', '&#10;')
        root = ET.fromstring(xml_clean.encode('utf-8'))
        
        # 1. 문서 헤더 정보 추출
        doc_header = root.find('.//DOCUMENT-HEADER')
        if doc_header is not None:
            doc_name_el = doc_header.find('DOCUMENT-NAME')
            company_el = doc_header.find('COMPANY-NAME')
            result["report_header"] = {
                "doc_name": ''.join(doc_name_el.itertext()).strip() if doc_name_el is not None else "감사보고서",
                "company_name": ''.join(company_el.itertext()).strip() if company_el is not None else "",
                "cik": company_el.attrib.get('AREGCIK', '') if company_el is not None else ""
            }
            
        # 2. 4대 재무제표 추출 (INSERTION 내 TITLE 및 TABLE)
        for insertion in root.findall('.//INSERTION'):
            title_el = insertion.find('.//TITLE')
            if title_el is None:
                continue
            title_text = ''.join(title_el.itertext()).strip()
            tables = insertion.findall('.//TABLE')
            
            # (1) 재무상태표
            if '재 무 상 태 표' in title_text or '재무상태표' in title_text:
                logger.info("[DSD Parser] Found Balance Sheet section")
                if len(tables) >= 2:
                    header_rows = _parse_table_rows(tables[0])
                    body_rows = _parse_table_rows(tables[1])
                    
                    # 기수/기간 파싱
                    for r in header_rows:
                        text = ' '.join(r)
                        if '당' in text or '현재' in text:
                            result["balance_sheet"]["periods"]["header"] = text
                            
                    bs_items = []
                    for r in body_rows:
                        if len(r) < 2 or r[0] == '과 목':
                            continue
                        name = r[0]
                        if len(r) >= 5:
                            cur_amt = clean_amount(r[2]) if clean_amount(r[2]) is not None else clean_amount(r[1])
                            pri_amt = clean_amount(r[4]) if clean_amount(r[4]) is not None else clean_amount(r[3])
                        elif len(r) >= 3:
                            cur_amt = clean_amount(r[1])
                            pri_amt = clean_amount(r[2])
                        else:
                            cur_amt = clean_amount(r[1])
                            pri_amt = None
                        
                        bs_items.append({
                            "account_name": name,
                            "current_amount": cur_amt,
                            "prior_amount": pri_amt
                        })
                        
                        # 주요 요약 지표 저장
                        if '자산총계' in name:
                            result["balance_sheet"]["summary"]["current_total_assets"] = cur_amt
                            result["balance_sheet"]["summary"]["prior_total_assets"] = pri_amt
                        elif '부채총계' in name:
                            result["balance_sheet"]["summary"]["current_total_liabilities"] = cur_amt
                            result["balance_sheet"]["summary"]["prior_total_liabilities"] = pri_amt
                        elif '자본총계' in name and '부채' not in name:
                            result["balance_sheet"]["summary"]["current_total_equity"] = cur_amt
                            result["balance_sheet"]["summary"]["prior_total_equity"] = pri_amt
                            
                    result["balance_sheet"]["items"] = bs_items

            # (2) 손익계산서
            elif '손 익 계 산 서' in title_text or '손익계산서' in title_text:
                logger.info("[DSD Parser] Found Income Statement section")
                if len(tables) >= 2:
                    body_rows = _parse_table_rows(tables[1])
                    is_items = []
                    for r in body_rows:
                        if len(r) < 2 or r[0] == '과 목':
                            continue
                        name = r[0]
                        if len(r) >= 5:
                            cur_amt = clean_amount(r[2]) if clean_amount(r[2]) is not None else clean_amount(r[1])
                            pri_amt = clean_amount(r[4]) if clean_amount(r[4]) is not None else clean_amount(r[3])
                        elif len(r) >= 3:
                            cur_amt = clean_amount(r[1])
                            pri_amt = clean_amount(r[2])
                        else:
                            cur_amt = clean_amount(r[1])
                            pri_amt = None
                        
                        is_items.append({
                            "account_name": name,
                            "current_amount": cur_amt,
                            "prior_amount": pri_amt
                        })
                        
                        # 주요 요약 지표 저장
                        if 'Ⅰ.매출액' in name or '매출액' == name:
                            result["income_statement"]["summary"]["current_revenue"] = cur_amt
                            result["income_statement"]["summary"]["prior_revenue"] = pri_amt
                        elif 'Ⅴ.영업이익' in name or '영업이익' == name:
                            result["income_statement"]["summary"]["current_operating_income"] = cur_amt
                            result["income_statement"]["summary"]["prior_operating_income"] = pri_amt
                        elif 'Ⅹ.당기순이익' in name or '당기순이익' in name or '당기순손익' in name:
                            result["income_statement"]["summary"]["current_net_income"] = cur_amt
                            result["income_statement"]["summary"]["prior_net_income"] = pri_amt
                            
                    result["income_statement"]["items"] = is_items

            # (3) 자본변동표
            elif '자 본 변 동 표' in title_text or '자본변동표' in title_text:
                if len(tables) >= 2:
                    result["changes_in_equity"]["items"] = _parse_table_rows(tables[1])
                    
            # (4) 현금흐름표
            elif '현 금 흐 름 표' in title_text or '현금흐름표' in title_text:
                if len(tables) >= 2:
                    cf_items = []
                    for r in _parse_table_rows(tables[1]):
                        if len(r) < 3 or r[0] == '과 목':
                            continue
                        cur_amt = clean_amount(r[2]) if len(r) > 2 and clean_amount(r[2]) is not None else (clean_amount(r[1]) if len(r) > 1 else None)
                        pri_amt = clean_amount(r[4]) if len(r) > 4 and clean_amount(r[4]) is not None else (clean_amount(r[3]) if len(r) > 3 else None)
                        cf_items.append({
                            "account_name": r[0],
                            "current_amount": cur_amt,
                            "prior_amount": pri_amt
                        })
                    result["cash_flow"]["items"] = cf_items

        # 3. 주석 (Notes) 추출
        for sec in root.findall('.//SECTION-2'):
            sec_title = sec.find('.//TITLE')
            sec_t = ''.join(sec_title.itertext()).strip() if sec_title is not None else ''
            if '주석' in sec_t:
                logger.info("[DSD Parser] Extracting Notes section...")
                current_note = {"note_number": 0, "title": "", "paragraphs": [], "tables": []}
                notes_list = []
                
                for elem in sec:
                    if elem.tag == 'P':
                        p_text = ''.join(elem.itertext()).replace('&cr;', '\n').strip()
                        if not p_text:
                            continue
                        
                        # 첫 줄 기준 주석 번호 감지 (예: '1. 회사의 개요', '2. 중요한 회계처리 방침' 등)
                        first_line = p_text.split('\n')[0].strip()
                        m = re.match(r'^(\d+)\.\s*(.+)', first_line)
                        if m:
                            if current_note["title"]:
                                notes_list.append(current_note)
                            current_note = {
                                "note_number": int(m.group(1)),
                                "title": f"{m.group(1)}. {m.group(2).strip()}",
                                "paragraphs": [p_text],
                                "tables": []
                            }
                        else:
                            if current_note["title"]:
                                current_note["paragraphs"].append(p_text)
                    elif elem.tag == 'TABLE':
                        t_rows = _parse_table_rows(elem)
                        if t_rows and current_note["title"]:
                            current_note["tables"].append(t_rows)
                            
                if current_note["title"]:
                    notes_list.append(current_note)
                    
                result["notes"] = notes_list
                logger.info("[DSD Parser] Extracted %d notes", len(notes_list))

        logger.info("[DSD Parser] Financial statement extraction complete.")
    except Exception as e:
        logger.error("[DSD Parser] Failed to parse financial statements: %s", str(e), exc_info=True)
        
    return result


def parse_dsd_file(dsd_input: Union[str, bytes, io.BytesIO]) -> Dict[str, Any]:
    """
    DSD 파일 종합 파싱 메인 엔트리 함수입니다.
    """
    logger.info("[DSD Parser] Starting complete DSD parsing pipeline...")
    
    try:
        archive_files = extract_dsd_archive(dsd_input)
        
        meta_info = {}
        if 'meta.xml' in archive_files:
            meta_info = parse_meta_xml(archive_files['meta.xml'])
            
        fs_info = {}
        if 'contents.xml' in archive_files:
            fs_info = parse_dsd_financial_statements(archive_files['contents.xml'])
            
        company_name = meta_info.get("company_name") or fs_info.get("report_header", {}).get("company_name", "미확인회사")
        cik = meta_info.get("cik") or fs_info.get("report_header", {}).get("cik", "")
        
        return {
            "success": True,
            "company_name": company_name,
            "cik": cik,
            "metadata": meta_info,
            "financial_statements": {
                "balance_sheet": fs_info.get("balance_sheet", {}),
                "income_statement": fs_info.get("income_statement", {}),
                "changes_in_equity": fs_info.get("changes_in_equity", {}),
                "cash_flow": fs_info.get("cash_flow", {})
            },
            "notes_count": len(fs_info.get("notes", [])),
            "notes": fs_info.get("notes", [])
        }
    except Exception as e:
        logger.error("[DSD Parser] Critical failure in parse_dsd_file: %s", str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
