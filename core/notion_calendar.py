# -*- coding: utf-8 -*-
import os
import re
import time
import datetime
import requests
from core.extensions import (
    NOTION_API_BASE_URL, NOTION_API_VERSION, NOTION_TODO_DATABASE_ID, logger
)

# 인메모리 캐시 (Notion API Rate limit 방지 및 빠른 응답 지원)
_ICS_CACHE = {
    'data': None,
    'timestamp': 0,
    'ttl': 300  # 5분 캐시
}


def _notion_plain_text(property_value):
    if not property_value:
        return ''
    property_type = property_value.get('type')
    value = property_value.get(property_type)
    if property_type in ('title', 'rich_text'):
        return ''.join(item.get('plain_text', '') for item in (value or []))
    if property_type in ('select', 'status'):
        return (value or {}).get('name', '')
    if property_type == 'multi_select':
        return [item.get('name', '') for item in (value or [])]
    if property_type in ('url', 'email', 'phone_number'):
        return value or ''
    if property_type == 'formula' and isinstance(value, dict):
        formula_type = value.get('type')
        return str(value.get(formula_type, '') or '')
    return str(value or '') if value is not None else ''


def _notion_checkbox(property_value):
    if not property_value:
        return False
    if property_value.get('type') == 'checkbox':
        return bool(property_value.get('checkbox'))
    val_str = str(property_value).strip().lower()
    return val_str in ('true', 'yes', '1', 'y')


def fetch_notion_schedule_events(force_refresh=False):
    """
    Notion Todo/Schedule 데이터베이스에서 모든 일정을 페이징하여 조회합니다.
    5분간 캐시되며 force_refresh=True인 경우 즉시 Notion API를 재호출합니다.
    """
    now = time.time()
    if not force_refresh and _ICS_CACHE['data'] is not None and (now - _ICS_CACHE['timestamp'] < _ICS_CACHE['ttl']):
        logger.info("[CALENDAR] Returning cached Notion schedule events (%d items)", len(_ICS_CACHE['data']))
        return _ICS_CACHE['data']

    token = os.getenv('NOTION_ACCESS_TOKEN', '').strip()
    database_id = os.getenv('NOTION_TODO_DATABASE_ID', NOTION_TODO_DATABASE_ID).strip()
    if not token:
        logger.error("[CALENDAR] NOTION_ACCESS_TOKEN is missing in environment variables.")
        raise RuntimeError("NOTION_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.")
    if not database_id:
        logger.error("[CALENDAR] NOTION_TODO_DATABASE_ID is missing in environment variables.")
        raise RuntimeError("NOTION_TODO_DATABASE_ID 환경변수가 설정되지 않았습니다.")

    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': NOTION_API_VERSION,
        'Content-Type': 'application/json',
    }

    payload = {
        'page_size': 100,
        'filter': {
            'property': '날짜',
            'date': {
                'is_not_empty': True
            }
        },
        'sorts': [{'property': '날짜', 'direction': 'ascending'}],
    }

    logger.info("[CALENDAR] Fetching schedule items from Notion DB: %s", database_id)
    pages = []
    has_more = True
    start_cursor = None

    while has_more:
        if start_cursor:
            payload['start_cursor'] = start_cursor
        
        try:
            response = requests.post(
                f'{NOTION_API_BASE_URL}/databases/{database_id}/query',
                headers=headers,
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            pages.extend(results)
            has_more = data.get('has_more', False)
            start_cursor = data.get('next_cursor')
        except requests.exceptions.RequestException as e:
            logger.error("[CALENDAR] Notion API query error: %s", e, exc_info=True)
            raise

    events = []
    for page in pages:
        props = page.get('properties', {})
        date_prop = props.get('날짜', {}).get('date')
        if not date_prop or not date_prop.get('start'):
            continue

        page_id = page.get('id', '')
        title = _notion_plain_text(props.get('일정과할일')) or '제목 없는 일정'
        status = _notion_plain_text(props.get('상태'))
        category = _notion_plain_text(props.get('세부내역'))
        audit_types = _notion_plain_text(props.get('감사구분'))
        if isinstance(audit_types, str):
            audit_types = [audit_types] if audit_types else []

        desc = _notion_plain_text(props.get('Description'))
        important = _notion_checkbox(props.get('중요'))
        urgent = _notion_checkbox(props.get('긴급'))
        must_do = _notion_checkbox(props.get('Must-DO'))
        completed = _notion_checkbox(props.get('완료'))
        gcal_id = _notion_plain_text(props.get('GCal_ID'))
        url = page.get('url', f"https://www.notion.so/{page_id.replace('-', '')}")
        last_edited_time = page.get('last_edited_time')
        created_time = page.get('created_time')

        events.append({
            'id': page_id,
            'title': title,
            'start': date_prop.get('start'),
            'end': date_prop.get('end'),
            'time_zone': date_prop.get('time_zone'),
            'status': status,
            'category': category,
            'audit_types': audit_types,
            'description': desc,
            'important': important,
            'urgent': urgent,
            'must_do': must_do,
            'completed': completed,
            'gcal_id': gcal_id,
            'url': url,
            'last_edited_time': last_edited_time,
            'created_time': created_time
        })

    logger.info("[CALENDAR] Successfully fetched %d schedule items from Notion.", len(events))
    _ICS_CACHE['data'] = events
    _ICS_CACHE['timestamp'] = now
    return events


def _escape_ical_text(text):
    """iCalendar RFC 5545 규격에 맞게 특수문자 치환"""
    if not text:
        return ''
    text = str(text)
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
    return text


def _parse_iso_date(dt_str):
    """ISO 날짜/시간 문자열 파싱 (YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS...)"""
    if not dt_str:
        return None, False
    # 종일 일정 형태 (YYYY-MM-DD)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', dt_str):
        parts = dt_str.split('-')
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2])), True
    # 시간 포함 형태
    try:
        clean_str = dt_str.split('.')[0] if '.' in dt_str else dt_str
        clean_str = clean_str.replace('Z', '')
        if '+' in clean_str:
            clean_str = clean_str.split('+')[0]
        dt = datetime.datetime.fromisoformat(clean_str)
        return dt, False
    except Exception:
        parts = dt_str[:10].split('-')
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2])), True


def generate_ical_feed(events, calendar_name="노션 일정 (Todo DB)"):
    """
    일정 리스트를 RFC 5545 표준 iCalendar (.ics) 포맷 문자열로 변환합니다.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LandingPage//Notion Schedule Sync//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ical_text(calendar_name)}",
        "X-WR-TIMEZONE:Asia/Seoul",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]

    for ev in events:
        start_raw = ev.get('start')
        end_raw = ev.get('end')
        if not start_raw:
            continue

        start_dt, is_all_day_start = _parse_iso_date(start_raw)
        if not start_dt:
            continue

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:notion-{ev['id']}@landing_page")
        lines.append(f"DTSTAMP:{now_utc}")

        # 종일 일정(Date-only) 처리
        if is_all_day_start:
            dtstart_str = start_dt.strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{dtstart_str}")
            
            if end_raw:
                end_dt, _ = _parse_iso_date(end_raw)
                if isinstance(end_dt, datetime.datetime):
                    end_dt = end_dt.date()
                # RFC 5545 규격상 DATE DTEND는 exclusive(종료일 불포함)이므로 +1일
                end_dt_exclusive = end_dt + datetime.timedelta(days=1)
                lines.append(f"DTEND;VALUE=DATE:{end_dt_exclusive.strftime('%Y%m%d')}")
            else:
                # 당일 1일 일정인 경우 DTEND는 start + 1일
                end_dt_exclusive = start_dt + datetime.timedelta(days=1)
                lines.append(f"DTEND;VALUE=DATE:{end_dt_exclusive.strftime('%Y%m%d')}")
        else:
            # 시간 포함 일정 처리 (Time-based)
            if isinstance(start_dt, datetime.datetime):
                lines.append(f"DTSTART;TZID=Asia/Seoul:{start_dt.strftime('%Y%m%dT%H%M%S')}")
            else:
                lines.append(f"DTSTART;VALUE=DATE:{start_dt.strftime('%Y%m%d')}")

            if end_raw:
                end_dt, is_all_day_end = _parse_iso_date(end_raw)
                if isinstance(end_dt, datetime.datetime):
                    lines.append(f"DTEND;TZID=Asia/Seoul:{end_dt.strftime('%Y%m%dT%H%M%S')}")
                elif is_all_day_end:
                    end_dt_exclusive = end_dt + datetime.timedelta(days=1)
                    lines.append(f"DTEND;VALUE=DATE:{end_dt_exclusive.strftime('%Y%m%d')}")
            else:
                # end가 없으면 기본 1시간 후로 설정
                if isinstance(start_dt, datetime.datetime):
                    end_dt = start_dt + datetime.timedelta(hours=1)
                    lines.append(f"DTEND;TZID=Asia/Seoul:{end_dt.strftime('%Y%m%dT%H%M%S')}")

        # 제목 (중요/긴급 표기 포함)
        title_prefix = []
        if ev.get('important'):
            title_prefix.append("⭐중요")
        if ev.get('urgent'):
            title_prefix.append("🔥긴급")
        if ev.get('audit_types'):
            title_prefix.append(f"[{','.join(ev['audit_types'])}]")
        elif ev.get('category'):
            title_prefix.append(f"[{ev['category']}]")
        
        full_title = f"{' '.join(title_prefix)} {ev['title']}".strip()
        lines.append(f"SUMMARY:{_escape_ical_text(full_title)}")

        # 상세 설명 구성
        desc_parts = []
        if ev.get('status'):
            desc_parts.append(f"상태: {ev['status']}")
        if ev.get('audit_types'):
            desc_parts.append(f"감사구분: {', '.join(ev['audit_types'])}")
        if ev.get('category'):
            desc_parts.append(f"세부내역: {ev['category']}")
        if ev.get('description'):
            desc_parts.append(f"내용: {ev['description']}")
        if ev.get('url'):
            desc_parts.append(f"노션 링크: {ev['url']}")
        
        desc_text = "\n".join(desc_parts)
        if desc_text:
            lines.append(f"DESCRIPTION:{_escape_ical_text(desc_text)}")

        if ev.get('url'):
            lines.append(f"URL:{ev['url']}")

        lines.append("STATUS:CONFIRMED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
