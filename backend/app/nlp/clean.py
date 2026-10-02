"""Text normalisation for Korean listings.

Korean job ads are full of non-breaking spaces, full-width digits, ideographic
spaces, and inconsistent line breaks. Normalising before anything reads the
text measurably improves every later extraction stage, so it happens first.

This is the only stage that rewrites the text. Downstream stages see a cleaned
copy; the caller keeps the original for storage.
"""

from __future__ import annotations

import re
import unicodedata

NBSP = "\u00a0"

_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_BREAK = re.compile(r"\r\n|\r|\n")
_INLINE_SPACE = re.compile(r"[ \t\u3000]+")
_TRAILING_NOISE = re.compile(r"[\s,;:.·\-–—、。]+$")
_BULLET_PREFIX = re.compile(r"^[\s\-*•·▪◦o\u25cb\u25a0#>]+")


def normalize_text(value: str) -> str:
    """Return a cleaned copy of ``value``.

    NFKC folding converts full-width digits and Latin letters to ASCII and
    normalises Hangul compatibility jamo, which is what makes ``시급 １２,０００원``
    parseable by the same rule as ``시급 12,000원``.
    """

    if not value:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace(NBSP, " ")
    text = _ZERO_WIDTH.sub("", text)
    text = _BREAK.sub("\n", text)
    text = _INLINE_SPACE.sub(" ", text)

    lines = []
    for raw_line in text.split("\n"):
        line = _BULLET_PREFIX.sub("", raw_line).strip()
        line = _TRAILING_NOISE.sub("", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def split_lines(value: str) -> list:
    """Normalise then split into non-empty lines."""

    cleaned = normalize_text(value)
    if not cleaned:
        return []
    return [line for line in cleaned.split("\n") if line.strip()]
