"""International-student eligibility and language requirements.

Two hard rules govern this module.

First, eligibility is never inferred. A listing either states something about
international applicants or it does not, and the output distinguishes "stated as
accepted", "employer states a visa is required", and "not specified". There is
no fourth rendering, and in particular no path that produces advice about
whether a student may legally work in Korea.

Second, stated and inferred language requirements are kept apart. If a level was
read out of surrounding prose rather than an explicit statement, ``explicit`` is
False, so the interface can render it differently from a condition the employer
actually wrote.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Phrases the employer uses to say international applicants are accepted.
ACCEPTED_PHRASES = (
    "외국인 가능",
    "외국인 환영",
    "외국인 우대",
    "외국인 지원 가능",
    "외국인도 지원",
    "외국인 자격",
    "외국인 비자 소지자",
    "foreign residents",
    "foreigners welcome",
    "외국인 및 국내",
)

# Phrases that indicate the employer expects a visa to already exist.
VISA_REQUIRED_PHRASES = (
    "비자 필요",
    "비자 있어야",
    "비자 발급",
    "visa 필요",
    "visa required",
    "체류 자격",
    "외국인등록",
    "취업 자격",
)

# Phrases that mean the listing says nothing useful on this point.
ELIGIBILITY_DISCLAIMERS = (
    "비자 문의",
    "자격 확인",
    "상세 문의",
)

DISPLAY_ACCEPTED = "International applicants: stated as accepted by the employer."
DISPLAY_VISA = (
    "Employer states a visa is required. Check your work authorization before applying."
)
DISPLAY_UNSPECIFIED = "International-student eligibility: not specified by the source."

# Language names, Korean and English, with ISO-639-1 codes.
LANGUAGES = (
    ("korean", ("korean", "한국어", "토픽", "topik", "한글")),
    ("english", ("english", "영어", "토종", "영문")),
    ("chinese", ("chinese", "중국어", "중국")),
    ("japanese", ("japanese", "japanese", "일본어", "일본")),
    ("spanish", ("spanish", "스페인어", "스페인")),
    ("vietnamese", ("vietnamese", "베트남어", "베트남")),
    ("mongolian", ("mongolian", "몽골어", "몽골")),
    ("thai", ("thai", "태국어")),
)

# TOPIK levels 1-6, plus "level 0" wording.
_TOPIK_PATTERN = re.compile(r"(?:토픽|topik|한국어)\s*(\d)\s*급", re.IGNORECASE)
_ENGLISH_LEVEL = re.compile(
    r"(?:영어|english)\s*(?:토종\s*)?(a1|a2|b1|b2|c1|c2)", re.IGNORECASE
)


def _find_phrase(text: str, phrases) -> Optional[Dict[str, str]]:
    """Return the first matching phrase with its span, or None."""

    lowered = (text or "").lower()
    best: Optional[Dict[str, str]] = None
    for phrase in phrases:
        index = lowered.find(phrase.lower())
        if index < 0:
            continue
        if best is None or index < best["start"]:
            best = {
                "phrase": phrase,
                "start": index,
                "statement": phrase,
            }
    return best


def extract_eligibility(description: str) -> Dict[str, Any]:
    """Report what the source stated about international-student eligibility.

    Returns ``international_students_accepted`` as True, False, or None. None
    means the source said nothing, which the interface must render as
    "not specified" rather than as a negative answer.
    """

    text = description or ""
    if not text.strip():
        return {
            "international_students_accepted": None,
            "statement": None,
            "source": None,
            "display": DISPLAY_UNSPECIFIED,
        }

    accepted = _find_phrase(text, ACCEPTED_PHRASES)
    visa = _find_phrase(text, VISA_REQUIRED_PHRASES)

    if visa is not None and (accepted is None or visa["start"] < accepted["start"]):
        return {
            "international_students_accepted": None,
            "statement": visa["phrase"],
            "source": "employer",
            "display": DISPLAY_VISA,
            "visa_required_stated": True,
        }

    if accepted is not None:
        return {
            "international_students_accepted": True,
            "statement": accepted["phrase"],
            "source": "employer",
            "display": DISPLAY_ACCEPTED,
            "visa_required_stated": False,
        }

    return {
        "international_students_accepted": None,
        "statement": None,
        "source": None,
        "display": DISPLAY_UNSPECIFIED,
        "visa_required_stated": False,
    }


def extract_language_requirements(segments) -> List[Dict[str, Any]]:
    """Extract language requirements, keeping stated and inferred apart.

    ``segments`` is the output of :func:`app.nlp.segments.segment_text`, so
    each hit carries whether the posting marked it required or preferred.
    """

    results: List[Dict[str, Any]] = []
    seen = set()

    for segment in segments:
        if segment.is_header:
            continue

        text = segment.text
        if not text:
            continue

        lowered = text.lower()

        topik = _TOPIK_PATTERN.search(lowered)
        if topik:
            level = int(topik.group(1))
            key = ("korean", segment.kind, level)
            if key not in seen:
                seen.add(key)
                results.append(
                    {
                        "language": "korean",
                        "level": "TOPIK {0}".format(level),
                        "level_value": level,
                        "scale": "TOPIK",
                        "requirement": segment.kind,
                        "explicit": True,
                        "evidence": topik.group(0),
                        "clause": text,
                    }
                )
            continue

        english_level = _ENGLISH_LEVEL.search(lowered)
        for code, names in LANGUAGES:
            if code == "korean":
                continue
            matched = next((name for name in names if name in lowered), None)
            if not matched:
                continue
            level = english_level.group(1).upper() if english_level else None
            key = (code, segment.kind, level)
            if key in seen:
                break
            seen.add(key)
            results.append(
                {
                    "language": code,
                    "level": "CEFR {0}".format(level) if level else None,
                    "level_value": level,
                    "scale": "CEFR",
                    "requirement": segment.kind,
                    "explicit": segment.explicit,
                    "evidence": matched,
                    "clause": text,
                }
            )
            break

    return results
