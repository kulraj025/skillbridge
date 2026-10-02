"""Structured field extraction: salary, hours, deadline, experience, education.

Every parser in this module returns a dict with a ``value`` key rather than
raising, and every parse records the original text it came from. Three reasons:

- A listing that states a salary in an unrecognised format should surface the
  text, not be dropped.
- "면협" (negotiable) is a real answer and must not be read as zero.
- Deadline strings often omit the year, so the parser needs ``posted_at`` to
  infer it, and a deadline that resolves into the past must roll forward a
  year rather than mark a live listing expired.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

# --- Korean number parsing -------------------------------------------------

_KOREAN_UNITS = {"만": 10_000, "천": 1_000, "억": 100_000_000}

_DIGITS = {
    "영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4,
    "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9,
}

_COMPILED_DIGITS = {
    "십": 10, "열": 10,
    "스물": 20, "서른": 30, "마흔": 40, "쉰": 50, "예순": 60,
    "일흔": 70, "여든": 80, "아흔": 90,
}

_NAMED = {
    "열하나": 11, "열둘": 12, "열셋": 13, "열넷": 14, "열다섯": 15,
    "열여섯": 16, "열일곱": 17, "열여덟": 18, "열아홉": 19,
}

_NUMBER_TOKEN = re.compile(r"[0-9][0-9,\.]*|[가-힣]+")


def parse_korean_number(text: str) -> Optional[float]:
    """Parse ``12000``, ``1.2만``, ``3만원``, ``1억 2천`` into a float.

    Korean job ads mix plain digits with 만/천 units constantly, so a plain
    ``int()`` misses most real salary strings.
    """

    if text is None:
        return None

    source = str(text).strip()
    if not source:
        return None

    if re.fullmatch(r"[0-9][0-9,\.]*", source):
        return float(source.replace(",", ""))

    total = 0.0
    current = 0.0
    matched_any = False

    for token in _NUMBER_TOKEN.findall(source):
        if re.fullmatch(r"[0-9][0-9,\.]*", token):
            current += float(token.replace(",", ""))
            matched_any = True
            continue

        multiplier = _parse_hangul_token(token)
        if multiplier is None:
            continue

        if current == 0:
            current = 1
        total += current * multiplier
        current = 0.0
        matched_any = True

    if not matched_any:
        return None
    return total + current


def _parse_hangul_token(token: str) -> Optional[float]:
    """Return the scale a Hangul token contributes.

    In a mixed-unit token the *last* unit character is the magnitude and
    everything before it builds the number, so ``천만`` is 1000 x 10000 =
    10,000,000 rather than 1000 + 10000. That is why ``2천만`` is 20,000,000 and
    why ``1억 2천만`` is 120,000,000.

    Tokens with no unit character are ordinary Korean numerals and are added
    rather than scaled.
    """

    if not token:
        return None

    unit_positions = [index for index, char in enumerate(token) if char in _KOREAN_UNITS]

    if not unit_positions:
        return _parse_korean_numeral(token)

    last_unit_position = unit_positions[-1]

    number = 1.0
    for char in token[:last_unit_position]:
        if char in _KOREAN_UNITS:
            number *= _KOREAN_UNITS[char]
            continue
        digit = _DIGITS.get(char)
        if digit is None:
            return None
        number = number * 10 + digit

    return number * _KOREAN_UNITS[token[last_unit_position]]


def _parse_korean_numeral(token: str) -> Optional[float]:
    if token in _COMPILED_DIGITS:
        return float(_COMPILED_DIGITS[token])
    if token in _NAMED:
        return float(_NAMED[token])
    if all(char in _DIGITS for char in token):
        return float("".join(str(_DIGITS[char]) for char in token))
    return None


# --- salary ----------------------------------------------------------------

SALARY_NEGOTIABLE = ("면협", "면의", "협상", "negotiable", "to be discussed")
SALARY_PATTERNS = (
    ("hour", ("시급", "시 급", "시간급", "hourly", "per hour")),
    ("month", ("월급", "월 급", "월급여", "monthly", "per month")),
    ("year", ("연봉", "연봉여", "연 급", "annual", "per year")),
)

_SALARY_RANGE = re.compile(r"([0-9][0-9,\.]*)\s*([가-힣]*)\s*원?\s*[-~～]\s*([0-9][0-9,\.]*)")
_SALARY_SINGLE = re.compile(r"([0-9][0-9,\.]*)\s*([0-9,]*\s*만?)\s*원")

_UNIT_WORDS = {"": 1, "만": 10_000, "억": 100_000_000}


def _salary_unit_for(text: str) -> Optional[str]:
    lowered = text.lower()
    for unit, markers in SALARY_PATTERNS:
        for marker in markers:
            if marker in lowered:
                return unit
    return None


def _apply_unit_suffix(value: float, suffix: str) -> float:
    suffix = (suffix or "").strip()
    if suffix in _UNIT_WORDS:
        return value * _UNIT_WORDS[suffix]
    if suffix in _KOREAN_UNITS:
        return value * _KOREAN_UNITS[suffix]
    return value


def extract_salary(description: str) -> Dict[str, Any]:
    """Extract a salary range, unit, and the original text."""

    text = description or ""
    if not text.strip():
        return {"value": None, "min": None, "max": None, "unit": None, "text": None}

    unit = _salary_unit_for(text)
    if any(marker in text.lower() for marker in SALARY_NEGOTIABLE):
        return {
            "value": None,
            "min": None,
            "max": None,
            "unit": unit,
            "text": _matched_salary_text(text),
            "negotiable": True,
        }

    span = _SALARY_RANGE.search(text)
    if span:
        low = parse_korean_number(span.group(1))
        high = parse_korean_number(span.group(3))
        if low is not None and high is not None:
            low = _apply_unit_suffix(low, span.group(2))
            high = _apply_unit_suffix(high, "")
            if low > high:
                low, high = high, low
            return {
                "value": (low + high) / 2.0,
                "min": low,
                "max": high,
                "unit": unit,
                "text": span.group(0).strip(),
                "negotiable": False,
            }

    single = _SALARY_SINGLE.search(text)
    if single:
        amount = parse_korean_number(single.group(1) + single.group(2))
        if amount is not None:
            return {
                "value": amount,
                "min": amount,
                "max": amount,
                "unit": unit,
                "text": single.group(0).strip(),
                "negotiable": False,
            }

    return {
        "value": None,
        "min": None,
        "max": None,
        "unit": unit,
        "text": _matched_salary_text(text),
        "negotiable": False,
    }


def _matched_salary_text(text: str) -> Optional[str]:
    for pattern in (_SALARY_RANGE, _SALARY_SINGLE):
        found = pattern.search(text)
        if found:
            return found.group(0).strip()
    return None


# --- working hours ---------------------------------------------------------

_HOURS_WEEKLY = re.compile(r"주\s*(\d+)\s*(?:시간|시간\s*근무|hr)", re.IGNORECASE)
_HOURS_TIMES = re.compile(r"주\s*(\d+)\s*회", re.IGNORECASE)
_HOURS_DAILY = re.compile(r"일\s*(\d+)\s*시간", re.IGNORECASE)
_TIME_RANGE = re.compile(
    r"(오전|오후|am|pm)?\s*(\d{1,2})\s*시\s*(?:부터|~|～|-|–|to)?\s*"
    r"(오전|오후|am|pm)?\s*(\d{1,2})\s*시"
)
_WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")

WEEKDAY_LABELS = {
    "월": "mon", "화": "tue", "수": "wed", "목": "thu",
    "금": "fri", "토": "sat", "일": "sun",
}

_WEEKDAY_ORDER = ("월", "화", "수", "목", "금", "토", "일")

_DAY_SUFFIXED = re.compile(r"([월화수목토일])요일")
# A glued run of weekday characters, e.g. "월화수목".
_DAY_RUN = re.compile(r"월화수목금?")
# A bare day character only counts when it is not glued to another Hangul
# syllable, so "금액" is not read as Friday and "수강" is not Tuesday. The
# surrounding text keeps its whitespace, because a space is the boundary that
# distinguishes "목 근무" from "목근무".
_DAY_STANDALONE = re.compile(r"(?<![가-힣])([월화수목토일])(?![가-힣])")
# Date fragments, consumed before day scanning. "10월 10일까지" contains 월 as a
# month counter, and reporting Monday because a deadline mentions October is
# exactly the kind of small wrong answer that makes a student distrust the
# whole explanation.
_DATE_MONTH = re.compile(r"\d+\s*월(?:\s*\d+\s*일)?")
_DATE_DAY = re.compile(r"월\s*\d+\s*일")


def _weekdays_in(text: str) -> List[str]:
    """Return the weekdays a listing mentions, in Monday-to-Sunday order.

    ``평일`` means weekdays and ``주말`` means the weekend. Both contain a day
    character that would otherwise be misread, so they are consumed before any
    bare day character is considered: scanning ``평일`` for ``일`` reports
    Sunday for a listing that means Monday to Friday.

    ``text`` keeps its whitespace on purpose. Stripping it first would glue
    "목 근무" into "목근무" and the day character would look like part of a
    longer word.
    """

    found = set()
    remainder = text or ""

    for match in _DAY_RUN.finditer(remainder):
        found.update(match.group(0))
    remainder = _DAY_RUN.sub("", remainder)

    for match in _DAY_SUFFIXED.finditer(remainder):
        found.add(match.group(1))
    remainder = _DAY_SUFFIXED.sub("", remainder)

    if "평일" in remainder:
        found.update(("월", "화", "수", "목", "금"))
        remainder = remainder.replace("평일", "")
    if "주말" in remainder:
        found.update(("토", "일"))
        remainder = remainder.replace("주말", "")

    remainder = _DATE_MONTH.sub(" ", remainder)
    remainder = _DATE_DAY.sub(" ", remainder)

    for match in _DAY_STANDALONE.finditer(remainder):
        found.add(match.group(1))

    return [day for day in _WEEKDAY_ORDER if day in found]


def extract_working_hours(description: str) -> Dict[str, Any]:
    """Extract weekly hours, days per week, weekdays, and a time range."""

    text = description or ""
    result: Dict[str, Any] = {
        "weekly_hours": None,
        "days_per_week": None,
        "weekdays": [],
        "start": None,
        "end": None,
        "text": None,
    }
    if not text.strip():
        return result

    weekly = _HOURS_WEEKLY.search(text)
    if weekly:
        result["weekly_hours"] = int(weekly.group(1))
        result["text"] = weekly.group(0).strip()

    times = _HOURS_TIMES.search(text)
    if times:
        result["days_per_week"] = int(times.group(1))
        if result["text"] is None:
            result["text"] = times.group(0).strip()

    daily = _HOURS_DAILY.search(text)
    if daily and result["weekly_hours"] is None:
        result["weekly_hours"] = int(daily.group(1))

    compact = re.sub(r"\s+", "", text)
    result["weekdays"] = _weekdays_in(text)

    span = _TIME_RANGE.search(compact)
    if span:
        start_meridiem = (span.group(1) or "").lower()
        end_meridiem = (span.group(3) or "").lower()
        start_hour = _to_24h(int(span.group(2)), start_meridiem)
        end_hour = _to_24h(int(span.group(4)), end_meridiem or start_meridiem)
        if start_hour is not None and end_hour is not None:
            result["start"] = "{0:02d}:00".format(start_hour)
            result["end"] = "{0:02d}:00".format(end_hour)
            if result["text"] is None:
                result["text"] = span.group(0).strip()

    return result


def _to_24h(hour: int, meridiem: str) -> Optional[int]:
    if hour > 24:
        return None
    if meridiem in ("오후", "pm"):
        if hour < 12:
            return hour + 12
        return hour if hour <= 24 else None
    if meridiem in ("오전", "am"):
        return 0 if hour == 12 else hour
    if hour <= 24:
        return hour
    return None


# --- experience and education ---------------------------------------------

_EXPERIENCE_YEARS = re.compile(r"(\d+)\s*년\s*(?:이상)?\s*(?:의)?\s*(?:경력|경험)", re.IGNORECASE)
_EXPERIENCE_REVERSED = re.compile(r"(?:경력|경험)\s*(\d+)\s*년", re.IGNORECASE)
_EXPERIENCE_FRESH = ("신입", "경력 무관", "무관", "신입 가능", "经验不限", "no experience")

_EDUCATION = (
    ("graduate", ("대학원", "graduate student", "석사", "박사")),
    ("bachelor", ("4년제", "학부", "undergraduate", "bachelor")),
    ("high_school", ("고등학교", "고등학생", "high school")),
)


def extract_experience(description: str) -> Dict[str, Any]:
    """Extract required years of experience, or ``null`` when not stated."""

    text = description or ""
    result: Dict[str, Any] = {"years": None, "text": None, "fresh_graduate_ok": False}
    if not text.strip():
        return result

    lowered = text.lower()
    for marker in _EXPERIENCE_FRESH:
        if marker in lowered:
            result["fresh_graduate_ok"] = True
            result["text"] = marker
            return result

    for pattern in (_EXPERIENCE_YEARS, _EXPERIENCE_REVERSED):
        found = pattern.search(text)
        if found:
            result["years"] = int(found.group(1))
            result["text"] = found.group(0).strip()
            return result

    return result


def extract_education(description: str) -> Dict[str, Any]:
    """Extract the highest education level the listing mentions."""

    text = description or ""
    result: Dict[str, Any] = {"level": None, "text": None}
    if not text.strip():
        return result

    lowered = text.lower()
    for level, markers in _EDUCATION:
        for marker in markers:
            if marker in lowered:
                result["level"] = level
                result["text"] = marker
                return result
    return result


# --- deadline --------------------------------------------------------------

_DEADLINE_KEYWORDS = ("접수기간", "접수 마감", "마감", "지원 마감", "deadline", "close")

_DATE_ISO = re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})")
_DATE_KO_YEAR = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DATE_KO_SHORT = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DATE_SLASH = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)")


def extract_deadline(
    description: str,
    posted_at: Optional[datetime] = None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Extract a deadline, inferring a missing year.

    Korean listings routinely omit the year. The year is taken from
    ``posted_at`` when available, and rolled forward if the result would land in
    the past, because marking a live listing expired is a much worse error than
    showing a deadline one year out.
    """

    text = description or ""
    result: Dict[str, Any] = {"value": None, "text": None, "inferred_year": False}
    if not text.strip():
        return result

    reference = today or (posted_at.date() if posted_at else date.today())
    lowered = text.lower()
    if not any(keyword in lowered for keyword in _DEADLINE_KEYWORDS):
        return result

    found = _DATE_ISO.search(text)
    if found:
        parsed = _safe_date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
        if parsed:
            result["value"] = parsed.isoformat()
            result["text"] = found.group(0).strip()
            return result

    found = _DATE_KO_YEAR.search(text)
    if found:
        parsed = _safe_date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
        if parsed:
            result["value"] = parsed.isoformat()
            result["text"] = found.group(0).strip()
            return result

    found = _DATE_KO_SHORT.search(text)
    if found:
        parsed = _resolve_short_date(int(found.group(1)), int(found.group(2)), reference)
        if parsed:
            result["value"] = parsed.isoformat()
            result["text"] = found.group(0).strip()
            result["inferred_year"] = True
            return result

    found = _DATE_SLASH.search(text)
    if found:
        month = int(found.group(1))
        day = int(found.group(2))
        if 1 <= month <= 12:
            parsed = _resolve_short_date(month, day, reference)
            if parsed:
                result["value"] = parsed.isoformat()
                result["text"] = found.group(0).strip()
                result["inferred_year"] = True
                return result

    return result


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _resolve_short_date(month: int, day: int, reference: date) -> Optional[date]:
    """Resolve a month/day pair against a reference date.

    A date that has already passed relative to the reference rolls forward a
    year, since listings are posted before their deadline.
    """

    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None

    for year in (reference.year, reference.year + 1):
        candidate = _safe_date(year, month, day)
        if candidate is None:
            continue
        if candidate >= reference - timedelta(days=1):
            return candidate
    return None
