"""Language detection by script ratio.

No model is needed. The decision is which script the text is written in, and a
ratio of Hangul to Latin letters answers it reliably for job listings. This
keeps the pipeline deterministic and free of a model download.
"""

from __future__ import annotations

import re
from typing import Optional

_HANGUL = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")
_KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_HANZI = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")

# A Korean listing that includes English terms still lands far above this.
# A short English listing with one stray character lands far below.
HANGUL_THRESHOLD = 0.15

UNDETERMINED = "und"


def hangul_ratio(value: str) -> float:
    """Share of alphabetic characters that are Hangul, between 0 and 1."""

    text = value or ""
    if not text:
        return 0.0
    hangul = len(_HANGUL.findall(text))
    latin = len(_LATIN.findall(text))
    total = hangul + latin
    if total == 0:
        return 0.0
    return hangul / total


def detect_language(value: str) -> str:
    """Return an ISO-639-1 code, or ``und`` when no script dominates."""

    text = value or ""
    if not text.strip():
        return UNDETERMINED

    hangul = len(_HANGUL.findall(text))
    kana = len(_KANA.findall(text))
    hanzi = len(_HANZI.findall(text))
    latin = len(_LATIN.findall(text))

    # Japanese uses kana, which shares codepoint ranges with some Hangul jamo
    # only in Japanese text. Kana without Hangul is a reliable signal.
    if kana and not hangul:
        return "ja"
    if hanzi and not hangul and not kana:
        return "zh"

    total = hangul + kana + latin
    if total == 0:
        return UNDETERMINED

    if hangul / total >= HANGUL_THRESHOLD:
        return "ko"
    if latin / total >= HANGUL_THRESHOLD:
        return "en"
    return UNDETERMINED


def is_korean(value: str) -> bool:
    """True when the text is Korean enough to warrant Korean extraction."""

    return detect_language(value) == "ko"
